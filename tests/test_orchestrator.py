import pytest
from unittest.mock import patch, MagicMock

from src.grace.models import DevelopmentPlan, Phase, Wave
from src.grace.orchestrator import GraceOrchestrator, OrchestratorResult


def _two_wave_plan() -> DevelopmentPlan:
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


def _two_phase_plan() -> DevelopmentPlan:
    return DevelopmentPlan(phases=[
        Phase(id="PHASE-1", goal="Phase 1", waves=[
            Wave(id="WAVE-1", goal="W1", modules=["M-A"],
                 allowed_write_scope=["src/a.py"],
                 frozen_scope=[], must_preserve=[], verification=[]),
        ]),
        Phase(id="PHASE-2", goal="Phase 2", waves=[
            Wave(id="WAVE-2", goal="W2", modules=["M-B"],
                 allowed_write_scope=["src/b.py"],
                 frozen_scope=[], must_preserve=[], verification=[]),
        ]),
    ])


class TestInitialState:
    def test_current_wave_returns_first_wave(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.current_wave is not None
        assert orch.current_wave.id == "WAVE-1"

    def test_current_wave_returns_none_for_empty_plan(self):
        plan = DevelopmentPlan()
        orch = GraceOrchestrator(plan)
        assert orch.current_wave is None

    def test_current_phase_returns_first_phase(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.current_phase is not None
        assert orch.current_phase.id == "PHASE-1"

    def test_has_next_with_two_waves(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.has_next is True


class TestAdvance:
    def test_advance_moves_to_next_wave(self):
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch._advance() is True
        assert orch.current_wave.id == "WAVE-2"

    def test_advance_returns_false_at_end(self):
        orch = GraceOrchestrator(_two_wave_plan())
        orch._advance()
        assert orch._advance() is False
        assert orch.current_wave is None

    def test_advance_moves_to_next_phase(self):
        orch = GraceOrchestrator(_two_phase_plan())
        assert orch._advance() is True
        assert orch.current_phase.id == "PHASE-2"
        assert orch.current_wave.id == "WAVE-2"


class TestRun:
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_runs_all_waves_on_success(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {
            "status": "PASSED", "reason": None,
            "violations": [], "verification": {},
        }
        orch = GraceOrchestrator(_two_wave_plan())
        result = orch.run()
        assert result.status == "SUCCESS"
        assert result.waves_completed == 2

    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_stops_on_review_failure(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.side_effect = [
            {"status": "PASSED", "reason": None, "violations": [], "verification": {}},
            {"status": "FAILED", "reason": "SCOPE_VIOLATION",
             "violations": ["infra/x.yaml"], "verification": {}},
        ]
        orch = GraceOrchestrator(_two_wave_plan())
        result = orch.run()
        assert result.status == "FAILED"
        assert result.reason == "SCOPE_VIOLATION"
        assert result.waves_completed == 1
        assert result.failure_packet is not None
        assert "FAILED" in result.failure_packet

    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_runs_single_wave_plan(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {
            "status": "PASSED", "reason": None,
            "violations": [], "verification": {},
        }
        plan = DevelopmentPlan(phases=[
            Phase(id="PHASE-1", goal="G", waves=[
                Wave(id="WAVE-1", goal="W1", modules=[],
                     allowed_write_scope=[], frozen_scope=[],
                     must_preserve=[], verification=[]),
            ]),
        ])
        orch = GraceOrchestrator(plan)
        result = orch.run()
        assert result.status == "SUCCESS"
        assert result.waves_completed == 1

    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_handles_empty_plan(self, mock_gen, mock_review):
        plan = DevelopmentPlan()
        orch = GraceOrchestrator(plan)
        result = orch.run()
        assert result.status == "SUCCESS"
        assert result.waves_completed == 0

    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_controller_called_with_correct_wave_ids(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {
            "status": "PASSED", "reason": None,
            "violations": [], "verification": {},
        }
        orch = GraceOrchestrator(_two_wave_plan())
        orch.run()
        assert mock_gen.call_count == 2
        assert mock_gen.call_args_list[0][0][1] == "WAVE-1"
        assert mock_gen.call_args_list[1][0][1] == "WAVE-2"


class TestExecuteWorkerTask:
    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_worker_stub_returns_true_by_default(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {
            "status": "PASSED", "reason": None,
            "violations": [], "verification": {},
        }
        orch = GraceOrchestrator(_two_wave_plan())
        assert orch.execute_worker_task("# Packet") is True

    @patch("src.grace.orchestrator.review_wave")
    @patch("src.grace.orchestrator.generate_controller_packet")
    def test_can_override_worker_to_fail(self, mock_gen, mock_review):
        mock_gen.return_value = "# Packet"
        mock_review.return_value = {
            "status": "PASSED", "reason": None,
            "violations": [], "verification": {},
        }
        orch = GraceOrchestrator(_two_wave_plan())
        orch.execute_worker_task = MagicMock(return_value=False)
        result = orch.run()
        assert result.status == "FAILED"
        assert "Worker task execution failed" in result.failure_packet


class TestOrchestratorResult:
    def test_result_dataclass_defaults(self):
        r = OrchestratorResult(status="SUCCESS")
        assert r.waves_completed == 0
        assert r.reason is None
        assert r.failure_packet is None
