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
        assert "All tests passed!" in results["pytest tests/"]["stdout"]

    @patch("src.grace.reviewer.subprocess.run")
    def test_failing_command(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="FAILED test_a.py::test_foo",
        )
        results = run_verification(["pytest tests/"])
        assert results["pytest tests/"]["returncode"] == 1

    @patch("src.grace.reviewer.subprocess.run")
    def test_multiple_commands(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="OK", stderr="",
        )
        results = run_verification(["lint", "test"])
        assert list(results.keys()) == ["lint", "test"]

    @patch("src.grace.reviewer.subprocess.run")
    def test_shell_true_for_command(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="OK", stderr="",
        )
        run_verification(["echo hello"])
        mock_run.assert_called_once_with(
            "echo hello", shell=True, capture_output=True, text=True, check=False,
        )


class TestReviewWave:
    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_passed_when_scope_ok_and_verification_ok(
        self, mock_verif, mock_git
    ):
        mock_git.return_value = ["src/grace/models.py"]
        mock_verif.return_value = {
            "pytest": {"returncode": 0, "stdout": "OK", "stderr": ""},
        }
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/grace/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["status"] == "PASSED"
        assert result["reason"] is None
        assert result["violations"] == []

    @patch("src.grace.reviewer.get_changed_files")
    def test_failed_on_scope_violation(self, mock_git):
        mock_git.return_value = ["infra/deploy.yaml", "src/grace/models.py"]
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/grace/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["status"] == "FAILED"
        assert result["reason"] == "SCOPE_VIOLATION"
        assert "infra/deploy.yaml" in result["violations"]
        assert "src/grace/models.py" not in result["violations"]

    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_failed_on_verification_failure(self, mock_verif, mock_git):
        mock_git.return_value = ["src/grace/models.py"]
        mock_verif.return_value = {
            "pytest": {"returncode": 1, "stdout": "", "stderr": "FAILED"},
        }
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/grace/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["status"] == "FAILED"
        assert result["reason"] == "VERIFICATION_FAILED"
        assert result["violations"] == []

    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_excludes_state_and_evidence(self, mock_verif, mock_git):
        mock_git.return_value = [
            "src/app.py",
            "grace_state.json",
            "evidence/T1/log.txt",
            "__pycache__/cli.cpython-312.pyc",
            ".pytest_cache/v/cache/lastfailed",
        ]
        mock_verif.return_value = {
            "pytest": {"returncode": 0, "stdout": "OK", "stderr": ""},
        }
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["status"] == "PASSED"
        assert result["reason"] is None

    @patch("src.grace.reviewer.get_changed_files")
    def test_excludes_state_but_catches_other_violations(self, mock_git):
        mock_git.return_value = [
            "src/app.py",
            "grace_state.json",
            "evidence/T1/log.txt",
            "__pycache__/cli.pyc",
            "infra/bad.yaml",
        ]
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["status"] == "FAILED"
        assert result["reason"] == "SCOPE_VIOLATION"
        assert "infra/bad.yaml" in result["violations"]
        assert "grace_state.json" not in result["violations"]
        assert "evidence/T1/log.txt" not in result["violations"]
        assert "__pycache__/cli.pyc" not in result["violations"]

    @patch("src.grace.reviewer.get_changed_files")
    @patch("src.grace.reviewer.run_verification")
    def test_verification_not_run_on_scope_violation(self, mock_verif, mock_git):
        mock_git.return_value = ["infra/deploy.yaml"]
        wave = Wave(
            id="WAVE-1",
            goal="test",
            allowed_write_scope=["src/grace/*"],
            verification=["pytest"],
        )
        result = review_wave(wave)
        assert result["verification"] == {}
        mock_verif.assert_not_called()


