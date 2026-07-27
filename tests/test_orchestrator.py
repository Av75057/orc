import pytest
from unittest.mock import patch, MagicMock, ANY, ANY

from src.grace.models import DevelopmentPlan, Phase, Wave
from src.grace.orchestrator import GraceOrchestrator, OrchestratorResult
from src.grace.worker import StubWorker


def _two_wave_plan():
    return DevelopmentPlan(phases=[
        Phase(id="PHASE-1", goal="Phase 1", waves=[
            Wave(id="WAVE-1", goal="First wave", modules=["M-A"],
                 allowed_write_scope=["src/a.py"],
                 frozen_scope=["src/b.py"],
                 must_preserve=["X"], verification=["pytest a"]),
            Wave(id="WAVE-2", goal="Second wave", modules=["M-B"],
                 allowed_write_scope=["src/b.py"],
                 frozen_scope=["src/a.py"],
                 must_preserve=["Y"], verification=["pytest b"]),
        ]),
    ])


class TestInitialState:
    def test_current_wave_returns_first_wave(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.current_wave is not None
        assert orch.current_wave.id == "WAVE-1"

    def test_default_workspace(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.workspace is not None
        import os
        assert orch.workspace == os.getcwd()

    def test_custom_workspace(self):
        orch = GraceOrchestrator(_two_wave_plan(), workspace="/tmp/myproj")
        assert orch.workspace == "/tmp/myproj"


class TestRun:
    @patch("src.grace.orchestrator.subprocess.run")
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_runs_all_waves_on_success(self, mock_gen, mock_review, mock_subprocess):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {"status": "PASSED", "reason": None, "violations": [], "verification": {}}
        orch = GraceOrchestrator(_two_wave_plan())
        result = orch.run()
        assert result.status == "SUCCESS"
        assert result.waves_completed == 2

    @patch("src.grace.orchestrator.subprocess.run")
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_stops_on_review_failure(self, mock_gen, mock_review, mock_subprocess):
        mock_gen.return_value = "# Packet"
        mock_review.side_effect = [
            {"status": "PASSED", "reason": None, "violations": [], "verification": {}},
            {"status": "FAILED", "reason": "SCOPE_VIOLATION", "violations": ["infra/x.yaml"], "verification": {}},
        ]
        orch = GraceOrchestrator(_two_wave_plan())
        result = orch.run()
        assert result.status == "FAILED"
        assert result.reason == "SCOPE_VIOLATION"
        assert result.waves_completed == 1

    @patch("src.grace.orchestrator.subprocess.run")
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_passes_workspace_to_reviewer(self, mock_gen, mock_review, mock_subprocess):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {"status": "PASSED", "reason": None, "violations": [], "verification": {}}
        orch = GraceOrchestrator(_two_wave_plan(), workspace="/tmp/proj")
        orch.run()
        mock_review.assert_called_with(ANY, workspace="/tmp/proj")

    @patch("src.grace.orchestrator.subprocess.run")
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_handles_empty_plan(self, mock_gen, mock_review, mock_subprocess):
        plan = DevelopmentPlan()
        orch = GraceOrchestrator(plan)
        result = orch.run()
        assert result.status == "SUCCESS"
        assert result.waves_completed == 0

    @patch("src.grace.orchestrator.subprocess.run")
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_controller_called_with_correct_wave_ids(self, mock_gen, mock_review, mock_subprocess):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {"status": "PASSED", "reason": None, "violations": [], "verification": {}}
        orch = GraceOrchestrator(_two_wave_plan())
        orch.run()
        assert mock_gen.call_count == 2
        assert mock_gen.call_args_list[0][0][1] == "WAVE-1"
        assert mock_gen.call_args_list[1][0][1] == "WAVE-2"


