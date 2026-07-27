import argparse
import json
import os
import sys
from pathlib import Path

from src.grace.artifact_loader import load_development_plan
from src.grace.orchestrator import GraceOrchestrator
from src.grace.logger import GraceLogger
from src.grace.worker import GraceWorker, StubWorker


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grace",
        description="GRACE Orchestrator",
    )
    parser.add_argument("plan", type=str, help="Path to development-plan.xml")
    parser.add_argument("--workspace", type=str, default=None,
                        help="Target project directory (default: current dir)")
    return parser


def _build_worker(workspace: str) -> GraceWorker:
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from src.grace.llm_worker import LLMWorker
            worker = LLMWorker(workspace=workspace)
            print(f"[CLI] OPENAI_API_KEY found. Initializing {worker.name}.", file=sys.stderr)
            return worker
        except ImportError as e:
            print(f"[CLI] LLMWorker import failed: {e}", file=sys.stderr)
    print("[CLI] No LLM API key. Using stub worker.", file=sys.stderr)
    return StubWorker(workspace=workspace)


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    workspace = args.workspace or os.getcwd()
    log = GraceLogger()

    try:
        plan = load_development_plan(args.plan)
    except Exception as e:
        log.log("M-CLI", "main", "LOAD_PLAN", "Failed to load plan", result="fail")
        print(f"Error: {e}", file=sys.stderr)
        return 1

    log.log(
        "M-CLI", "main", "LOAD_PLAN",
        f"Loaded plan with {len(plan.phases)} phase(s)",
        trace_id="TRACE-CLI-001", scenario_id="SCN-BOOT",
    )

    worker = _build_worker(workspace)
    orchestrator = GraceOrchestrator(plan, worker=worker, workspace=workspace)
    result = orchestrator.run()

    state = {
        "completed_waves": result.completed_wave_ids,
        "escalation": None if result.status == "SUCCESS" else {
            "reason": result.reason or "Unknown",
            "details": result.failure_packet or "",
        },
    }
    Path("grace_state.json").write_text(json.dumps(state, indent=2))

    log.log(
        "M-CLI", "main", "ORCHESTRATOR_RUN",
        f"Orchestrator finished with status={result.status}, waves_completed={result.waves_completed}",
        result="ok" if result.status == "SUCCESS" else "fail",
        trace_id="TRACE-CLI-002", scenario_id="SCN-BOOT",
    )

    if result.status == "FAILED":
        print(result.failure_packet or "", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

