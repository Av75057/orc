import pytest
import os
from src.grace.models import DevelopmentPlan, Phase, Wave
from src.grace.controller import generate_controller_packet


def _make_plan() -> DevelopmentPlan:
    return DevelopmentPlan(phases=[
        Phase(id="PHASE-1", goal="Test phase", waves=[
            Wave(
                id="WAVE-1",
                goal="Test wave",
                modules=["M-CORE"],
                allowed_write_scope=["src/core.py", "tests/test_core.py"],
                frozen_scope=["src/legacy.py"],
                must_preserve=["Python 3.9+ compatibility"],
                verification=["python -m pytest tests/test_core.py -v"],
            ),
            Wave(
                id="WAVE-2",
                goal="Second wave",
                modules=["M-EXTRAS"],
                allowed_write_scope=["src/extras.py"],
                frozen_scope=["src/core.py"],
                must_preserve=["API stability"],
                verification=["python -m pytest tests/test_extras.py -v"],
            ),
        ]),
    ])


def _sections(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.startswith("##")]


class TestWaveSelection:
    def test_selects_first_wave_by_default(self):
        plan = _make_plan()
        packet = generate_controller_packet(plan)
        assert "WAVE-1" in packet

    def test_selects_specific_wave_by_id(self):
        plan = _make_plan()
        packet = generate_controller_packet(plan, wave_id="WAVE-2")
        assert "WAVE-2" in packet

    def test_raises_for_unknown_wave_id(self):
        plan = _make_plan()
        with pytest.raises(ValueError, match="not found"):
            generate_controller_packet(plan, wave_id="WAVE-99")

    def test_raises_for_empty_plan(self):
        plan = DevelopmentPlan()
        with pytest.raises(ValueError, match="empty"):
            generate_controller_packet(plan)


class TestPacketSections:
    PACKET_SECTIONS = [
        "IDs",
        "Goal",
        "Allowed Write Scope",
        "Frozen / Out Of Scope",
        "Must Preserve",
        "Verification",
        "Expected Evidence",
        "Escalation",
    ]

    def test_contains_all_required_sections(self):
        packet = generate_controller_packet(_make_plan())
        found = _sections(packet)
        for section in self.PACKET_SECTIONS:
            assert section in " ".join(found), f"Missing section: {section}"


class TestContextInjection:
    def test_injects_existing_file_content(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "legacy.py").write_text("def legacy_func():\n    return 42\n")

        plan = _make_plan()
        packet = generate_controller_packet(plan, workspace=str(tmp_path))
        assert "## Existing Context (Read-Only)" in packet
        assert "def legacy_func()" in packet
        assert "return 42" in packet
        assert "### `src/legacy.py`" in packet

    def test_no_context_without_workspace(self):
        plan = _make_plan()
        packet = generate_controller_packet(plan)
        assert "## Existing Context" not in packet

    def test_skips_nonexistent_files(self, tmp_path):
        plan = _make_plan()
        packet = generate_controller_packet(plan, workspace=str(tmp_path))
        assert "## Existing Context" not in packet

    def test_truncates_large_files(self, tmp_path):
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        lines = [f"line {i}" for i in range(300)]
        (src_dir / "core.py").write_text("\n".join(lines))

        plan = DevelopmentPlan(phases=[
            Phase(id="P1", goal="G", waves=[
                Wave(id="W1", goal="G", modules=[], allowed_write_scope=[],
                     frozen_scope=["src/core.py"], must_preserve=[], verification=[]),
            ]),
        ])
        packet = generate_controller_packet(plan, workspace=str(tmp_path))
        assert "file truncated" in packet
        assert "line 199" in packet
        assert "line 299" not in packet

    def test_injects_module_ref_files(self, tmp_path):
        src_dir = tmp_path / "m_core"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("VERSION = '1.0'\n")

        plan = DevelopmentPlan(phases=[
            Phase(id="P1", goal="G", waves=[
                Wave(id="W1", goal="G", modules=["m_core/__init__.py"],
                     allowed_write_scope=[], frozen_scope=[],
                     must_preserve=[], verification=[]),
            ]),
        ])
        packet = generate_controller_packet(plan, workspace=str(tmp_path))
        assert "VERSION = '1.0'" in packet

    def test_backward_compatible_no_workspace(self):
        plan = _make_plan()
        packet = generate_controller_packet(plan, wave_id="WAVE-1")
        assert "PHASE-1" in packet
        assert "WAVE-1" in packet


class TestPacketContent:
    def test_packet_starts_with_heading(self):
        packet = generate_controller_packet(_make_plan())
        assert packet.startswith("# Controller Packet \u2014")
