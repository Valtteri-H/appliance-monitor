"""Unit tests for Appliance State Machine."""
from custom_components.appliance_monitor.coordinator import ApplianceStateMachine
from custom_components.appliance_monitor.profile_engine import ProfileEngine


def test_state_machine_cycle_flow():
    engine = ProfileEngine()
    started_called = []
    finished_called = []

    sm = ApplianceStateMachine(
        profile_engine=engine,
        starting_power=10.0,
        finishing_power=3.0,
        starting_delay=30.0,
        finishing_delay=120.0,
        on_cycle_started=lambda: started_called.append(True),
        on_cycle_finished=lambda snap: finished_called.append(snap),
    )

    t = 1000.0
    # Valmiustila 1W
    sm.update_power(1.0, t)
    assert sm.data.state == "idle"

    # Kone käynnistyy 50W, mutta vasta 10s kulunut -> ei vielä running
    t += 10.0
    sm.update_power(50.0, t)
    assert sm.data.state == "idle"

    # Yli 30s teho päällä -> siirtyy RUNNING
    t += 35.0
    sm.update_power(60.0, t)
    assert sm.data.state == "running"
    assert len(started_called) == 1

    # Lämmitysvaihe 2000W
    t += 60.0
    sm.update_power(2000.0, t)
    assert sm.data.state == "running"
    assert sm.data.phase == "heating"

    # Tauko / liotus 1W (kesto 60s -> alle 120s viiveen)
    t += 60.0
    sm.update_power(1.0, t)
    assert sm.data.state == "paused"

    # Teho palaa takaisin 200W -> palaa RUNNING
    t += 30.0
    sm.update_power(200.0, t)
    assert sm.data.state == "running"

    # Ohjelma oikeasti loppuu: teho 0W yli 120s
    t += 60.0
    sm.update_power(0.5, t)
    assert sm.data.state == "paused"

    t += 125.0
    sm.update_power(0.5, t)
    assert sm.data.state == "finished"
    assert len(finished_called) == 1
    assert finished_called[0].max_power_w == 2000.0

    # Kuittaus
    sm.reset_to_idle()
    assert sm.data.state == "idle"
