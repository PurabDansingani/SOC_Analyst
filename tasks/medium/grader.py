import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from environment import SOCEnv

def _clamp(score: float) -> float:
    """Keep the score strictly inside (0, 1) with a safe buffer."""
    EPS = 0.01
    if score != score: return EPS
    return max(EPS, min(score, 1.0 - EPS))

def grade(env: SOCEnv, obs=None) -> float:
    """
    Grades the actual environment state for the DDoS mitigation task.
    """
    # 1. Check if the DDoS threat is inactive
    threat_mitigated = not env.active_threats["ddos"]["active"]
    
    # 2. Check if the CPU usage has recovered (should be < 50)
    cpu_usage = env.servers["web_server"]["cpu"]
    cpu_recovered = cpu_usage < 50
    
    # Success: Threat stopped AND CPU recovered
    if threat_mitigated and cpu_recovered:
        return _clamp(0.85)
    
    # Partial Success: Threat blocked but CPU still high
    if threat_mitigated:
        return _clamp(0.50)
        
    # Failure: DDoS still active
    return _clamp(0.30)
