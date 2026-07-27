"""
START_MODULE_CONTRACT: M-REVIEWER
  purpose: Проверяет соответствие результатов worker'а packet'у.
           Scope compliance, verification status, git snapshot.
  owns:
    - src/grace/reviewer.py
  inputs:
    - ControllerPacket
    - WorkerResult
    - git status
  outputs:
    - ReviewResult (status, violations, summary)
  dependencies:
    - M-MODELS (ControllerPacket, WorkerResult, ReviewResult)
    - git (subprocess)
  side_effects:
    - Reads git status
    - Writes structured JSON logs
  invariants:
    - Scope violation = hard failure
    - Verification failure = hard failure
    - Out-of-scope changes = hard failure
  failure_policy:
    - Формирует failure packet с reason
    - Отделяет hard failure от acceptable follow-up
  non_goals:
    - Не исправляет код
    - Не запускает verification повторно
END_MODULE_CONTRACT: M-REVIEWER
"""

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


def _ensure_git_repo(workspace: str):
    git_dir = os.path.join(workspace, ".git")
    if not os.path.exists(git_dir):
        print(f"[REVIEWER] Git repository not found in {workspace}. Initializing...")
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial auto-commit by GRACE Reviewer", "--allow-empty"],
            cwd=workspace, capture_output=True,
        )
        print("[REVIEWER] Git initialized and initial snapshot created.")


def get_changed_files(workspace: Optional[str] = None) -> List[str]:
    cwd = workspace or os.getcwd()
    _ensure_git_repo(cwd)
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=False, cwd=cwd,
        )
    except Exception as e:
        print(f"[REVIEWER] Git error: {e}")
        return ["__GIT_ERROR__"]
    if result.returncode != 0:
        print(f"[REVIEWER] Git error: {result.stderr.strip()}")
        return ["__GIT_ERROR__"]
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
    if "__GIT_ERROR__" in changed:
        return {
            "status": "FAILED",
            "reason": "GIT_ERROR",
            "violations": [],
            "verification": {},
        }
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

    if not all_ok:
        failed = [cmd for cmd, r in verif.items() if r["returncode"] != 0]
        errors = "\n".join(
            f"[{cmd}]\nSTDOUT:\n{r['stdout']}\nSTDERR:\n{r['stderr']}"
            for cmd, r in verif.items() if r["returncode"] != 0
        )
        return {
            "status": "FAILED",
            "reason": "VERIFICATION_FAILED",
            "violations": [],
            "verification": verif,
            "error_output": errors,
        }

    return {
        "status": "PASSED",
        "reason": None,
        "violations": [],
        "verification": verif,
    }



