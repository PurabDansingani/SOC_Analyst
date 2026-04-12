from environment import SOCEnv, snap_score_tenths


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

        base_success = 0.5
        file_bonus = saved_files * 0.15

        return snap_score_tenths(base_success + file_bonus)

    # Partial Failure: Only one of the threats was stopped
    if brute_force_stopped or malware_stopped:
        return snap_score_tenths(0.3)

    # Full Failure: Both threats still active
    return snap_score_tenths(0.2)
