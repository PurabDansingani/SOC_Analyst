import json
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field, model_validator

# --- OpenEnv Spec Models ---

class Action(BaseModel):
    tool: Literal["search_logs", "block_ip", "isolate_service", "kill_process", "submit_report"] = Field(
        description="Tools: 'search_logs' (needs 'query'), 'block_ip' (needs 'ip'), 'isolate_service' (needs 'service'), 'kill_process' (needs 'pid'), 'submit_report' (needs 'compromised_ip' and 'mitigated_threats')."
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
        examples=[0.01],
        description="Step reward. Guaranteed to be strictly within (0, 1).",
    )
    done: bool
    message: str
    success: bool = False

    @model_validator(mode="after")
    def _clamp_score_to_open_interval(self):
        """Auto-clamp individual step score into (0, 1) to satisfy validator."""
        EPS = 0.0001
        s = self.score
        if s != s:  # NaN guard
            s = EPS
        self.score = max(EPS, min(s, 1.0 - EPS))
        return self


# --- Stateful Simulation Engine ---

class SOCEnv:
    def __init__(self):
        self.current_task = "easy"
        self._reset_state()

    @staticmethod
    def _clamp_final_score(score: float, eps: float = 0.01) -> float:
        """Ensures the total sum remains strictly inside (0, 1)."""
        if score != score:
            return eps
        if score <= eps:
            return eps
        if score >= 1.0 - eps:
            return 1.0 - eps
        return float(score)

    @classmethod
    def _clamp_step_score(cls, score: float, eps: float = 0.001) -> float:
        """Clamps the individual delta reward."""
        return round(cls._clamp_final_score(score, eps=eps), 4)

    def _reset_state(self):
        self.tick = 0
        self.max_ticks = 15
        self.last_output = "System booted. Network monitoring online."
        self._episode_score_total = 0.0
        # Reduced living reward to allow more headroom for success grades
        self._living_reward = 0.002 
        
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
            desc = "A brute force attack is underway. Find the IP and block it."
        elif task_id == "medium":
            self.active_threats["ddos"]["active"] = True
            desc = "The web server CPU is spiking. Identify the DDoS IP and block it."
        elif task_id == "hard":
            self.active_threats["brute_force"]["active"] = True
            self.active_threats["ransomware"]["active"] = True
            desc = "Multiple threats detected. Stop the brute force and kill the malware process."

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
            ip = self.active_threats["brute_force"]["ip"]
            self.logs.append(f"[{time_str}] [AUTH] Failed login for 'admin' from {ip}")

        if self.active_threats["ddos"]["active"]:
            ip = self.active_threats["ddos"]["ip"]
            self.servers["web_server"]["cpu"] = 99
            self.logs.append(f"[{time_str}] [NET] massive SYN flood detected from {ip}.")
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

        self.logs.append(f"[{time_str}] [SYS] Health check passed.")

    def step(self, action: Action) -> tuple[Observation, Reward]:
        # Default incremental reward
        step_reward_val = self._living_reward
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
            else:
                self.last_output = f"IP {ip} already blocked."

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

        elif action.tool == "submit_report":
            graded = self._grade_task(action.params)
            # DELTA LOGIC: (Target Total) - (Already Given)
            # This ensures the SUM of all rewards = graded.score
            target_total = graded.score
            delta = target_total - self._episode_score_total
            graded.score = self._clamp_step_score(delta)
            return self.state(), graded

        self._simulate_tick()

        # Handle Timeout
        if self.tick >= self.max_ticks:
            target_failure_score = 0.15
            delta = target_failure_score - self._episode_score_total
            timeout_reward = Reward(
                score=self._clamp_step_score(delta),
                done=True,
                message="Timeout: Threats persisted.",
                success=False
            )
            return self.state(), timeout_reward

        # Standard Step Reward
        final_step_reward = self._clamp_step_score(step_reward_val)
        self._episode_score_total += final_step_reward
        
        return self.state(), Reward(score=final_step_reward, done=False, message=message, success=success)

    def _grade_task(self, params: dict) -> Reward:
        reported_ip = params.get("compromised_ip", "")
        
        if self.current_task == "easy":
            if not self.active_threats["brute_force"]["active"] and reported_ip == "103.45.67.89":
                return Reward(score=0.85, done=True, message="Success", success=True)
            return Reward(score=0.20, done=True, message="Failed", success=False)
            
        elif self.current_task == "medium":
            if not self.active_threats["ddos"]["active"]:
                return Reward(score=0.85, done=True, message="Success", success=True)
            return Reward(score=0.30, done=True, message="Failed", success=False)
            
        elif self.current_task == "hard":
            if not self.active_threats["brute_force"]["active"] and not self.active_threats["ransomware"]["active"]:
                # Scoring based on data integrity
                saved = sum(1 for s in self.files.values() if s == "normal")
                grade = 0.5 + (saved * 0.15) # 0.5 to 0.95 range
                return Reward(score=grade, done=True, message="Mitigated", success=True)
            return Reward(score=0.15, done=True, message="Failed", success=False)

        return Reward(score=0.1, done=True, message="Error", success=False)
