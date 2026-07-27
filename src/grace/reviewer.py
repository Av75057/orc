import subprocess
from typing import List, Dict, Any
from fnmatch import fnmatch

from src.grace.models import Wave

ORCHESTRATOR_FILES = [
    "grace_state.json",
    "evidence/",
    "__pycache__/",
    ".pytest_cache/",
]


def get_changed_files() -> List[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git status failed: {result.stderr.strip()}")
    files = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        filepath = line[3:].strip().strip('"')
        if filepath:
            files.append(filepath)
    return files


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


def _is_orchestrator_file(filepath: str) -> bool:
    for pattern in ORCHESTRATOR_FILES:
        if filepath.startswith(pattern) or filepath == pattern.rstrip("/"):
            return True
    return False


def review_wave(wave: Wave) -> Dict[str, Any]:
    changed = get_changed_files()
    changed = [f for f in changed if not _is_orchestrator_file(f)]
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


