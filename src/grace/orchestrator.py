import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from src.grace.models import DevelopmentPlan, Wave, Phase
from src.grace.artifact_loader import load_development_plan
from src.grace.controller import generate_controller_packet
from src.grace.reviewer import review_wave
import subprocess

from src.grace.worker import GraceWorker, StubWorker


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

    def _build_failure_packet(self, reason: str) -> str:
        wave = self.current_wave
        phase = self.current_phase
        wave_id = wave.id if wave else "N/A"
        phase_id = phase.id if phase else "N/A"
        return f"""# Orchestrator Failure Packet

## Status: FAILED

## Execution Context
- Phase: {phase_id}
- Wave: {wave_id}

## Reason
{reason}

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

    def _save_evidence(self, wave_id: str, stdout_text: str):
        import os as _os
        evidence_dir = Path(_os.getcwd()) / "evidence" / wave_id
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / "worker_stdout.txt").write_text(stdout_text)
        (evidence_dir / "controller_packet.md").write_text(self._last_packet)

    def run(self) -> OrchestratorResult:
        waves_completed = 0
        completed_ids: List[str] = []

        while self.current_wave is not None:
            wave = self.current_wave
            phase = self.current_phase
            wave_id = wave.id
            phase_id = phase.id if phase else ""

            packet = generate_controller_packet(self.plan, wave_id, workspace=self.workspace)
            self._last_packet = packet

            worker_ok = self.worker.execute(packet)
            if not worker_ok:
                return OrchestratorResult(
                    status="FAILED",
                    phase_id=phase_id,
                    wave_id=wave_id,
                    reason="Worker task execution failed",
                    waves_completed=waves_completed,
                    completed_wave_ids=completed_ids,
                    failure_packet=self._build_failure_packet(
                        "Worker task execution failed"
                    ),
                )

            self._commit_workspace(self.workspace)

            # Save evidence from captured stdout
            import io as _io, os as _os
            try:
                stdout_buf = sys.stdout
                if hasattr(stdout_buf, 'getvalue'):
                    # Can't capture here - stdout already printed
                    pass
            except:
                pass

            review = review_wave(wave, workspace=self.workspace)
            if review["status"] != "PASSED":
                reason = review.get("reason", "Unknown gate failure")
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




