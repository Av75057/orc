import pytest
import subprocess
from unittest.mock import patch, MagicMock
from src.grace.models import Wave
from src.grace.reviewer import (
    get_changed_files,
    check_write_scope,
    run_verification,
    review_wave,
)


class TestGetChangedFiles:
    @patch("src.grace.reviewer.subprocess.run")
    def test_returns_list_of_files(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" M src/a.py\n M tests/test_a.py\n",
            stderr="",
        )
        files = get_changed_files()
        assert files == ["src/a.py", "tests/test_a.py"]

    @patch("src.grace.reviewer.subprocess.run")
    def test_uses_cwd_from_workspace(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr="",
        )
        get_changed_files(workspace="/tmp/project")
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["cwd"] == "/tmp/project"

    @patch("src.grace.reviewer.subprocess.run")
    def test_defaults_cwd_to_cwd(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr="",
        )
        get_changed_files()
        mock_run.assert_called_once()
        # without workspace, cwd should be os.getcwd() or None
        assert mock_run.call_args[1]["cwd"] is not None

    @patch("src.grace.reviewer.subprocess.run")
    def test_parses_untracked_files(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="?? new_file.py\n M modified.py\n?? frontend/app.tsx\n",
            stderr="",
        )
        files = get_changed_files()
        assert "new_file.py" in files
        assert "modified.py" in files
        assert "frontend/app.tsx" in files

    @patch("src.grace.reviewer.subprocess.run")
    def test_raises_on_git_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: not a git repository",
        )
        with pytest.raises(RuntimeError, match="git status failed"):
            get_changed_files()

    @patch("src.grace.reviewer.subprocess.run")
    def test_skips_empty_lines(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" M src/a.py\n\n M tests/test_a.py\n",
            stderr="",
        )
        files = get_changed_files()
        assert files == ["src/a.py", "tests/test_a.py"]


class TestCheckWriteScope:
    def test_all_files_in_scope(self):
        changed = ["src/a.py", "tests/test_a.py"]
        scope = ["src/a.py", "tests/test_a.py", "src/grace/models.py"]
        assert check_write_scope(changed, scope) == []

    def test_file_outside_scope(self):
        changed = ["src/a.py", "infra/deploy.yaml"]
        scope = ["src/a.py", "tests/test_a.py"]
        assert check_write_scope(changed, scope) == ["infra/deploy.yaml"]

    def test_multiple_violations(self):
        changed = ["src/a.py", "infra/x.yaml", "frontend/x.js"]
        scope = ["src/*"]
        assert check_write_scope(changed, scope) == ["infra/x.yaml", "frontend/x.js"]

    def test_empty_changed_files(self):
        assert check_write_scope([], ["src/*"]) == []

    def test_glob_pattern_matching(self):
        changed = ["src/grace/a.py", "src/grace/b.py"]
        scope = ["src/grace/*"]
        assert check_write_scope(changed, scope) == []

    def test_glob_pattern_rejection(self):
        changed = ["src/grace/a.py", "infra/x.yaml"]
        scope = ["src/grace/*"]
        assert check_write_scope(changed, scope) == ["infra/x.yaml"]


class TestRunVerification:
    @patch("src.grace.reviewer.subprocess.run")
    def test_successful_command(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="All tests passed!\n", stderr="",
        )
        results = run_verification(["pytest tests/"])
        assert results["pytest tests/"]["returncode"] == 0

    @patch("src.grace.reviewer.subprocess.run")
    def test_uses_workspace_cwd(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="OK", stderr="",
        )
        run_verification(["pytest"], workspace="/tmp/project")
        mock_run.assert_called_once()
        assert mock_run.call_args[1]["cwd"] == "/tmp/project"

    @patch("src.grace.reviewer.subprocess.run")
    def test_failing_command(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="FAILED",
        )
        results = run_verification(["pytest tests/"])
        assert results["pytest tests/"]["returncode"] == 1


class TestReviewWave:
    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_passed_when_scope_ok_and_verification_ok(self, mock_verif, mock_git):
        mock_git.return_value = ["src/grace/models.py"]
        mock_verif.return_value = {"pytest": {"returncode": 0, "stdout": "OK", "stderr": ""}}
        wave = Wave(id="WAVE-1", goal="test", allowed_write_scope=["src/grace/*"], verification=["pytest"])
        result = review_wave(wave)
        assert result["status"] == "PASSED"

    @patch("src.grace.reviewer.get_changed_files")
    def test_failed_on_scope_violation(self, mock_git):
        mock_git.return_value = ["infra/deploy.yaml", "src/grace/models.py"]
        wave = Wave(id="WAVE-1", goal="test", allowed_write_scope=["src/grace/*"], verification=["pytest"])
        result = review_wave(wave)
        assert result["status"] == "FAILED"
        assert result["reason"] == "SCOPE_VIOLATION"

    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_passes_workspace_to_git_and_verif(self, mock_verif, mock_git):
        mock_git.return_value = ["src/app.py"]
        mock_verif.return_value = {"pytest": {"returncode": 0, "stdout": "OK", "stderr": ""}}
        wave = Wave(id="WAVE-1", goal="test", allowed_write_scope=["src/*"], verification=["pytest"])
        result = review_wave(wave, workspace="/tmp/project")
        assert result["status"] == "PASSED"
        mock_git.assert_called_once_with("/tmp/project")
        mock_verif.assert_called_once_with(["pytest"], "/tmp/project")

    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_excludes_state_and_evidence(self, mock_verif, mock_git):
        mock_git.return_value = ["src/app.py", "grace_state.json", "evidence/T1/log.txt"]
        mock_verif.return_value = {"pytest": {"returncode": 0, "stdout": "OK", "stderr": ""}}
        wave = Wave(id="WAVE-1", goal="test", allowed_write_scope=["src/*"], verification=["pytest"])
        result = review_wave(wave)
        assert result["status"] == "PASSED"

    @patch("src.grace.reviewer.get_changed_files")
    def test_excludes_state_but_catches_other_violations(self, mock_git):
        mock_git.return_value = ["src/app.py", "grace_state.json", "infra/bad.yaml"]
        wave = Wave(id="WAVE-1", goal="test", allowed_write_scope=["src/*"], verification=["pytest"])
        result = review_wave(wave)
        assert result["status"] == "FAILED"
        assert "infra/bad.yaml" in result["violations"]
        assert "grace_state.json" not in result["violations"]

