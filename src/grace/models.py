"""
START_MODULE_CONTRACT: M-MODELS
 purpose: Canonical data model for GRACE execution artifacts
 owns:
   - src/grace/models.py
 inputs:
   - XML artifacts (development-plan.xml)
   - YAML config (grace_config.yaml)
 outputs:
   - Typed dataclasses: Plan, Phase, Wave, AgentProfile, ExecutionConfig
 dependencies:
   - dataclasses, typing, xml.etree
 side_effects:
   - none (pure data)
 invariants:
   - All IDs are non-empty strings
   - Wave.allowed_write_scope is never None (empty list ok)
   - AgentProfile.priority > 0
 failure_policy:
   - ValueError on malformed required fields
   - Missing optional fields get sensible defaults
 non_goals:
   - No I/O beyond XML parsing
   - No execution logic
END_MODULE_CONTRACT: M-MODELS
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Agent / Execution configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentProfile:
    name: str
    model: str
    api_url: str
    priority: int = 100
    effort: str = "medium"
    timeout_seconds: int = 600
    roles: List[str] = field(default_factory=lambda: ["coder"])

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("AgentProfile.name must not be empty")
        if self.priority <= 0:
            raise ValueError(f"AgentProfile.priority must be > 0, got {self.priority}")
        valid_efforts = {"low", "medium", "high", "xhigh"}
        if self.effort not in valid_efforts:
            raise ValueError(f"effort must be one of {valid_efforts}, got '{self.effort}'")


@dataclass
class ExecutionConfig:
    profiles: List[AgentProfile] = field(default_factory=list)
    max_retries: int = 3
    progress_timeout: int = 600
    absolute_timeout: int = 3600
    worktree_isolation: bool = False
    evidence_dir: str = ".grace/evidence"
    log_dir: str = ".grace/logs"


# ---------------------------------------------------------------------------
# Plan / Phase / Wave
# ---------------------------------------------------------------------------

@dataclass
class Wave:
    id: str
    goal: str
    modules: List[str] = field(default_factory=list)
    allowed_write_scope: List[str] = field(default_factory=list)
    frozen_scope: List[str] = field(default_factory=list)
    must_preserve: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    deferred_work: List[str] = field(default_factory=list)
    trace_assertions: List[str] = field(default_factory=list)
    use_case_refs: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Wave.id must not be empty")
        if not self.goal:
            raise ValueError("Wave.goal must not be empty")


@dataclass
class Phase:
    id: str
    goal: str
    waves: List[Wave] = field(default_factory=list)
    gate_criteria: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Phase.id must not be empty")
        if not self.goal:
            raise ValueError("Phase.goal must not be empty")


@dataclass
class Plan:
    phases: List[Phase] = field(default_factory=list)

    def get_wave(self, wave_id: str) -> Optional[Wave]:
        for phase in self.phases:
            for wave in phase.waves:
                if wave.id == wave_id:
                    return wave
        return None

    def get_phase_for_wave(self, wave_id: str) -> Optional[Phase]:
        for phase in self.phases:
            for wave in phase.waves:
                if wave.id == wave_id:
                    return phase
        return None


# ---------------------------------------------------------------------------
# XML parsing (backward-compatible)
# ---------------------------------------------------------------------------

def _text_list(element, tag: str) -> List[str]:
    if element is None:
        return []
    return [child.text.strip() for child in element.findall(tag) if child is not None and child.text]


def _parse_wave(wave_el: ET.Element) -> Wave:
    wave_id = wave_el.get("id", "")
    goal_el = wave_el.find("Goal")
    goal = goal_el.text.strip() if goal_el is not None and goal_el.text else ""

    modules = [ref.get("id", "") for ref in wave_el.findall("ModuleRef")]

    allowed_el = wave_el.find("AllowedWriteScope")
    allowed = _text_list(allowed_el, "File")

    frozen_el = wave_el.find("FrozenScope")
    frozen = _text_list(frozen_el, "File")

    preserve_el = wave_el.find("MustPreserve")
    preserve = _text_list(preserve_el, "Item")
    if not preserve and preserve_el is not None:
        preserve = _text_list(preserve_el, "Invariant")

    verification_el = wave_el.find("Verification")
    verification = _text_list(verification_el, "Command")

    acceptance_el = wave_el.find("AcceptanceCriteria")
    acceptance = _text_list(acceptance_el, "Criterion")

    deferred_el = wave_el.find("DeferredWork")
    deferred = _text_list(deferred_el, "Item")

    trace_el = wave_el.find("TraceAssertions")
    traces = _text_list(trace_el, "Assertion")

    uc_el = wave_el.find("UseCaseRefs")
    use_cases = _text_list(uc_el, "Ref")

    # Support old <Modules><Module>...</Module></Modules> format
    if not modules:
        modules = _text_list(wave_el, "Modules/Module")

    return Wave(
        id=wave_id, goal=goal, modules=modules,
        allowed_write_scope=allowed, frozen_scope=frozen,
        must_preserve=preserve, verification=verification,
        acceptance_criteria=acceptance, deferred_work=deferred,
        trace_assertions=traces, use_case_refs=use_cases,
    )


def _parse_phase(phase_el: ET.Element) -> Phase:
    phase_id = phase_el.get("id", "")
    goal_el = phase_el.find("Goal")
    goal = goal_el.text.strip() if goal_el is not None and goal_el.text else ""
    waves = [_parse_wave(w) for w in phase_el.findall("Wave")]
    gate_el = phase_el.find("GateCriteria")
    gate = _text_list(gate_el, "Criterion")
    return Phase(id=phase_id, goal=goal, waves=waves, gate_criteria=gate)


def parse_development_plan(xml_path: str | Path) -> Plan:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()
    phases = [_parse_phase(p) for p in root.findall("Phase")]
    return Plan(phases=phases)


# ---------------------------------------------------------------------------
# Backward compatibility aliases
# ---------------------------------------------------------------------------
DevelopmentPlan = Plan
load_development_plan = parse_development_plan
