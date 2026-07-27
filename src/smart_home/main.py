"""
START_MODULE_CONTRACT: M-MAIN
  purpose: CLI entrypoint. Creates SmartHomeController, runs
           scenarios, outputs JSON device state to stdout.
  owns:
    - src/smart_home/main.py
    - tests/test_main.py
  inputs:
    - none (CLI)
  outputs:
    - JSON to stdout
    - exit code 0 on success
  dependencies:
    - M-CONTROLLER-SH
    - Python stdlib: json, sys
  side_effects:
    - Prints to stdout
  invariants:
    - SC-06: valid JSON, exit code 0
  failure_policy:
    - FAIL-04: ImportError → clear message, exit code 1
  non_goals:
    - CLI arguments
    - File logging
END_MODULE_CONTRACT: M-MAIN
"""
from __future__ import annotations

import json
import sys


def main() -> None:
    """Run scenarios and print JSON."""
    from src.smart_home.controller import SmartHomeController

    controller = SmartHomeController()
    controller.simulate_cold_temp()
    controller.simulate_motion()
    controller.simulate_all_clear()

    state = controller.get_state()
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    try:
        main()
    except ImportError as exc:
        print(f"Missing module: {exc}", file=sys.stderr)
        sys.exit(1)
