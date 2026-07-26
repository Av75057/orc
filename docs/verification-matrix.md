# Verification Matrix

## Use Case: UC-PLAN-LOAD
- **Module Gate:** M-CORE
- **Scenario Check:** SCN-BOOT
- **Phase Gate:** PHASE-1
- **Verification:** `python -m pytest tests/test_artifact_loader.py -v`
- **Expected Traces:**
  - `M-CLI, LOAD_PLAN`
  - `M-CLI, ORCHESTRATOR_RUN`

## Use Case: UC-PACKET-GEN
- **Module Gate:** M-CONTROLLER
- **Scenario Check:** SCN-BOOT
- **Phase Gate:** PHASE-1
- **Verification:** `python -m pytest tests/test_controller.py -v`
- **Expected Traces:**
  - `M-CLI, LOAD_PLAN`

## Use Case: UC-GATE-CHECK
- **Module Gate:** M-REVIEWER
- **Scenario Check:** SCN-BOOT
- **Phase Gate:** PHASE-1
- **Verification:** `python -m pytest tests/test_reviewer.py -v`
- **Expected Traces:**
  - `M-CLI, LOAD_PLAN`

## Use Case: UC-ORCHESTRATE
- **Module Gate:** M-ORCHESTRATOR
- **Scenario Check:** SCN-BOOT
- **Phase Gate:** PHASE-1
- **Verification:** `python -m pytest tests/test_orchestrator.py -v`
- **Expected Traces:**
  - `M-CLI, LOAD_PLAN`
  - `M-CLI, ORCHESTRATOR_RUN`
