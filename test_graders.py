"""
Quick validation script: imports each grader and verifies scores are strictly in (0, 1).
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from tasks.easy.grader import grade as easy_grade
from tasks.medium.grader import grade as medium_grade
from tasks.hard.grader import grade as hard_grade

def test_grader(name, grade_fn):
    score = grade_fn()
    in_range = 0 < score < 1
    status = "PASS" if in_range else "FAIL"
    print(f"[{status}] {name}: score={score:.6f}  (0 < {score:.6f} < 1 = {in_range})")
    return in_range

if __name__ == "__main__":
    print("=" * 60)
    print("OpenEnv Grader Validation Test")
    print("=" * 60)
    
    results = []
    results.append(test_grader("easy", easy_grade))
    results.append(test_grader("medium", medium_grade))
    results.append(test_grader("hard", hard_grade))
    
    print("-" * 60)
    if all(results):
        print("ALL GRADERS PASSED - scores strictly in (0, 1)")
    else:
        print("SOME GRADERS FAILED - fix before resubmitting!")
        sys.exit(1)
