# Verification Matrix — Smart Home

## Use Case to Module Gate Mapping

| Use Case | Description | Module Gate | Wave | Phase |
|----------|-------------|-------------|------|-------|
| UC-01 | Event publish/subscribe | M-EVENTBUS gate | WAVE-1 | PHASE-1 |
| UC-02 | Temperature monitoring + thermostat | M-SENSORS + M-ACTUATORS | WAVE-2, WAVE-3 | PHASE-2, PHASE-3 |
| UC-03 | Motion detection + light control | M-SENSORS + M-ACTUATORS | WAVE-2, WAVE-3 | PHASE-2, PHASE-3 |
| UC-04 | Smart home orchestration | M-CONTROLLER gate | WAVE-4 | PHASE-4 |
| UC-05 | CLI entrypoint with JSON output | M-MAIN gate | WAVE-4 | PHASE-4 |
| UC-06 | Deterministic verification | M-TESTS gate | WAVE-5 | PHASE-5 |

## Deterministic Checks

| ID | Check | Test File |
|----|-------|-----------|
| VM-D01 | Event is frozen dataclass | test_event_bus.py |
| VM-D02 | EventBus delivers to all subscribers | test_event_bus.py |
| VM-D03 | subscribe/unsubscribe work | test_event_bus.py |
| VM-D04 | Duplicate subscribe ignored | test_event_bus.py |
| VM-D05 | Publish to empty topic ignored | test_event_bus.py |
| VM-D06 | TemperatureSensor.read publishes | test_sensors.py |
| VM-D07 | MotionSensor.detect publishes | test_sensors.py |
| VM-D08 | Thermostat.is_on follows threshold | test_actuators.py |
| VM-D09 | LightBulb.is_on follows motion | test_actuators.py |
| VM-D10 | Controller does not modify EventBus | test_integration.py |
| VM-D11 | main.py outputs valid JSON | test_main.py |
| VM-D12 | main.py exit code 0 | test_main.py |

## Trace Assertions

| ID | Trace | Wave |
|----|-------|------|
| VM-T01 | EventBus.publish -> subscriber call | WAVE-1 |
| VM-T02 | EventBus.publish error -> log -> continue | WAVE-1 |
| VM-T03 | TemperatureSensor.read -> EventBus | WAVE-2 |
| VM-T04 | MotionSensor.detect -> EventBus | WAVE-2 |
| VM-T05 | EventBus -> Thermostat.is_on | WAVE-3 |
| VM-T06 | EventBus -> LightBulb.is_on | WAVE-3 |
| VM-T07 | Controller init -> subscribe | WAVE-4 |
| VM-T08 | simulate_cold_temp -> Thermostat ON | WAVE-4 |
| VM-T09 | simulate_motion -> LightBulb ON | WAVE-4 |
| VM-T10 | Full pipeline: sensor -> bus -> actuator -> JSON | WAVE-5 |

## Phase Gates

| Phase | Criteria |
|-------|----------|
| PHASE-1 | WAVE-1 tests green; Event frozen; EventBus delivers |
| PHASE-2 | WAVE-2 tests green; sensors publish correct topics |
| PHASE-3 | WAVE-3 tests green; threshold logic holds |
| PHASE-4 | WAVE-4 tests green; JSON output valid; integration e2e |
| PHASE-5 | All tests green; all invariants covered; no src changes |

## Invariant Coverage

| Invariant | Covered By |
|-----------|-----------|
| INV-01 | VM-D02, VM-D06, VM-D07 |
| INV-02 | VM-D08 |
| INV-03 | VM-D09 |
| INV-04 | VM-D03 |
| INV-05 | VM-D10 |
| INV-06 | VM-D01 |
