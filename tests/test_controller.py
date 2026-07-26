import pytest
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

    def test_sections_in_correct_order(self):
        packet = generate_controller_packet(_make_plan())
        found = _sections(packet)
        expected = [f"## {s}" for s in self.PACKET_SECTIONS]
        for i, exp in enumerate(expected):
            assert found[i] == exp, f"Position {i}: expected {exp!r}, got {found[i]!r}"


class TestPacketContent:
    def test_id_section_contains_phase_and_wave(self):
        packet = generate_controller_packet(_make_plan())
        assert "PHASE-1" in packet
        assert "WAVE-1" in packet
        assert "M-CORE" in packet

    def test_goal_section_contains_wave_goal(self):
        packet = generate_controller_packet(_make_plan())
        assert "Test wave" in packet

    def test_allowed_write_scope_lists_files(self):
        packet = generate_controller_packet(_make_plan())
        assert "src/core.py" in packet
        assert "tests/test_core.py" in packet

    def test_frozen_scope_lists_files(self):
        packet = generate_controller_packet(_make_plan())
        assert "src/legacy.py" in packet

    def test_must_preserve_lists_items(self):
        packet = generate_controller_packet(_make_plan())
        assert "Python 3.9+ compatibility" in packet

    def test_verification_lists_commands(self):
        packet = generate_controller_packet(_make_plan())
        assert "python -m pytest tests/test_core.py -v" in packet

    def test_packet_starts_with_heading(self):
        packet = generate_controller_packet(_make_plan())
        assert packet.startswith("# Controller Packet —")

    def test_packet_generated_for_second_wave(self):
        packet = generate_controller_packet(_make_plan(), wave_id="WAVE-2")
        assert "WAVE-2" in packet
        assert "M-EXTRAS" in packet
        assert "src/extras.py" in packet
        assert "API stability" in packet
        assert "tests/test_extras.py" in packet
