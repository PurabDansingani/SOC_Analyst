from environment import SOCEnv


def _clamp(score: float) -> float:
    # Use a wider margin (0.01) to stay safely away from 1.0 and 0.0
    # to avoid precision errors in the validator's floating point check.
    EPS = 0.01
    if score != score:
        return EPS
    return max(EPS, min(score, 1.0 - EPS))


def grade(env: SOCEnv, obs=None) -> float:
    """
    Grades the ACTUAL state of the provided environment.
    """
    # 1. Check if the specific threat for 'easy' is mitigated
    is_mitigated = not env.active_threats["brute_force"]["active"]

    # 2. Return a fixed total score based on success/failure
    # These values must be strictly between 0 and 1.
    if is_mitigated:
        return _clamp(0.85)

    return _clamp(0.15)
