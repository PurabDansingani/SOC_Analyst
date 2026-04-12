from environment import SOCEnv, snap_score_tenths


def grade(env: SOCEnv, obs=None) -> float:
    """
    Grades the ACTUAL state of the provided environment.
    """
    # 1. Check if the specific threat for 'easy' is mitigated
    is_mitigated = not env.active_threats["brute_force"]["active"]

    # 2. Return a fixed total score based on success/failure (0.0–1.0 in 0.1 steps).
    if is_mitigated:
        return snap_score_tenths(0.9)

    return snap_score_tenths(0.2)
