import pytest
from pathlib import Path
from src.grace.config import ProfileManager, load_config
from src.grace.models import AgentProfile, ExecutionConfig


class TestLoadConfig:
    def test_defaults_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config.max_retries == 3
        assert len(config.profiles) >= 1

    def test_load_from_yaml(self, tmp_path):
        yaml = """profiles:
  - name: test-coder
    model: test-model
    api_url: http://localhost:8080
    priority: 500
    effort: high
    timeout_seconds: 300
    roles: [coder, reviewer]

execution:
  max_retries: 5
  worktree_isolation: true
"""
        f = tmp_path / "grace_config.yaml"; f.write_text(yaml)
        config = load_config(f)
        assert config.max_retries == 5
        assert config.worktree_isolation is True
        assert config.profiles[0].name == "test-coder"
        assert config.profiles[0].priority == 500
        assert config.profiles[0].roles == ["coder", "reviewer"]

    def test_env_override(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GRACE_MAX_RETRIES", "10")
        monkeypatch.setenv("GRACE_WORKTREE_ISOLATION", "true")
        config = load_config()
        assert config.max_retries == 10
        assert config.worktree_isolation is True

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")


class TestProfileManager:
    def _config(self):
        return ExecutionConfig(profiles=[
            AgentProfile(name="low", model="m1", api_url="u1", priority=100, roles=["coder"]),
            AgentProfile(name="high", model="m2", api_url="u2", priority=300, roles=["coder"]),
            AgentProfile(name="mid", model="m3", api_url="u3", priority=200, roles=["coder", "reviewer"]),
            AgentProfile(name="rev", model="m4", api_url="u4", priority=400, roles=["reviewer"]),
        ])

    def test_ladder_sorted(self):
        pm = ProfileManager(self._config())
        ladder = pm.get_ladder("coder")
        priorities = [p.priority for p in ladder]
        assert priorities == sorted(priorities, reverse=True)

    def test_ladder_filters_role(self):
        pm = ProfileManager(self._config())
        names = {p.name for p in pm.get_ladder("reviewer")}
        assert names == {"mid", "rev"}

    def test_next_profile_skips_failed(self):
        pm = ProfileManager(self._config())
        first = pm.next_profile("coder")
        assert first is not None and first.name == "high"
        second = pm.next_profile("coder", failed=["high"])
        assert second is not None and second.name == "mid"
        third = pm.next_profile("coder", failed=["high", "mid"])
        assert third is not None and third.name == "low"

    def test_next_exhausted(self):
        pm = ProfileManager(self._config())
        assert pm.next_profile("coder", failed=["high", "mid", "low"]) is None

    def test_get_profile(self):
        pm = ProfileManager(self._config())
        p = pm.get_profile("mid")
        assert p is not None and p.priority == 200
        assert pm.get_profile("nonexistent") is None
