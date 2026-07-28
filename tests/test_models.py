import pytest
import tempfile
from pathlib import Path
from src.grace.models import (
    AgentProfile, ExecutionConfig, Phase, Plan, Wave,
    parse_development_plan, DevelopmentPlan, load_development_plan,
)


class TestAgentProfile:
    def test_valid_profile(self):
        p = AgentProfile(name="coder-test", model="deepseek-chat", api_url="https://api.deepseek.com/chat/completions", priority=300, effort="medium", timeout_seconds=600, roles=["coder"])
        assert p.name == "coder-test"
        assert p.priority == 300

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            AgentProfile(name="", model="m", api_url="u")

    def test_zero_priority_raises(self):
        with pytest.raises(ValueError, match="priority must be > 0"):
            AgentProfile(name="x", model="m", api_url="u", priority=0)

    def test_invalid_effort_raises(self):
        with pytest.raises(ValueError, match="effort must be one of"):
            AgentProfile(name="x", model="m", api_url="u", effort="ultra")

    def test_default_roles(self):
        p = AgentProfile(name="x", model="m", api_url="u")
        assert p.roles == ["coder"]

    def test_default_effort(self):
        p = AgentProfile(name="x", model="m", api_url="u")
        assert p.effort == "medium"


class TestWave:
    def test_minimal_wave(self):
        w = Wave(id="WAVE-1", goal="Test")
        assert w.acceptance_criteria == []
        assert w.deferred_work == []
        assert w.trace_assertions == []
        assert w.use_case_refs == []

    def test_full_wave(self):
        w = Wave(id="WAVE-2", goal="Full", modules=["M-A"], allowed_write_scope=["a.py"], frozen_scope=["b.py"], must_preserve=["inv"], verification=["pytest"], acceptance_criteria=["green"], deferred_work=["later"], trace_assertions=["A->B"], use_case_refs=["UC-1"])
        assert len(w.acceptance_criteria) == 1
        assert len(w.trace_assertions) == 1

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="Wave.id must not be empty"):
            Wave(id="", goal="g")

    def test_empty_goal_raises(self):
        with pytest.raises(ValueError, match="Wave.goal must not be empty"):
            Wave(id="W", goal="")


class TestPhase:
    def test_minimal_phase(self):
        p = Phase(id="PHASE-1", goal="Goal")
        assert p.gate_criteria == []

    def test_phase_with_gate(self):
        p = Phase(id="PHASE-1", goal="Goal", gate_criteria=["all green"])
        assert len(p.gate_criteria) == 1

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="Phase.id must not be empty"):
            Phase(id="", goal="g")


class TestPlan:
    def _make(self):
        return Plan(phases=[Phase(id="P1", goal="Phase 1", waves=[Wave(id="W1", goal="First")]), Phase(id="P2", goal="Phase 2", waves=[Wave(id="W2", goal="Second")])])

    def test_get_wave(self):
        w = self._make().get_wave("W2")
        assert w is not None and w.goal == "Second"

    def test_get_wave_not_found(self):
        assert self._make().get_wave("W99") is None

    def test_get_phase_for_wave(self):
        phase = self._make().get_phase_for_wave("W1")
        assert phase is not None and phase.id == "P1"


_OLD_XML = """<DevelopmentPlan>
  <Phase id="PHASE-1">
    <Goal>Old phase</Goal>
    <Wave id="WAVE-1">
      <Goal>Old wave</Goal>
      <ModuleRef id="M-CORE" />
      <AllowedWriteScope><File>core.py</File></AllowedWriteScope>
      <Verification><Command>pytest</Command></Verification>
    </Wave>
  </Phase>
</DevelopmentPlan>"""

_NEW_XML = """<DevelopmentPlan>
  <Phase id="PHASE-1">
    <Goal>New phase</Goal>
    <GateCriteria><Criterion>All green</Criterion></GateCriteria>
    <Wave id="WAVE-1">
      <Goal>New wave</Goal>
      <ModuleRef id="M-CORE" />
      <AllowedWriteScope><File>core.py</File></AllowedWriteScope>
      <FrozenScope><File>frozen.py</File></FrozenScope>
      <MustPreserve><Item>API contract</Item></MustPreserve>
      <Verification><Command>pytest</Command></Verification>
      <AcceptanceCriteria><Criterion>Tests pass</Criterion></AcceptanceCriteria>
      <DeferredWork><Item>UI polish</Item></DeferredWork>
      <TraceAssertions><Assertion>init->complete</Assertion></TraceAssertions>
      <UseCaseRefs><Ref>UC-1</Ref></UseCaseRefs>
    </Wave>
  </Phase>
</DevelopmentPlan>"""


class TestParse:
    def test_backward_compat(self, tmp_path):
        f = tmp_path / "plan.xml"; f.write_text(_OLD_XML)
        plan = parse_development_plan(f)
        wave = plan.phases[0].waves[0]
        assert wave.id == "WAVE-1" and wave.goal == "Old wave"
        assert wave.modules == ["M-CORE"]
        assert wave.acceptance_criteria == []

    def test_new_xml(self, tmp_path):
        f = tmp_path / "plan.xml"; f.write_text(_NEW_XML)
        plan = parse_development_plan(f)
        wave = plan.phases[0].waves[0]
        assert wave.frozen_scope == ["frozen.py"]
        assert wave.must_preserve == ["API contract"]
        assert wave.acceptance_criteria == ["Tests pass"]
        assert wave.deferred_work == ["UI polish"]
        assert wave.trace_assertions == ["init->complete"]
        assert wave.use_case_refs == ["UC-1"]
        assert plan.phases[0].gate_criteria == ["All green"]

    def test_backward_alias(self, tmp_path):
        f = tmp_path / "plan.xml"; f.write_text(_OLD_XML)
        plan = load_development_plan(f)
        assert isinstance(plan, DevelopmentPlan)
        assert isinstance(plan, Plan)
