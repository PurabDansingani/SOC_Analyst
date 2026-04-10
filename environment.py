import json
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field

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
    score: float
    done: bool
    message: str
    success: bool = False


# --- Stateful Simulation Engine ---

class SOCEnv:
    def __init__(self):
        self.current_task = "easy"
        self._reset_state()

    @staticmethod
    def _clamp_final_score(score: float, eps: float = 1e-6) -> float:
        if score != score:  # NaN check
            return eps
        # Ensure STRICTLY inside (0, 1)
        if score <= eps:
            return eps
        if score >= 1.0 - eps:
            return 1.0 - eps
        return float(score)

    def _reset_state(self):
        self.tick = 0
        self.max_ticks = 15
        self.last_output = "System booted. Network monitoring online."
        # Track cumulative episode score so validators that SUM rewards
        # see a final task score strictly in (0, 1).
        self._episode_score_total = 0.0
        
        # Simulated Infrastructure
        self.active_blocks = []
        self.isolated_services = []
        self.logs = []
        self.files = {"data_1.sql": "normal", "users.db": "normal", "config.yaml": "normal"}
        
        self.servers = {
            "web_server": {"cpu": 15, "status": "online", "pids": ["nginx (pid: 101)", "ssh (pid: 102)"]},
            "db_server": {"cpu": 10, "status": "online", "pids": ["postgres (pid: 201)"]}
        }
        
        # Threat Tracking
        self.active_threats = {
            "brute_force": {"active": False, "ip": "103.45.67.89", "target": "web_server"},
            "ddos": {"active": False, "ip": "202.11.22.33", "target": "web_server"},
            "ransomware": {"active": False, "pid": "malware.exe (pid: 666)", "target": "db_server"}
        }

    def reset(self, task_id: str = "easy") -> Observation:
        self.current_task = task_id
        self._reset_state()
        
        # Inject threats based on difficulty
        if task_id == "easy":
            self.active_threats["brute_force"]["active"] = True
            desc = "A brute force attack is underway. Find the IP and block it."
        elif task_id == "medium":
            self.active_threats["ddos"]["active"] = True
            desc = "The web server CPU is spiking. Identify the DDoS IP, block it, and restore CPU to normal."
        elif task_id == "hard":
            self.active_threats["brute_force"]["active"] = True
            self.active_threats["ransomware"]["active"] = True
            desc = "Multiple threats detected. Stop the brute force IP, find the anomalous process on the db_server, kill it, and submit your report."

        # Run initial tick to populate starting logs
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

    # --- THE THREAT MATRIX GENERATORS ---
    def _simulate_tick(self):
        """Advances time and generates dynamic system behavior based on active threats."""
        self.tick += 1
        time_str = f"T+{self.tick}s"

        # 1. Brute Force Generator
        if self.active_threats["brute_force"]["active"]:
            ip = self.active_threats["brute_force"]["ip"]
            # Injecting multiple logs per tick to simulate speed
            self.logs.append(f"[{time_str}] [AUTH] Failed login for 'admin' from {ip}")
            self.logs.append(f"[{time_str}] [AUTH] Failed login for 'root' from {ip}")

        # 2. DDoS Generator
        if self.active_threats["ddos"]["active"]:
            ip = self.active_threats["ddos"]["ip"]
            if "web_server" in self.isolated_services:
                self.active_threats["ddos"]["active"] = False
                self.servers["web_server"]["cpu"] = 15
                self.servers["web_server"]["status"] = "isolated"
                self.logs.append(f"[{time_str}] [NET] DDoS path to web_server blocked due to service isolation.")
            else:
                self.servers["web_server"]["cpu"] = 99
                self.servers["web_server"]["status"] = "degraded"
                self.logs.append(f"[{time_str}] [NET] massive SYN flood detected from {ip}. Dropping packets.")
        elif self.servers["web_server"]["cpu"] == 99: 
            # If threat was stopped, naturally recover CPU
            self.servers["web_server"]["cpu"] = 15
            self.servers["web_server"]["status"] = "isolated" if "web_server" in self.isolated_services else "online"
            self.logs.append(f"[{time_str}] [SYS] web_server CPU returning to normal thresholds.")

        # 3. Ransomware Generator
        if self.active_threats["ransomware"]["active"]:
            pid = self.active_threats["ransomware"]["pid"]
            if pid not in self.servers["db_server"]["pids"]:
                self.servers["db_server"]["pids"].append(pid)
            
            # Encrypt one file per tick
            for filename, status in self.files.items():
                if status == "normal":
                    self.files[filename] = "encrypted"
                    self.logs.append(f"[{time_str}] [FILE_MONITOR] {filename} extension changed to .encrypted by {pid}")
                    break # Only encrypt one per tick

        # Normal background noise logs
        self.logs.append(f"[{time_str}] [CRON] Cleanup script executed normally.")

    # --- ACTION EXECUTION ---
    def step(self, action: Action) -> tuple[Observation, Reward]:
        # Important: validators commonly SUM all step rewards to compute the task score.
        # So we emit *incremental* rewards whose total equals the final grade.
        reward = Reward(score=0.0, done=False, message="", success=False)
        
        # Execute Tool
        if action.tool == "search_logs":
            query = action.params.get("query", "").lower()
            results = [log for log in self.logs if query in log.lower()]
            # Return last 5 matches to avoid context window overflow
            self.last_output = json.dumps(results[-5:]) if results else "No matching logs found."

        elif action.tool == "block_ip":
            ip = action.params.get("ip")
            if ip not in self.active_blocks:
                self.active_blocks.append(ip)
                self.last_output = f"Firewall rule added: DROP IP {ip}."
                
                # Check if this mitigates active threats
                if ip == self.active_threats["brute_force"]["ip"]:
                    self.active_threats["brute_force"]["active"] = False
                    self.last_output += " Brute force traffic stopped."
                if ip == self.active_threats["ddos"]["ip"]:
                    self.active_threats["ddos"]["active"] = False
                    self.last_output += " DDoS traffic stopped."
            else:
                self.last_output = f"IP {ip} is already blocked."

        elif action.tool == "kill_process":
            pid = action.params.get("pid")
            killed = False
            for server, data in self.servers.items():
                if pid in data["pids"]:
                    data["pids"].remove(pid)
                    killed = True
                    self.last_output = f"Process {pid} terminated on {server}."
                    if pid == self.active_threats["ransomware"]["pid"]:
                        self.active_threats["ransomware"]["active"] = False
                        self.last_output += " Malicious file encryption halted."
            if not killed:
                self.last_output = f"Process {pid} not found on any server."

        elif action.tool == "isolate_service":
            service = action.params.get("service")
            if not service:
                self.last_output = "Missing required parameter: service."
            elif service not in self.servers:
                self.last_output = f"Service {service} not found."
            elif service in self.isolated_services:
                self.last_output = f"Service {service} is already isolated."
            else:
                self.isolated_services.append(service)
                self.servers[service]["status"] = "isolated"
                self.last_output = f"Service {service} isolated from the network."

        elif action.tool == "submit_report":
            obs = self.state()
            graded = self._grade_task(action.params)
            final_total = self._clamp_final_score(graded.score)
            # Telescoping reward: return only the delta to reach the final total.
            delta = final_total - self._episode_score_total
            self._episode_score_total = final_total
            graded.score = delta
            return obs, graded

        # Advance the simulation!
        self._simulate_tick()

        # Check timeout
        if self.tick >= self.max_ticks:
            # End the episode with a small but valid final score strictly in (0, 1).
            final_total = self._clamp_final_score(0.05)
            delta = final_total - self._episode_score_total
            self._episode_score_total = final_total
            reward.score = delta
            reward.done = True
            reward.message = "Critical failure: Max time elapsed. Systems compromised."
            reward.success = False
            obs = self.state()
            return obs, reward

        obs = self.state()
        return obs, reward

    # --- GRADER ---
    def _grade_task(self, params: dict) -> Reward:
        reported_ip = params.get("compromised_ip", "")
        
        if self.current_task == "easy":
            if not self.active_threats["brute_force"]["active"] and reported_ip == "103.45.67.89":
                return Reward(score=0.9, done=True, message="Success: Brute force stopped and identified.", success=True)
            return Reward(score=0.2, done=True, message="Failed: Attack still active or wrong IP.", success=False)
            
        elif self.current_task == "medium":
            if not self.active_threats["ddos"]["active"] and self.servers["web_server"]["cpu"] < 50:
                return Reward(score=0.9, done=True, message="Success: DDoS mitigated and server recovered.", success=True)
            return Reward(score=0.4, done=True, message="Failed: Server still under load.", success=False)
            
        elif self.current_task == "hard":
            if not self.active_threats["brute_force"]["active"] and not self.active_threats["ransomware"]["active"]:
                # Check how many files were saved
                saved_files = sum(1 for status in self.files.values() if status == "normal")
                if saved_files == 3:
                    return Reward(score=0.9, done=True, message="Perfect! All threats stopped before any data loss.", success=True)
                elif saved_files > 0:
                    return Reward(score=0.8, done=True, message=f"Threats stopped, but {3-saved_files} files were encrypted.", success=True)
                else:
                    return Reward(score=0.5, done=True, message="Threats stopped too late. All files lost.", success=True)
            return Reward(score=0.1, done=True, message="Failed: Critical threats still active on network.", success=False)

        return Reward(score=0.1, done=True, message="Unknown error.", success=False)