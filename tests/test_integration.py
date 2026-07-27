from __future__ import annotations
import pytest
from src.smart_home.controller import SmartHomeController


@pytest.fixture
def ctrl() -> SmartHomeController:
    return SmartHomeController()


class TestColdTemp:
    def test_thermostat_on(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        assert ctrl.thermostat.is_on is True

    def test_light_unaffected(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        assert ctrl.light_bulb.is_on is False


class TestMotion:
    def test_light_on(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_motion()
        assert ctrl.light_bulb.is_on is True

    def test_thermostat_unaffected(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_motion()
        assert ctrl.thermostat.is_on is False


class TestAllClear:
    def test_both_off(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        ctrl.simulate_motion()
        assert ctrl.thermostat.is_on is True
        assert ctrl.light_bulb.is_on is True
        ctrl.simulate_all_clear()
        assert ctrl.thermostat.is_on is False
        assert ctrl.light_bulb.is_on is False


class TestFullCycle:
    def test_end_to_end(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        assert ctrl.thermostat.is_on is True and ctrl.light_bulb.is_on is False
        ctrl.simulate_motion()
        assert ctrl.thermostat.is_on is True and ctrl.light_bulb.is_on is True
        ctrl.simulate_all_clear()
        assert ctrl.thermostat.is_on is False and ctrl.light_bulb.is_on is False

    def test_state_dict(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        ctrl.simulate_motion()
        s = ctrl.get_state()
        assert s["thermostat"]["is_on"] is True
        assert s["light_bulb"]["is_on"] is True
        ctrl.simulate_all_clear()
        s = ctrl.get_state()
        assert s["thermostat"]["is_on"] is False
        assert s["light_bulb"]["is_on"] is False


class TestInvariant:
    def test_controller_does_not_mutate_bus(self, ctrl: SmartHomeController) -> None:
        before = {t: len(cbs) for t, cbs in ctrl.bus._subscribers.items()}
        ctrl.simulate_cold_temp()
        ctrl.simulate_motion()
        ctrl.simulate_all_clear()
        after = {t: len(cbs) for t, cbs in ctrl.bus._subscribers.items()}
        assert before == after


class TestGetState:
    def test_initial(self, ctrl: SmartHomeController) -> None:
        assert ctrl.get_state() == {
            "thermostat": {"name": "thermostat", "is_on": False},
            "light_bulb": {"name": "light-bulb", "is_on": False},
        }

    def test_after_cold(self, ctrl: SmartHomeController) -> None:
        ctrl.simulate_cold_temp()
        assert ctrl.get_state()["thermostat"]["is_on"] is True
