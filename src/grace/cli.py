import argparse
import json
import sys
from pathlib import Path

from src.grace.artifact_loader import load_development_plan
from src.grace.orchestrator import GraceOrchestrator
from src.grace.logger import GraceLogger


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grace",
        description="GRACE Orchestrator — strict GRACE methodology runner",
    )
    parser.add_argument(
        "plan",
        type=str,
        help="Path to development-plan.xml",
    )
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

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
        trace_id="TRACE-CLI-001",
        scenario_id="SCN-BOOT",
    )

    orchestrator = GraceOrchestrator(plan)
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
        f"Orchestrator finished with status={result.status}, "
        f"waves_completed={result.waves_completed}",
        result="ok" if result.status == "SUCCESS" else "fail",
        trace_id="TRACE-CLI-002",
        scenario_id="SCN-BOOT",
    )

    if result.status == "FAILED":
        print(result.failure_packet or "", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
