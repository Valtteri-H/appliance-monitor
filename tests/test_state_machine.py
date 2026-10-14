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


def test_dryer_and_dishwasher_phases():
    engine = ProfileEngine()

    # Kuivausrumpu
    dryer_sm = ApplianceStateMachine(
        profile_engine=engine,
        starting_power=10.0,
        finishing_power=3.0,
        starting_delay=5.0,
        finishing_delay=10.0,
        appliance_type="dryer",
    )
    t = 100.0
    dryer_sm.update_power(20.0, t)
    t += 6.0
    dryer_sm.update_power(20.0, t)
    assert dryer_sm.data.state == "running"
    assert dryer_sm.data.phase == "drying"

    # Lämmitys kuivausrummussa (kynnys 350W)
    t += 10.0
    dryer_sm.update_power(400.0, t)
    assert dryer_sm.data.phase == "drying"
    assert dryer_sm._current_snapshot.heating_duration_seconds > 0

    # Astianpesukone
    dw_sm = ApplianceStateMachine(
        profile_engine=engine,
        starting_power=10.0,
        finishing_power=3.0,
        starting_delay=5.0,
        finishing_delay=10.0,
        appliance_type="dishwasher",
    )
    t = 100.0
    dw_sm.update_power(20.0, t)
    t += 6.0
    dw_sm.update_power(20.0, t)
    assert dw_sm.data.state == "running"
    # Teho < 1500W -> aluksi huuhtelu (rinsing)
    assert dw_sm.data.phase == "rinsing"

    # Teho > 1500W -> lämmitys (heating)
    t += 10.0
    dw_sm.update_power(1800.0, t)
    assert dw_sm.data.phase == "heating"


def test_state_machine_export_restore_and_transitions():
    engine = ProfileEngine()
    sm = ApplianceStateMachine(
        profile_engine=engine,
        starting_power=10.0,
        finishing_power=3.0,
        starting_delay=30.0,
        finishing_delay=60.0,
    )

    t = 1000.0
    sm.update_power(50.0, t)
    # Aikaa käynnistymiseen jäljellä 30s
    rem = sm.time_until_transition(t)
    assert rem == 30.0

    # 10s myöhemmin jäljellä 20s
    t += 10.0
    sm.update_power(50.0, t)
    assert sm.time_until_transition(t) == 20.0

    # Käynnistyy
    t += 25.0
    sm.update_power(50.0, t)
    assert sm.data.state == "running"
    assert sm.time_until_transition(t) is None

    # Teho tippuu nollille -> aikaa sammumiseen 60s
    t += 10.0
    sm.update_power(0.0, t)
    assert sm.data.state == "paused"
    assert sm.time_until_transition(t) == 60.0

    # Tallennetaan tila (export)
    exported = sm.export_active_state()
    assert exported is not None
    assert exported["state"] == "paused"

    # Uusi state machine palauttaa tilan (restore)
    new_sm = ApplianceStateMachine(profile_engine=engine)
    success = new_sm.restore_active_state(exported, current_monotonic=t)
    assert success is True
    assert new_sm.data.state == "paused"
    assert new_sm._current_snapshot is not None

    # Thresholdien päivitys lennosta
    new_sm.update_thresholds(
        starting_power=15.0,
        finishing_power=5.0,
        starting_delay=20.0,
        finishing_delay=40.0,
    )
    assert new_sm.starting_power == 15.0
    assert new_sm.finishing_delay == 40.0
