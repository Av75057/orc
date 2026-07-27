import os
import subprocess
from typing import List, Dict, Any, Optional
from fnmatch import fnmatch

from src.grace.models import Wave


ORCHESTRATOR_FILES = [
    "grace_state.json",
    "evidence/",
    "__pycache__/",
    ".pytest_cache/",
]


def get_changed_files(workspace: Optional[str] = None) -> List[str]:
    cwd = workspace or os.getcwd()
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=False, cwd=cwd,
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


def run_verification(commands: List[str], workspace: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    cwd = workspace or os.getcwd()
    results = {}
    for cmd in commands:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=False, cwd=cwd,
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


def review_wave(wave: Wave, workspace: Optional[str] = None) -> Dict[str, Any]:
    changed = get_changed_files(workspace)
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

    verif = run_verification(wave.verification, workspace)
    all_ok = all(v["returncode"] == 0 for v in verif.values())

    return {
        "status": "PASSED" if all_ok else "FAILED",
        "reason": None if all_ok else "VERIFICATION_FAILED",
        "violations": [],
        "verification": verif,
    }

