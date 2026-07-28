"""
START_MODULE_CONTRACT: M-CONTROLLER
 purpose: Generate controller packets from Plan/Wave data per GRACE canon
 owns:
   - src/grace/controller.py
 inputs:
   - Plan, Phase, Wave, workspace path
 outputs:
   - Markdown controller packet string
 dependencies:
   - models.Plan, models.Phase, models.Wave
 side_effects:
   - none (pure string generation)
 invariants:
   - Packet always contains: IDs, Goal, Allowed Write Scope,
     Frozen, Must Preserve, Verification, Expected Evidence, Escalation
   - New fields included when non-empty
 failure_policy:
   - ValueError if wave not found in plan
 non_goals:
   - Does not execute anything
   - Does not modify files
END_MODULE_CONTRACT: M-CONTROLLER
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import Plan


def generate_controller_packet(
    plan: Plan,
    wave_id: str = "",
    workspace: str | Path = ".",
) -> str:
    if not wave_id:
        wave = plan.phases[0].waves[0] if plan.phases and plan.phases[0].waves else None
    else:
        wave = plan.get_wave(wave_id)
    if wave is None:
        raise ValueError(f"Wave not found in plan")

    phase = plan.get_phase_for_wave(wave.id)
    phase_id = phase.id if phase else "UNKNOWN"

    lines: list[str] = []
    lines.append(f"# Controller Packet — {wave.id}")
    lines.append("")
    lines.append("## IDs")
    lines.append(f"- Phase: {phase_id}")
    lines.append(f"- Wave: {wave.id}")
    lines.append(f"- Modules: {', '.join(wave.modules) if wave.modules else 'N/A'}")
    if wave.use_case_refs:
        lines.append(f"- Use Cases: {', '.join(wave.use_case_refs)}")
    lines.append("")
    lines.append("## Goal")
    lines.append(wave.goal)
    lines.append("")
    lines.append("## Allowed Write Scope")
    if wave.allowed_write_scope:
        for f in wave.allowed_write_scope:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (not specified)")
    lines.append("")
    lines.append("## Frozen / Out Of Scope")
    if wave.frozen_scope:
        for f in wave.frozen_scope:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (not specified)")
    lines.append("")
    lines.append("## Must Preserve")
    if wave.must_preserve:
        for item in wave.must_preserve:
            lines.append(f"- {item}")
    else:
        lines.append("- (not specified)")
    lines.append("")
    lines.append("## Verification")
    if wave.verification:
        for cmd in wave.verification:
            lines.append(f"- `{cmd}`")
    else:
        lines.append("- (not specified)")
    lines.append("")
    if wave.acceptance_criteria:
        lines.append("## Acceptance Criteria")
        for c in wave.acceptance_criteria:
            lines.append(f"- {c}")
        lines.append("")
    if wave.trace_assertions:
        lines.append("## Trace Assertions")
        for a in wave.trace_assertions:
            lines.append(f"- {a}")
        lines.append("")
    if wave.deferred_work:
        lines.append("## Deferred Work")
        for d in wave.deferred_work:
            lines.append(f"- {d}")
        lines.append("")
    lines.append("## Expected Evidence")
    lines.append("- files changed")
    lines.append("- commands run")
    lines.append("- test results")
    lines.append("- residual risks")
    lines.append("")
    lines.append("## Escalation")
    lines.append("If neighbor scope / schema / frontend / infra change is required, stop and request a new packet.")
    lines.append("")
    return "\n".join(lines)


