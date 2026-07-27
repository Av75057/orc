"""
START_MODULE_CONTRACT: M-CONTROLLER
  purpose: Генерация controller packets из development-plan.xml.
           Фиксирует scope, verification, invariants для каждой wave.
  owns:
    - src/grace/controller.py
  inputs:
    - DevelopmentPlan (parsed)
    - wave_id, phase_id
  outputs:
    - ControllerPacket (по каноническому shape)
  dependencies:
    - M-ARTIFACT-LOADER
    - M-MODELS (ControllerPacket dataclass)
  side_effects:
    - Reads frozen-scope files for context injection
  invariants:
    - Packet содержит все MUST-поля
    - Write scope не пересекается между waves
    - Frozen scope покрывает все файлы вне write scope
  failure_policy:
    - ValueError при отсутствии wave в plan
  non_goals:
    - Не исполняет packet
    - Не проверяет результаты
END_MODULE_CONTRACT: M-CONTROLLER
"""

import os
from pathlib import Path
from typing import Optional
from src.grace.models import DevelopmentPlan, Wave

MAX_CONTEXT_LINES = 200


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


def _read_context_file(workspace: str, filepath: str) -> Optional[str]:
    full = Path(workspace) / filepath
    if not full.exists() or not full.is_file():
        return None
    try:
        lines = full.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_CONTEXT_LINES:
            return "\n".join(lines[:MAX_CONTEXT_LINES]) + "\n// ... file truncated ..."
        return "\n".join(lines)
    except (OSError, UnicodeDecodeError):
        return None


def _build_context_section(wave: Wave, workspace: Optional[str] = None) -> str:
    if not workspace:
        return ""
    files_to_read = set(wave.frozen_scope + wave.modules)
    blocks = []
    for filepath in sorted(files_to_read):
        content = _read_context_file(workspace, filepath)
        if content:
            blocks.append(f"### `{filepath}`\n```\n{content}\n```")
    if not blocks:
        return ""
    return "\n".join(["## Existing Context (Read-Only)"] + blocks)


def generate_controller_packet(
    plan: DevelopmentPlan,
    wave_id: Optional[str] = None,
    workspace: Optional[str] = None,
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
    context_section = _build_context_section(wave, workspace)

    ctx_block = f"\n\n{context_section}" if context_section else ""

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
{ctx_block}
## Expected Evidence
- Files modified strictly within Allowed Write Scope.
- Verification commands exit with code 0.
- Return `Worker Result Packet` with changed files list and verification stdout.

## Escalation
- If the implementation requires modifying a file from Frozen / Out Of Scope, stop and return an Escalation Packet.
- If verification fails after 2-3 attempts, stop and return a Failure Packet.
- If the Goal conflicts with Must Preserve invariants, stop and request a new Controller Packet.
"""



