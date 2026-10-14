"""Full integration test for ApplianceCoordinator, sensors and learning flow."""
import pytest
from homeassistant import ConfigEntry, HomeAssistant

from custom_components.appliance_monitor import async_setup_entry, async_unload_entry
from custom_components.appliance_monitor.const import (
    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
    CONF_FINISHING_DELAY,
    CONF_FINISHING_POWER,
    CONF_NOTIFY_SERVICE,
    CONF_POWER_SENSOR,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_REMINDER_INTERVAL,
    CONF_STARTING_DELAY,
    CONF_STARTING_POWER,
    DOMAIN,
    EVENT_CYCLE_FINISHED,
    EVENT_CYCLE_STARTED,
)


class MockState:
    def __init__(self, state: str):
        self.state = state


@pytest.mark.asyncio
async def test_coordinator_full_cycle_and_learning():
    hass = HomeAssistant()
    entry = ConfigEntry(
        entry_id="test_washing_machine",
        title="Pyykinpesukone",
        data={
            CONF_POWER_SENSOR: "sensor.test_power",
            CONF_STARTING_POWER: 10.0,
            CONF_FINISHING_POWER: 3.0,
            CONF_STARTING_DELAY: 5.0,   # Nopeutettu testiajo
            CONF_FINISHING_DELAY: 10.0,
            CONF_NOTIFY_SERVICE: "notify.mobile_app_test",
            CONF_ENABLE_ACTIONABLE_NOTIFICATIONS: True,
        },
    )

    setup_success = await async_setup_entry(hass, entry)
    assert setup_success is True

    coord_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coord_data["coordinator"]
    sm = coordinator.sm

    # Simuloidaan koneen käynnistys
    sm.update_power(50.0, 100.0)
    assert sm.data.state == "idle"

    # Teho päällä 6s -> käynnistyy
    sm.update_power(50.0, 106.0)
    assert sm.data.state == "running"
    assert any(ev[0] == EVENT_CYCLE_STARTED for ev in hass.bus.fired)

    # Lämmitysvaihe
    sm.update_power(2050.0, 150.0)
    assert sm.data.phase == "heating"

    # Pesun loppuminen ja 12s teho nollassa -> finished
    sm.update_power(1.0, 200.0)
    assert sm.data.state == "paused"

    sm.update_power(1.0, 212.0)
    assert sm.data.state == "finished"
    assert any(ev[0] == EVENT_CYCLE_FINISHED for ev in hass.bus.fired)

    import asyncio
    await asyncio.sleep(0.01)

    assert len(hass.services.calls) == 1
    assert hass.services.calls[0][0] == "notify"
    assert hass.services.calls[0][1] == "mobile_app_test"

    # Käyttäjä vahvistaa ohjelman: "Kirjopesu 40°C"
    snapshot = sm.data.last_completed_cycle
    assert snapshot is not None
    await coordinator.async_learn_cycle(snapshot, "Kirjopesu 40°C")

    # Tarkistetaan että profiili tallentui
    assert "Kirjopesu 40°C" in coordinator.engine.profiles

    # Käyttäjä huomaa tehneensä virheen ja poistaa viimeisimmän syklin
    removed = await coordinator.async_forget_last_cycle()
    assert removed is not None
    assert "Kirjopesu 40°C" not in coordinator.engine.profiles

    # Opitaan profiili uudestaan ja testataan palvelukutsu delete_program
    # Nollataan confirmed_by_user jotta eri ohjelmanimi tallentuu uudeksi näytteeksi
    snapshot.confirmed_by_user = False
    await coordinator.async_learn_cycle(snapshot, "PoistettavaOhjelma")
    assert "PoistettavaOhjelma" in coordinator.engine.profiles

    await hass.services.async_call(
        DOMAIN,
        "delete_program",
        {"entry_id": entry.entry_id, "program_name": "PoistettavaOhjelma"},
    )
    assert "PoistettavaOhjelma" not in coordinator.engine.profiles

    # Testataan mobiili-ilmoituksen interaktiivinen vahvistus
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"APPLIANCE_MONITOR_CONFIRM_{entry.entry_id}_Eco 40-60"},
    )
    await asyncio.sleep(0.01)
    assert "Eco 40-60" in coordinator.engine.profiles

    # Testataan mukautetun nimen syöttö text-entiteetillä
    from custom_components.appliance_monitor.text import ApplianceProgramText

    text_entity = ApplianceProgramText(coordinator, entry)
    snapshot.confirmed_by_user = False
    await text_entity.async_set_value("Puuvilla 90°C")
    assert "Puuvilla 90°C" in coordinator.engine.profiles

    # Siivous
    unload_success = await async_unload_entry(hass, entry)
    assert unload_success is True


@pytest.mark.asyncio
async def test_live_state_events_timers_and_recovery():
    hass = HomeAssistant()
    entry = ConfigEntry(
        entry_id="test_live_coordinator",
        title="Pyykinpesukone",
        data={
            CONF_POWER_SENSOR: "sensor.test_power",
            CONF_STARTING_POWER: 10.0,
            CONF_FINISHING_POWER: 3.0,
            CONF_STARTING_DELAY: 5.0,
            CONF_FINISHING_DELAY: 10.0,
            CONF_NOTIFY_SERVICE: "notify.mobile_app_test",
            CONF_ENABLE_ACTIONABLE_NOTIFICATIONS: True,
        },
    )

    setup_success = await async_setup_entry(hass, entry)
    assert setup_success is True

    coord_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = coord_data["coordinator"]
    assert coordinator.sm.data.state == "idle"

    # Aseta unavailable ja unknown -> varmista ettei tila muutu eikä kaadu
    hass.states.set("sensor.test_power", "unavailable")
    assert coordinator.sm.data.state == "idle"

    hass.states.set("sensor.test_power", "unknown")
    assert coordinator.sm.data.state == "idle"

    # Aseta teho 120.0 -> varmista että _transition_unsub ajastetaan hass._scheduled_callbacks-listaan
    hass.states.set("sensor.test_power", "120.0")
    assert coordinator.sm.data.state == "idle"
    assert coordinator._transition_unsub is not None
    assert len(hass._scheduled_callbacks) > 0
    assert any(
        cb[1] == coordinator._async_check_delayed_transition
        for cb in hass._scheduled_callbacks
    )

    # Testaa coordinator.update_config(entry) uusilla options-arvoilla lennosta
    entry.options = {
        CONF_STARTING_POWER: 25.0,
        CONF_FINISHING_POWER: 5.0,
        CONF_STARTING_DELAY: 15.0,
        CONF_FINISHING_DELAY: 20.0,
        CONF_NOTIFY_SERVICE: "notify.mobile_app_custom",
        CONF_ENABLE_ACTIONABLE_NOTIFICATIONS: False,
        CONF_QUIET_HOURS_START: "22:00",
        CONF_QUIET_HOURS_END: "07:00",
        CONF_REMINDER_INTERVAL: 30,
    }
    coordinator.update_config(entry)
    assert coordinator.notify_service == "notify.mobile_app_custom"
    assert coordinator.enable_notifications is False
    assert coordinator.quiet_hours_start == "22:00"
    assert coordinator.quiet_hours_end == "07:00"
    assert coordinator.reminder_interval == 30.0
    assert coordinator.sm.starting_power == 25.0
    assert coordinator.sm.finishing_power == 5.0
    assert coordinator.sm.starting_delay == 15.0
    assert coordinator.sm.finishing_delay == 20.0

    # Testaa palvelu clear_history
    coordinator.engine.register_program("TestiOhjelma")
    assert "TestiOhjelma" in coordinator.engine.profiles

    await hass.services.async_call(
        DOMAIN,
        "clear_history",
        {"entry_id": entry.entry_id},
    )
    assert len(coordinator.engine.profiles) == 0
    assert len(coordinator.engine.history) == 0

    unload_success = await async_unload_entry(hass, entry)
    assert unload_success is True
