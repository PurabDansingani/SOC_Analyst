"""
Grader for the 'easy' task: Brute Force Triage.
Called by the OpenEnv validator to compute a task score strictly in (0, 1).
"""

import sys
import os

# Ensure the project root is on the path so we can import environment.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from environment import SOCEnv, Action


def _clamp(score: float, eps: float = 0.0001) -> float:
    """Ensure the score is strictly inside (0, 1)."""
    if score != score:  # NaN guard
        return eps
    return max(eps, min(score, 1.0 - eps))


def grade(*args, **kwargs) -> float:
    """
    Deterministic grader for the easy task.
    Runs the environment with the known-correct policy and returns a score in (0, 1).
    """
    env = SOCEnv()
    obs = env.reset("easy")

    # Step 1: block the brute-force IP
    obs, reward = env.step(Action(tool="block_ip", params={"ip": "103.45.67.89"}))

    # Step 2: submit report
    obs, reward = env.step(Action(tool="submit_report", params={"compromised_ip": "103.45.67.89"}))

    return _clamp(reward.score)
