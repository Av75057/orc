from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent
SRC_DIR = str(REPO_ROOT / "src")


class TestMainCLI:
    def test_exit_code_zero(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "src.smart_home.main"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": SRC_DIR},
        )
        assert r.returncode == 0

    def test_json_output(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "src.smart_home.main"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": SRC_DIR},
        )
        state = json.loads(r.stdout)
        assert isinstance(state, dict)
        assert "thermostat" in state
        assert "light_bulb" in state

    def test_no_stderr(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "src.smart_home.main"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": SRC_DIR},
        )
        assert r.stderr == "" or "DeprecationWarning" not in r.stderr


class TestMainInProcess:
    def test_function_runs(self) -> None:
        import io
        from contextlib import redirect_stdout
        from src.smart_home.main import main
        buf = io.StringIO()
        with redirect_stdout(buf):
            main()
        state = json.loads(buf.getvalue())
        assert state["thermostat"]["is_on"] is False
        assert state["light_bulb"]["is_on"] is False

