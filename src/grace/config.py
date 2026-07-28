"""
START_MODULE_CONTRACT: M-CONFIG
 purpose: Load and manage execution configuration and agent profiles
 owns:
   - src/grace/config.py
 inputs:
   - grace_config.yaml
   - environment variables GRACE_*
 outputs:
   - ExecutionConfig, ProfileManager
 dependencies:
   - PyYAML, os, pathlib
 invariants:
   - ProfileManager.get_ladder() always returns profiles sorted by priority desc
   - Environment variables override YAML values
 failure_policy:
   - FileNotFoundError if config missing and no defaults
   - ValueError on malformed profile entries
 non_goals:
   - No execution logic
   - No LLM calls
END_MODULE_CONTRACT: M-CONFIG
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from .models import AgentProfile, ExecutionConfig


_DEFAULT_CONFIG: Dict[str, Any] = {
    "profiles": [
        {
            "name": "coder-deepseek",
            "model": "deepseek-chat",
            "api_url": "https://api.deepseek.com/chat/completions",
            "priority": 300,
            "effort": "medium",
            "timeout_seconds": 600,
            "roles": ["coder"],
        },
        {
            "name": "reviewer-deepseek",
            "model": "deepseek-chat",
            "api_url": "https://api.deepseek.com/chat/completions",
            "priority": 300,
            "effort": "medium",
            "timeout_seconds": 600,
            "roles": ["reviewer"],
        },
    ],
    "execution": {
        "max_retries": 3,
        "progress_timeout": 600,
        "absolute_timeout": 3600,
        "worktree_isolation": False,
        "evidence_dir": ".grace/evidence",
        "log_dir": ".grace/logs",
    },
}


def load_config(config_path: Optional[str | Path] = None) -> ExecutionConfig:
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    raw: Dict[str, Any] = {}
    if config_path is not None:
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        else:
            raise FileNotFoundError(f"Config file not found: {path}")
    else:
        for candidate in [Path("grace_config.yaml"), Path(".grace/config.yaml")]:
            if candidate.exists():
                with open(candidate, "r", encoding="utf-8") as fh:
                    raw = yaml.safe_load(fh) or {}
                break

    merged = _deep_merge(_DEFAULT_CONFIG, raw)

    profiles = []
    for entry in merged.get("profiles", []):
        profiles.append(AgentProfile(
            name=entry["name"],
            model=entry["model"],
            api_url=entry["api_url"],
            priority=int(entry.get("priority", 100)),
            effort=entry.get("effort", "medium"),
            timeout_seconds=int(entry.get("timeout_seconds", 600)),
            roles=entry.get("roles", ["coder"]),
        ))

    exec_raw = merged.get("execution", {})
    config = ExecutionConfig(
        profiles=profiles,
        max_retries=int(os.environ.get("GRACE_MAX_RETRIES", exec_raw.get("max_retries", 3))),
        progress_timeout=int(os.environ.get("GRACE_PROGRESS_TIMEOUT", exec_raw.get("progress_timeout", 600))),
        absolute_timeout=int(os.environ.get("GRACE_ABSOLUTE_TIMEOUT", exec_raw.get("absolute_timeout", 3600))),
        worktree_isolation=os.environ.get("GRACE_WORKTREE_ISOLATION", str(exec_raw.get("worktree_isolation", False))).lower() in ("true", "1", "yes"),
        evidence_dir=os.environ.get("GRACE_EVIDENCE_DIR", exec_raw.get("evidence_dir", ".grace/evidence")),
        log_dir=os.environ.get("GRACE_LOG_DIR", exec_raw.get("log_dir", ".grace/logs")),
    )
    return config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ProfileManager:
    def __init__(self, config: ExecutionConfig) -> None:
        self._profiles = sorted(config.profiles, key=lambda p: -p.priority)

    @property
    def all_profiles(self) -> List[AgentProfile]:
        return list(self._profiles)

    def get_ladder(self, role: str) -> List[AgentProfile]:
        return [p for p in self._profiles if role in p.roles]

    def next_profile(self, role: str, failed: Optional[List[str]] = None) -> Optional[AgentProfile]:
        failed_set = set(failed or [])
        for profile in self.get_ladder(role):
            if profile.name not in failed_set:
                return profile
        return None

    def get_profile(self, name: str) -> Optional[AgentProfile]:
        for p in self._profiles:
            if p.name == name:
                return p
        return None
