import pytest
from src.grace.models import Plan, Phase, Wave
from src.grace.controller import generate_controller_packet


def _make_plan():
    return Plan(phases=[
        Phase(id="PHASE-1", goal="Test phase", waves=[
            Wave(id="WAVE-1", goal="Test wave", modules=["M-CORE"],
                 allowed_write_scope=["src/core.py", "tests/test_core.py"],
                 frozen_scope=["src/legacy.py"],
                 must_preserve=["Python 3.9+ compatibility"],
                 verification=["python -m pytest tests/test_core.py -v"]),
            Wave(id="WAVE-2", goal="Second wave", modules=["M-EXTRAS"],
                 allowed_write_scope=["src/extras.py"],
                 frozen_scope=["src/core.py"],
                 must_preserve=["API stability"],
                 verification=["python -m pytest tests/test_extras.py -v"]),
        ]),
    ])


def _sections(text: str) -> list[str]:
    return [line.strip() for line in text.split("\n") if line.startswith("##")]


class TestWaveSelection:
    def test_selects_first_wave_by_default(self):
        packet = generate_controller_packet(_make_plan())
        assert "WAVE-1" in packet

    def test_selects_specific_wave(self):
        packet = generate_controller_packet(_make_plan(), wave_id="WAVE-2")
        assert "WAVE-2" in packet

    def test_raises_for_unknown_wave(self):
        with pytest.raises(ValueError):
            generate_controller_packet(_make_plan(), wave_id="WAVE-99")

    def test_raises_for_empty_plan(self):
        plan = Plan()
        with pytest.raises(ValueError):
            generate_controller_packet(plan)


class TestPacketSections:
    SECTIONS = ["IDs", "Goal", "Allowed Write Scope", "Frozen / Out Of Scope",
                "Must Preserve", "Verification", "Expected Evidence", "Escalation"]

    def test_contains_all_sections(self):
        found = _sections(generate_controller_packet(_make_plan()))
        for s in self.SECTIONS:
            assert s in " ".join(found), f"Missing: {s}"


class TestPacketContent:
    def test_id_section(self):
        packet = generate_controller_packet(_make_plan())
        assert "PHASE-1" in packet and "WAVE-1" in packet and "M-CORE" in packet

    def test_goal_section(self):
        assert "Test wave" in generate_controller_packet(_make_plan())

    def test_write_scope(self):
        packet = generate_controller_packet(_make_plan())
        assert "src/core.py" in packet and "tests/test_core.py" in packet

    def test_frozen_scope(self):
        assert "src/legacy.py" in generate_controller_packet(_make_plan())

    def test_must_preserve(self):
        assert "Python 3.9" in generate_controller_packet(_make_plan())

    def test_verification(self):
        assert "pytest" in generate_controller_packet(_make_plan())

    def test_starts_with_heading(self):
        assert generate_controller_packet(_make_plan()).startswith("# Controller Packet")

