from typing import Optional
from src.grace.models import DevelopmentPlan, Wave


def _find_wave(plan: DevelopmentPlan, wave_id: Optional[str] = None) -> Wave:
    if wave_id:
        for phase in plan.phases:
            for wave in phase.waves:
                if wave.id == wave_id:
                    return wave
        raise ValueError(f"Wave {wave_id!r} not found")
    if plan.phases and plan.phases[0].waves:
        return plan.phases[0].waves[0]
    raise ValueError("DevelopmentPlan is empty")


def generate_controller_packet(
    plan: DevelopmentPlan,
    wave_id: Optional[str] = None,
) -> str:
    wave = _find_wave(plan, wave_id)

    phase_id = ""
    for phase in plan.phases:
        if wave in phase.waves:
            phase_id = phase.id
            break

    modules_str = ", ".join(wave.modules) if wave.modules else "N/A"
    scope_lines = "\n".join(f"- `{f}`" for f in wave.allowed_write_scope)
    frozen_lines = "\n".join(f"- `{f}`" for f in wave.frozen_scope)
    preserve_lines = "\n".join(f"- {item}" for item in wave.must_preserve)
    verif_lines = "\n".join(f"- `{cmd}`" for cmd in wave.verification)

    return f"""# Controller Packet — {phase_id} / {wave.id}

## IDs
- Phase: {phase_id}
- Wave: {wave.id}
- Modules: {modules_str}

## Goal
{wave.goal}

## Allowed Write Scope
{scope_lines}

## Frozen / Out Of Scope
{frozen_lines}

## Must Preserve
{preserve_lines}

## Verification
{verif_lines}

## Expected Evidence
- Files modified strictly within Allowed Write Scope.
- Verification commands exit with code 0.
- Return `Worker Result Packet` with changed files list and verification stdout.

## Escalation
- If the implementation requires modifying a file from Frozen / Out Of Scope, stop and return an Escalation Packet.
- If verification fails after 2-3 attempts, stop and return a Failure Packet.
- If the Goal conflicts with Must Preserve invariants, stop and request a new Controller Packet.
"""
