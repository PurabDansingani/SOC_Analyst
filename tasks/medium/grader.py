from environment import SOCEnv, snap_score_tenths


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
        return snap_score_tenths(0.9)

    # Partial Success: Threat blocked but CPU still high
    if threat_mitigated:
        return snap_score_tenths(0.5)

    # Failure: DDoS still active
    return snap_score_tenths(0.3)
