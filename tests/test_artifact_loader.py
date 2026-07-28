import pytest
import os
from pathlib import Path
from src.grace.models import DevelopmentPlan, Phase, Wave
from src.grace.artifact_loader import load_development_plan


def _xml_path(filename: str = "development-plan.xml") -> str:
    return str(Path(__file__).resolve().parents[1] / "docs" / filename)


def test_load_development_plan_returns_correct_structure():
    plan = load_development_plan(_xml_path())
    assert isinstance(plan, DevelopmentPlan)
    assert len(plan.phases) >= 1


def test_load_development_plan_phase_fields():
    plan = load_development_plan(_xml_path())
    phase = plan.phases[0]
    assert phase.id == "PHASE-1"
    assert "EventBus" in phase.goal
    assert len(phase.waves) == 1


def test_load_development_plan_wave_fields():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert wave.id == "WAVE-1"
    assert "eventbus" in wave.goal.lower()
    assert "M-MODELS" in wave.modules
    assert "M-EVENTBUS" in wave.modules


def test_load_development_plan_allowed_write_scope():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert "src/smart_home/models.py" in wave.allowed_write_scope
    assert "src/smart_home/event_bus.py" in wave.allowed_write_scope


def test_load_development_plan_frozen_scope():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert "src/smart_home/sensors.py" in wave.frozen_scope
    assert "src/smart_home/actuators.py" in wave.frozen_scope
    assert "docs/*" in wave.frozen_scope


def test_load_development_plan_verification():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert any("PYTHONPATH=src" in cmd for cmd in wave.verification)


def test_load_development_plan_invalid_xml_raises():
    path = _xml_path("nonexistent.xml")
    with pytest.raises((FileNotFoundError, OSError)):
        load_development_plan(path)


def test_load_development_plan_wrong_root_raises():
    bad_xml = Path(_xml_path()).parent / "_bad_test.xml"
    bad_xml.write_text("<WrongRoot><Item /></WrongRoot>")
    try:
        with pytest.raises(ValueError, match="DevelopmentPlan"):
            load_development_plan(str(bad_xml))
    finally:
        bad_xml.unlink()



