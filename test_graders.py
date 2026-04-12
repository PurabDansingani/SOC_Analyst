"""
Quick validation script: imports each grader and verifies scores in [0, 1] on 0.1 steps.
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from environment import SOCEnv
from tasks.easy.grader import grade as easy_grade
from tasks.medium.grader import grade as medium_grade
from tasks.hard.grader import grade as hard_grade


def _is_tenth_grid(score: float) -> bool:
    return abs(round(score, 1) - score) < 1e-6 and abs(round(score * 10) - score * 10) < 1e-5


def test_grader(name, grade_fn, task_id: str):
    env = SOCEnv()
    env.reset(task_id)
    score = grade_fn(env)
    in_range = 0.0 <= score <= 1.0 and _is_tenth_grid(score)
    status = "PASS" if in_range else "FAIL"
    print(f"[{status}] {name}: score={score:.6f}  ([0,1] tenth grid = {in_range})")
    return in_range

if __name__ == "__main__":
    print("=" * 60)
    print("OpenEnv Grader Validation Test")
    print("=" * 60)
    
    results = []
    results.append(test_grader("easy", easy_grade, "easy"))
    results.append(test_grader("medium", medium_grade, "medium"))
    results.append(test_grader("hard", hard_grade, "hard"))
    
    print("-" * 60)
    if all(results):
        print("ALL GRADERS PASSED - scores on 0.0, 0.1, ..., 1.0 grid")
    else:
        print("SOME GRADERS FAILED - fix before resubmitting!")
        sys.exit(1)
