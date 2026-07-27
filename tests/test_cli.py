import pytest
from unittest.mock import patch, MagicMock
from src.grace.cli import create_parser, main


class TestCreateParser:
    def test_parser_requires_plan_argument(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_accepts_plan_path(self):
        parser = create_parser()
        args = parser.parse_args(["docs/development-plan.xml"])
        assert args.plan == "docs/development-plan.xml"

    def test_parser_accepts_workspace(self):
        parser = create_parser()
        args = parser.parse_args(["--workspace", "/tmp/proj", "plan.xml"])
        assert args.workspace == "/tmp/proj"


class TestMain:
    @patch("src.grace.cli.load_development_plan")
    @patch("src.grace.cli.GraceOrchestrator")
    def test_main_success_path(self, mock_orch_cls, mock_load):
        mock_load.return_value = MagicMock(phases=[MagicMock()])
        mock_orch = MagicMock()
        mock_orch.run.return_value = MagicMock(status="SUCCESS", waves_completed=2, completed_wave_ids=["WAVE-1","WAVE-2"], failure_packet=None)
        mock_orch_cls.return_value = mock_orch
        code = main(["docs/test.xml"])
        assert code == 0

    @patch("src.grace.cli.load_development_plan")
    def test_main_returns_1_on_load_failure(self, mock_load):
        mock_load.side_effect = FileNotFoundError("not found")
        code = main(["docs/missing.xml"])
        assert code == 1

    @patch("src.grace.cli.load_development_plan")
    @patch("src.grace.cli.GraceOrchestrator")
    def test_main_passes_workspace(self, mock_orch_cls, mock_load):
        mock_load.return_value = MagicMock(phases=[MagicMock()])
        mock_orch = MagicMock()
        mock_orch.run.return_value = MagicMock(status="SUCCESS", waves_completed=1, completed_wave_ids=["WAVE-1"], failure_packet=None)
        mock_orch_cls.return_value = mock_orch
        code = main(["--workspace", "/tmp/proj", "docs/test.xml"])
        assert code == 0
        mock_orch_cls.assert_called_once()
        assert mock_orch_cls.call_args[1]["workspace"] == "/tmp/proj"

    @patch("src.grace.cli.load_development_plan")
    @patch("src.grace.cli.GraceOrchestrator")
    def test_main_returns_1_on_failure_status(self, mock_orch_cls, mock_load):
        mock_load.return_value = MagicMock(phases=[MagicMock()])
        mock_orch = MagicMock()
        mock_orch.run.return_value = MagicMock(status="FAILED", waves_completed=1, completed_wave_ids=[], failure_packet="# Fail", reason="Test failure")
        mock_orch_cls.return_value = mock_orch
        code = main(["docs/test.xml"])
        assert code == 1



