import json
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field, model_validator


def snap_score_tenths(value: float | None) -> float:
    """Snap any score to one decimal in [0.0, 0.1, …, 1.0]."""
    if value is None:
        return 0.0
    if value != value:  # NaN
        return 0.0
    v = max(0.0, min(1.0, float(value)))
    return round(v, 1)


# --- OpenEnv Spec Models ---

class Action(BaseModel):
    tool: Literal["search_logs", "block_ip", "isolate_service", "kill_process", "submit_report"] = Field(
        description="Tools: 'search_logs' (needs 'query'), 'block_ip' (needs 'ip'), 'isolate_service' (needs 'service'), 'kill_process' (needs 'pid'), 'submit_report' (needs 'compromised_ip')."
    )
    params: Dict[str, Any] = Field(default_factory=dict)

class ServerState(BaseModel):
    name: str
    cpu_usage: int
    status: str
    active_pids: List[str]

class Observation(BaseModel):
    tick_time: int
    servers: List[ServerState]
    active_blocks: List[str]
    last_tool_output: str
    task_description: str

class Reward(BaseModel):
    score: float = Field(
        ...,
        description="Step reward in [0, 1], snapped to 0.1 increments (0, 0.1, …, 1.0).",
    )
    done: bool
    message: str
    success: bool = False

    @model_validator(mode="after")
    def _snap_score(self):
        self.score = snap_score_tenths(self.score)
        return self


# --- Stateful Simulation Engine ---

class SOCEnv:
    def __init__(self):
        self.current_task = "easy"
        self._reset_state()

    @staticmethod
    def _clamp_step_score(score: float) -> float:
        """Snap step / delta reward to tenths in [0, 1]."""
        return snap_score_tenths(score)

    def _reset_state(self):
        self.tick = 0
        self.max_ticks = 15
        self.last_output = "System booted. Monitoring active."
        self._episode_score_total = 0.0
        
        self.active_blocks = []
        self.isolated_services = []
        self.logs = []
        self.files = {"data_1.sql": "normal", "users.db": "normal", "config.yaml": "normal"}
        
        self.servers = {
            "web_server": {"cpu": 15, "status": "online", "pids": ["nginx (pid: 101)", "ssh (pid: 102)"]},
            "db_server": {"cpu": 10, "status": "online", "pids": ["postgres (pid: 201)"]}
        }
        
        self.active_threats = {
            "brute_force": {"active": False, "ip": "103.45.67.89", "target": "web_server"},
            "ddos": {"active": False, "ip": "202.11.22.33", "target": "web_server"},
            "ransomware": {"active": False, "pid": "malware.exe (pid: 666)", "target": "db_server"}
        }

    def reset(self, task_id: str = "easy") -> Observation:
        self.current_task = task_id
        self._reset_state()
        
        if task_id == "easy":
            self.active_threats["brute_force"]["active"] = True
            desc = "Identify and block the brute force IP."
        elif task_id == "medium":
            self.active_threats["ddos"]["active"] = True
            desc = "Mitigate the DDoS attack spiking the web server CPU."
        elif task_id == "hard":
            self.active_threats["brute_force"]["active"] = True
            self.active_threats["ransomware"]["active"] = True
            desc = "Stop the brute force and kill the ransomware PID before data loss."

        self._simulate_tick()
        return self.state(task_description=desc)

    def state(self, task_description: str = None) -> Observation:
        server_states = [
            ServerState(name=name, cpu_usage=data["cpu"], status=data["status"], active_pids=data["pids"])
            for name, data in self.servers.items()
        ]
        return Observation(
            tick_time=self.tick,
            servers=server_states,
            active_blocks=self.active_blocks,
            last_tool_output=self.last_output,
            task_description=task_description or "Continue task."
        )

    def _simulate_tick(self):
        self.tick += 1
        time_str = f"T+{self.tick}s"

        if self.active_threats["brute_force"]["active"]:
            self.logs.append(f"[{time_str}] [AUTH] Failed login from {self.active_threats['brute_force']['ip']}")

        if self.active_threats["ddos"]["active"]:
            self.servers["web_server"]["cpu"] = 99
            self.logs.append(f"[{time_str}] [NET] massive SYN flood detected.")
        elif self.servers["web_server"]["cpu"] == 99: 
            self.servers["web_server"]["cpu"] = 15

        if self.active_threats["ransomware"]["active"]:
            pid = self.active_threats["ransomware"]["pid"]
            if pid not in self.servers["db_server"]["pids"]:
                self.servers["db_server"]["pids"].append(pid)
            for filename, status in self.files.items():
                if status == "normal":
                    self.files[filename] = "encrypted"
                    self.logs.append(f"[{time_str}] [FILE] {filename} encrypted by {pid}")
                    break

    def step(self, action: Action) -> tuple[Observation, Reward]:
        # Partial progress in 0.1 increments (meaningful tool outcomes only).
        current_step_reward = 0.0
        done = False
        message = ""
        success = False

        if action.tool == "search_logs":
            query = action.params.get("query", "").lower()
            results = [log for log in self.logs if query in log.lower()]
            self.last_output = json.dumps(results[-5:]) if results else "No matches."

        elif action.tool == "block_ip":
            ip = action.params.get("ip")
            if ip not in self.active_blocks:
                self.active_blocks.append(ip)
                if ip == self.active_threats["brute_force"]["ip"]:
                    self.active_threats["brute_force"]["active"] = False
                if ip == self.active_threats["ddos"]["ip"]:
                    self.active_threats["ddos"]["active"] = False
                self.last_output = f"Blocked IP {ip}."
                current_step_reward = 0.1
            else:
                self.last_output = f"IP {ip} is already blocked."

        elif action.tool == "kill_process":
            pid = action.params.get("pid")
            killed = False
            for server, data in self.servers.items():
                if pid in data["pids"]:
                    data["pids"].remove(pid)
                    killed = True
                    if pid == self.active_threats["ransomware"]["pid"]:
                        self.active_threats["ransomware"]["active"] = False
            self.last_output = f"Killed {pid}." if killed else "PID not found."
            if killed:
                current_step_reward = 0.1

        elif action.tool == "submit_report":
            graded = self._grade_task(action.params)
            # DELTA CALCULATION: Ensures Sum(Rewards) == graded.score
            target_total = graded.score
            delta = target_total - self._episode_score_total
            graded.score = self._clamp_step_score(max(0.0, delta))
            return self.state(), graded

        self._simulate_tick()

        # Handle Timeout
        if self.tick >= self.max_ticks:
            target_failure_score = 0.2
            delta = target_failure_score - self._episode_score_total
            return self.state(), Reward(
                score=self._clamp_step_score(max(0.0, delta)),
                done=True,
                message="Max ticks reached. System compromised.",
                success=False
            )

        # Standard Step Update
        clamped_step_reward = self._clamp_step_score(current_step_reward)
        self._episode_score_total += clamped_step_reward
        
        return self.state(), Reward(score=clamped_step_reward, done=False, message=message, success=success)

    def _grade_task(self, params: dict) -> Reward:
        """Internal helper to determine the TARGET total score for the episode."""
        reported_ip = params.get("compromised_ip", "")
        
        if self.current_task == "easy":
            if not self.active_threats["brute_force"]["active"] and reported_ip == "103.45.67.89":
                return Reward(score=0.9, done=True, message="Success", success=True)
            return Reward(score=0.2, done=True, message="Incorrect IP or threat active", success=False)
            
        elif self.current_task == "medium":
            if not self.active_threats["ddos"]["active"] and self.servers["web_server"]["cpu"] < 50:
                return Reward(score=0.9, done=True, message="DDoS mitigated", success=True)
            return Reward(score=0.3, done=True, message="Server still degraded", success=False)
            
        elif self.current_task == "hard":
            if not self.active_threats["brute_force"]["active"] and not self.active_threats["ransomware"]["active"]:
                # Variable score based on data integrity (Variance check)
                saved_files = sum(1 for s in self.files.values() if s == "normal")
                total_grade = snap_score_tenths(0.5 + (saved_files * 0.15))
                return Reward(score=total_grade, done=True, message=f"Threats cleared. {saved_files} files saved.", success=True)
            return Reward(score=0.2, done=True, message="Critical threats still active", success=False)

        return Reward(score=0.1, done=True, message="Unknown task state", success=False)
