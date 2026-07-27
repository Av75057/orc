"""
START_MODULE_CONTRACT: M-ORCHESTRATOR
  purpose: Drive phase/wave execution loop. Последовательно обходит
           waves из development-plan.xml, генерирует controller packets,
           вызывает worker, проверяет через reviewer, коммитит.
  owns:
    - src/grace/orchestrator.py
  inputs:
    - DevelopmentPlan (parsed from XML)
    - GraceWorker (implementation)
    - workspace path
  outputs:
    - OrchestratorResult (per wave: status, evidence, review)
  dependencies:
    - M-CONTROLLER (packet generation)
    - M-REVIEWER (gate checking)
    - M-WORKER (code execution)
    - M-ARTIFACT-LOADER (plan parsing)
  side_effects:
    - git commit per wave
    - evidence/ directory writes
    - structured JSON logs
  invariants:
    - Wave order strictly sequential within phase
    - Wave not skipped on failure
    - Out-of-scope files not modified
  failure_policy:
    - Build failure packet, stop execution
    - Repair loop up to 3 attempts
  non_goals:
    - Does not generate code
    - Does not modify shared artifacts
    - Does not make architectural decisions
END_MODULE_CONTRACT: M-ORCHESTRATOR

import os
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from src.grace.models import DevelopmentPlan, Wave, Phase
from src.grace.artifact_loader import load_development_plan
from src.grace.controller import generate_controller_packet
from src.grace.reviewer import review_wave
from src.grace.worker import GraceWorker, StubWorker

MAX_RETRIES = 3


@dataclass
class OrchestratorResult:
    status: str
    phase_id: str = ""
    wave_id: str = ""
    reason: Optional[str] = None
    waves_completed: int = 0
    completed_wave_ids: List[str] = field(default_factory=list)
    failure_packet: Optional[str] = None


class GraceOrchestrator:
    def __init__(self, plan: DevelopmentPlan, worker: Optional[GraceWorker] = None,
                 workspace: Optional[str] = None):
        self.plan = plan
        self.worker = worker or StubWorker(workspace=workspace)
        self.workspace = workspace or os.getcwd()
        self._phase_idx: int = 0
        self._wave_idx: int = 0

    @property
    def current_wave(self) -> Optional[Wave]:
        try:
            return self.plan.phases[self._phase_idx].waves[self._wave_idx]
        except IndexError:
            return None

    @property
    def current_phase(self) -> Optional[Phase]:
        try:
            return self.plan.phases[self._phase_idx]
        except IndexError:
            return None

    def _advance(self) -> bool:
        phase = self.plan.phases[self._phase_idx]
        if self._wave_idx + 1 < len(phase.waves):
            self._wave_idx += 1
            return True
        if self._phase_idx + 1 < len(self.plan.phases):
            self._phase_idx += 1
            self._wave_idx = 0
            return True if self.plan.phases[self._phase_idx].waves else False
        self._phase_idx = len(self.plan.phases)
        self._wave_idx = 0
        return False

    def _build_failure_packet(self, reason: str, details: str = "") -> str:
        wave = self.current_wave
        phase = self.current_phase
        wave_id = wave.id if wave else "N/A"
        phase_id = phase.id if phase else "N/A"
        detail_block = f"\n\n## Details\n```\n{details}\n```" if details else ""
        return f"""# Orchestrator Failure Packet

## Status: FAILED

## Execution Context
- Phase: {phase_id}
- Wave: {wave_id}

## Reason
{reason}
{detail_block}
## Action
Orchestrator execution stopped. Manual intervention required.
"""

    def _commit_workspace(self, ws: str):
        subprocess.run(
            ["git", "add", "-A"],
            capture_output=True, text=True, check=False, cwd=ws,
        )
        subprocess.run(
            ["git", "commit", "-m", f"auto: {self.current_wave.id} completed"],
            capture_output=True, text=True, check=False, cwd=ws,
        )

    def _process_wave(self, wave_id: str, phase_id: str) -> Optional[Dict[str, Any]]:
        packet = generate_controller_packet(self.plan, wave_id, workspace=self.workspace)
        max_api_retries = 3

        for api_attempt in range(max_api_retries):
            try:
                # Initial worker execution
                worker_ok = self.worker.execute(packet)
            except RuntimeError as e:
                msg = str(e)
                if "LLM_API_HTTP" in msg or "LLM_API_TIMEOUT" in msg or "RATE_LIMIT" in msg:
                    print(f"[ORCHESTRATOR] API error: {msg[:100]}. Retry {api_attempt + 1}/{max_api_retries}...",
                          file=__import__("sys").stderr)
                    if api_attempt < max_api_retries - 1:
                        continue
                    return {"status": "FAILED", "reason": f"Worker API failed after {max_api_retries} retries"}
                raise

            if not worker_ok:
                return {"status": "FAILED", "reason": "Worker task execution failed", "details": "Worker returned False with no error context"}

            self._commit_workspace(self.workspace)

            review = review_wave(self.current_wave, workspace=self.workspace)

            if review["status"] == "PASSED":
                return review

            if review.get("reason") == "SCOPE_VIOLATION":
                return review

            # Self-healing: retry on VERIFICATION_FAILED
            for attempt in range(1, MAX_RETRIES):
                error_output = review.get("error_output", "")
                print(f"[ORCHESTRATOR] VERIFICATION_FAILED. Repair attempt {attempt}/{MAX_RETRIES} for {wave_id}",
                      file=__import__("sys").stderr)

                try:
                    repair_ok = self.worker.execute(packet, error_context=error_output)
                except RuntimeError as e:
                    msg = str(e)
                    if "LLM_API" in msg or "RATE_LIMIT" in msg:
                        print(f"[ORCHESTRATOR] API error during repair: {msg[:100]}. Retry from api loop...",
                              file=__import__("sys").stderr)
                        break  # Go back to api retry loop
                    raise

                if not repair_ok:
                    return {"status": "FAILED", "reason": "Worker repair execution failed"}

                self._commit_workspace(self.workspace)

                review = review_wave(self.current_wave, workspace=self.workspace)

                if review["status"] == "PASSED":
                    return review

                if review.get("reason") == "SCOPE_VIOLATION":
                    return review

            else:
                # Repair loop exhausted
                return review

            # If we got here from a 'break' (API retry needed), continue the outer loop
            print(f"[ORCHESTRATOR] API retry loop: restarting wave after API issue. ({api_attempt + 1}/{max_api_retries})",
                  file=__import__("sys").stderr)
            continue

        return {"status": "FAILED", "reason": "MAX_RETRIES_EXCEEDED"}

    def run(self) -> OrchestratorResult:
        waves_completed = 0
        completed_ids: List[str] = []

        while self.current_wave is not None:
            wave = self.current_wave
            phase = self.current_phase
            wave_id = wave.id
            phase_id = phase.id if phase else ""

            result = self._process_wave(wave_id, phase_id)

            if result is None or result["status"] != "PASSED":
                reason = result.get("reason", "Unknown gate failure") if result else "Unknown"
                return OrchestratorResult(
                    status="FAILED",
                    phase_id=phase_id,
                    wave_id=wave_id,
                    reason=reason,
                    waves_completed=waves_completed,
                    completed_wave_ids=completed_ids,
                    failure_packet=self._build_failure_packet(reason),
                )

            completed_ids.append(wave_id)
            waves_completed += 1

            if not self._advance():
                break

        return OrchestratorResult(
            status="SUCCESS",
            phase_id=self.plan.phases[0].id if self.plan.phases else "",
            waves_completed=waves_completed,
            completed_wave_ids=completed_ids,
        )






