# Verification Matrix — Smart Home Automation System

## Wave Gates

| Wave | Gate Command | Pass Criteria |
|------|-------------|---------------|
| WAVE-CORE-1 | `python -m pytest tests/test_event_bus.py -v` | DC-01..DC-04 pass |
| WAVE-SENSORS-2 | `python -m pytest tests/test_sensors.py -v` | Sensor publishes events |
| WAVE-ACTUATORS-3 | `python -m pytest tests/test_actuators.py -v` | DC-05..DC-08 pass |
| WAVE-INTEGRATION-4 | `python -m pytest tests/test_integration.py -v` | DC-09..DC-11 pass |
| WAVE-TESTS-5 | `python -m pytest tests/ -v` | All tests pass, exit code 0 |

## Deterministic Checks

| ID | Check | Assert | Module |
|----|-------|--------|--------|
| DC-01 | EventBus delivery | received == num_subscribers | M-EVENTBUS |
| DC-02 | Unsubscribe removes callback | received_after == 0 | M-EVENTBUS |
| DC-03 | Subscriber error isolation | delivery continues after error | M-EVENTBUS |
| DC-04 | Duplicate subscribe ignored | delivered once | M-EVENTBUS |
| DC-05 | Thermostat ON on cold | thermostat.is_on is True | M-THERMOSTAT |
| DC-06 | Thermostat OFF on warm | thermostat.is_on is False | M-THERMOSTAT |
| DC-07 | Light ON on motion | light.is_on is True | M-LIGHTBULB |
| DC-08 | Light OFF on clear | light.is_on is False | M-LIGHTBULB |
| DC-09 | Integration cold | thermostat.on after simulate_cold_temp | M-CONTROLLER-SH |
| DC-10 | Integration motion | light.on after simulate_motion | M-CONTROLLER-SH |
| DC-11 | Integration clear | both off after simulate_all_clear | M-CONTROLLER-SH |

