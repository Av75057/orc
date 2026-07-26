import subprocess
from typing import List, Dict, Any
from fnmatch import fnmatch

from src.grace.models import Wave


def get_changed_files(commit_ref: str = "HEAD") -> List[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", commit_ref],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def check_write_scope(changed_files: List[str], allowed_scope: List[str]) -> List[str]:
    violations = []
    for f in changed_files:
        if not any(fnmatch(f, pattern) for pattern in allowed_scope):
            violations.append(f)
    return violations


def run_verification(commands: List[str]) -> Dict[str, Dict[str, Any]]:
    results = {}
    for cmd in commands:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=False,
        )
        results[cmd] = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    return results


def review_wave(wave: Wave, commit_ref: str = "HEAD") -> Dict[str, Any]:
    changed = get_changed_files(commit_ref)
    violations = check_write_scope(changed, wave.allowed_write_scope)
    scope_ok = len(violations) == 0

    if not scope_ok:
        return {
            "status": "FAILED",
            "reason": "SCOPE_VIOLATION",
            "violations": violations,
            "verification": {},
        }

    verif = run_verification(wave.verification)
    all_ok = all(v["returncode"] == 0 for v in verif.values())

    return {
        "status": "PASSED" if all_ok else "FAILED",
        "reason": None if all_ok else "VERIFICATION_FAILED",
        "violations": [],
        "verification": verif,
    }
