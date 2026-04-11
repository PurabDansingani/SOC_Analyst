from environment import SOCEnv


def _clamp(score: float) -> float:
    """Keep the score strictly inside (0, 1) with a safe buffer."""
    EPS = 0.01
    if score != score:
        return EPS
    return max(EPS, min(score, 1.0 - EPS))


def grade(env: SOCEnv, obs=None) -> float:
    """
    Grades the actual environment state for the full incident response task.
    """
    # 1. Verify both critical threats are neutralized
    brute_force_stopped = not env.active_threats["brute_force"]["active"]
    malware_stopped = not env.active_threats["ransomware"]["active"]

    if brute_force_stopped and malware_stopped:
        # 2. Calculate data integrity bonus (Variance signal)
        # Check how many files remain 'normal' (not encrypted)
        saved_files = sum(1 for status in env.files.values()
                          if status == "normal")

        # Score ranges from 0.50 (all encrypted) to 0.95 (perfect save)
        base_success = 0.50
        file_bonus = saved_files * 0.15

        return _clamp(base_success + file_bonus)

    # Partial Failure: Only one of the threats was stopped
    if brute_force_stopped or malware_stopped:
        return _clamp(0.25)

    # Full Failure: Both threats still active
    return _clamp(0.15)
