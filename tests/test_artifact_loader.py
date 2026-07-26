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
    assert len(plan.phases) == 1


def test_load_development_plan_phase_fields():
    plan = load_development_plan(_xml_path())
    phase = plan.phases[0]
    assert phase.id == "PHASE-1"
    assert "artifact-driven" in phase.goal
    assert len(phase.waves) == 1


def test_load_development_plan_wave_fields():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert wave.id == "WAVE-1"
    assert "data models" in wave.goal
    assert "M-ARTIFACTS" in wave.modules
    assert "M-CORE" in wave.modules


def test_load_development_plan_allowed_write_scope():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert "src/grace/models.py" in wave.allowed_write_scope
    assert "src/grace/artifact_loader.py" in wave.allowed_write_scope
    assert "tests/test_artifact_loader.py" in wave.allowed_write_scope
    assert "docs/development-plan.xml" in wave.allowed_write_scope


def test_load_development_plan_frozen_scope():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert "src/grace/controller.py" in wave.frozen_scope
    assert "infra/*" in wave.frozen_scope
    assert "frontend/*" in wave.frozen_scope


def test_load_development_plan_must_preserve():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    items = wave.must_preserve
    assert any("Python 3.9" in item for item in items)
    assert any("Standard library" in item for item in items)
    assert any("side effects" in item for item in items)


def test_load_development_plan_verification():
    plan = load_development_plan(_xml_path())
    wave = plan.phases[0].waves[0]
    assert any("pytest" in cmd for cmd in wave.verification)


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
