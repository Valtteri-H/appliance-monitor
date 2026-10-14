"""Tests for entity platforms and config flow of Appliance Monitor."""
import pytest
from homeassistant import ConfigEntry, HomeAssistant
from homeassistant.helpers import selector

from custom_components.appliance_monitor import (
    async_setup_entry,
    async_unload_entry,
    binary_sensor,
    button,
    select,
    sensor,
    text,
)
from custom_components.appliance_monitor.binary_sensor import ApplianceRunningBinarySensor
from custom_components.appliance_monitor.button import (
    ApplianceForgetButton,
    ApplianceResetButton,
)
from custom_components.appliance_monitor.config_flow import (
    ApplianceMonitorConfigFlow,
    ApplianceMonitorOptionsFlow,
)
from custom_components.appliance_monitor.const import (
    CONF_ENERGY_SENSOR,
    CONF_FINISHING_POWER,
    CONF_POWER_SENSOR,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_STARTING_POWER,
    DOMAIN,
    PHASE_DRYING,
    PHASE_WASHING_HEATING,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RUNNING,
)
from custom_components.appliance_monitor.profile_engine import CycleSnapshot
from custom_components.appliance_monitor.select import ApplianceProgramSelect
from custom_components.appliance_monitor.sensor import (
    ApplianceDurationSensor,
    ApplianceEnergySensor,
    AppliancePhaseSensor,
    ApplianceProgramSensor,
    ApplianceRemainingSensor,
    ApplianceStatusSensor,
)
from custom_components.appliance_monitor.text import ApplianceProgramText

# Ensure selectors are callable so voluptuous schemas compile in tests
for sel_cls in (
    selector.TextSelector,
    selector.EntitySelector,
    selector.SelectSelector,
    selector.NumberSelector,
    selector.BooleanSelector,
):
    sel_cls.__call__ = lambda self, value: value


@pytest.fixture
async def coordinator_setup():
    """Fixture to set up a test coordinator and integration."""
    hass = HomeAssistant()
    entry = ConfigEntry(
        entry_id="test_entities_entry",
        title="Testipesukone",
        data={
            CONF_POWER_SENSOR: "sensor.power",
            CONF_STARTING_POWER: 10.0,
            CONF_FINISHING_POWER: 3.0,
        },
    )
    setup_success = await async_setup_entry(hass, entry)
    assert setup_success is True

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    yield hass, entry, coordinator
    await async_unload_entry(hass, entry)


@pytest.mark.asyncio
async def test_sensor_platform_and_entities(coordinator_setup):
    hass, entry, coordinator = coordinator_setup

    sensors = []
    await sensor.async_setup_entry(hass, entry, sensors.extend)
    assert len(sensors) == 6

    status_sensor = next(s for s in sensors if isinstance(s, ApplianceStatusSensor))
    phase_sensor = next(s for s in sensors if isinstance(s, AppliancePhaseSensor))
    program_sensor = next(s for s in sensors if isinstance(s, ApplianceProgramSensor))
    remaining_sensor = next(s for s in sensors if isinstance(s, ApplianceRemainingSensor))
    duration_sensor = next(s for s in sensors if isinstance(s, ApplianceDurationSensor))
    energy_sensor = next(s for s in sensors if isinstance(s, ApplianceEnergySensor))

    # 1. Status sensor
    coordinator.sm.data.state = STATE_IDLE
    assert status_sensor.native_value == "idle"
    coordinator.sm.data.state = STATE_RUNNING
    assert status_sensor.native_value == "running"
    coordinator.sm.data.state = STATE_PAUSED
    assert status_sensor.native_value == "paused"
    coordinator.sm.data.state = STATE_FINISHED
    assert status_sensor.native_value == "finished"

    # 2. Phase sensor
    coordinator.sm.data.phase = PHASE_WASHING_HEATING
    assert phase_sensor.native_value == "heating"
    coordinator.sm.data.phase = PHASE_DRYING
    assert phase_sensor.native_value == "drying"

    # 3. Program sensor + extra_state_attributes
    coordinator.sm.data.predicted_program = None
    coordinator.sm.data.prediction_confidence = 0.0
    assert program_sensor.native_value is None
    assert program_sensor.extra_state_attributes == {"confidence": 0.0}

    coordinator.sm.data.predicted_program = "Eco 40-60"
    coordinator.sm.data.prediction_confidence = 0.854
    assert program_sensor.native_value == "Eco 40-60"
    assert program_sensor.extra_state_attributes == {"confidence": 85.4}

    # 4. Remaining time sensor
    coordinator.sm.data.estimated_remaining_seconds = None
    assert remaining_sensor.native_value is None

    coordinator.sm.data.estimated_remaining_seconds = 1800.0  # 30 min
    assert remaining_sensor.native_value == 30

    # 5. Cycle duration sensor
    coordinator.sm.data.cycle_duration_seconds = 3600.0  # 60 min
    assert duration_sensor.native_value == 60

    # 6. Cycle energy sensor
    coordinator.sm.data.cycle_energy_kwh = 1.2346
    assert energy_sensor.native_value == 1.235


@pytest.mark.asyncio
async def test_binary_sensor_platform_and_entity(coordinator_setup):
    hass, entry, coordinator = coordinator_setup

    binary_sensors = []
    await binary_sensor.async_setup_entry(hass, entry, binary_sensors.extend)
    assert len(binary_sensors) == 1

    run_sensor = binary_sensors[0]
    assert isinstance(run_sensor, ApplianceRunningBinarySensor)

    # idle -> False
    coordinator.sm.data.state = STATE_IDLE
    assert run_sensor.is_on is False

    # running -> True
    coordinator.sm.data.state = STATE_RUNNING
    assert run_sensor.is_on is True

    # paused -> True
    coordinator.sm.data.state = STATE_PAUSED
    assert run_sensor.is_on is True

    # finished -> False
    coordinator.sm.data.state = STATE_FINISHED
    assert run_sensor.is_on is False


@pytest.mark.asyncio
async def test_select_platform_and_entity(coordinator_setup):
    hass, entry, coordinator = coordinator_setup

    selects = []
    await select.async_setup_entry(hass, entry, selects.extend)
    assert len(selects) == 1

    select_entity = selects[0]
    assert isinstance(select_entity, ApplianceProgramSelect)

    # options
    opts = select_entity.options
    for default_prog in ["Eco 40-60", "Kirjopesu 40°C", "Valkopyykki 60°C", "Pika 30 min"]:
        assert default_prog in opts
    assert opts == sorted(opts)

    # current_option
    coordinator.sm.data.last_completed_cycle = None
    coordinator.sm.data.predicted_program = None
    assert select_entity.current_option is None

    coordinator.sm.data.predicted_program = "Eco 40-60"
    assert select_entity.current_option == "Eco 40-60"

    snap = CycleSnapshot(
        duration_seconds=3600.0,
        total_energy_kwh=0.8,
        program_name="Kirjopesu 40°C",
    )
    coordinator.sm.data.last_completed_cycle = snap
    assert select_entity.current_option == "Kirjopesu 40°C"

    # async_select_option syklin kanssa
    await select_entity.async_select_option("Valkopyykki 60°C")
    assert "Valkopyykki 60°C" in coordinator.engine.profiles
    assert snap.confirmed_by_user is True

    # async_select_option ilman sykliä
    coordinator.sm.data.last_completed_cycle = None
    coordinator.sm.data.predicted_program = None
    await select_entity.async_select_option("UusiPreset")
    assert "UusiPreset" in coordinator.engine.profiles
    assert select_entity.current_option == "UusiPreset"


@pytest.mark.asyncio
async def test_text_platform_and_entity(coordinator_setup):
    hass, entry, coordinator = coordinator_setup

    texts = []
    await text.async_setup_entry(hass, entry, texts.extend)
    assert len(texts) == 1

    text_entity = texts[0]
    assert isinstance(text_entity, ApplianceProgramText)

    # native_value alussa tyhjä
    assert text_entity.native_value == ""

    # Tyhjä syöte ei tee mitään
    await text_entity.async_set_value("")
    assert text_entity.native_value == ""
    await text_entity.async_set_value("   ")
    assert text_entity.native_value == ""

    # Rekisteröinti ilman sykliä
    coordinator.sm.data.last_completed_cycle = None
    await text_entity.async_set_value("Oma Erikoispesu")
    assert text_entity.native_value == "Oma Erikoispesu"
    assert "Oma Erikoispesu" in coordinator.engine.profiles

    # Opetus syklin kanssa
    snap = CycleSnapshot(
        duration_seconds=4000.0,
        total_energy_kwh=1.1,
    )
    coordinator.sm.data.last_completed_cycle = snap
    await text_entity.async_set_value("Hienopesu 30°C")
    assert text_entity.native_value == "Hienopesu 30°C"
    assert "Hienopesu 30°C" in coordinator.engine.profiles
    assert snap.confirmed_by_user is True


@pytest.mark.asyncio
async def test_button_platform_and_entities(coordinator_setup):
    hass, entry, coordinator = coordinator_setup

    buttons = []
    await button.async_setup_entry(hass, entry, buttons.extend)
    assert len(buttons) == 2

    reset_btn = next(b for b in buttons if isinstance(b, ApplianceResetButton))
    forget_btn = next(b for b in buttons if isinstance(b, ApplianceForgetButton))

    # ApplianceResetButton.async_press
    coordinator.sm.data.state = STATE_FINISHED
    await reset_btn.async_press()
    assert coordinator.sm.data.state == STATE_IDLE

    # ApplianceForgetButton.async_press
    snap = CycleSnapshot(
        duration_seconds=2400.0,
        total_energy_kwh=0.5,
    )
    await coordinator.async_learn_cycle(snap, "PoistettavaSykli")
    assert "PoistettavaSykli" in coordinator.engine.profiles

    await forget_btn.async_press()
    assert "PoistettavaSykli" not in coordinator.engine.profiles


@pytest.mark.asyncio
async def test_config_flow():
    flow = ApplianceMonitorConfigFlow()

    # Näytä oletuslomake
    step_init = await flow.async_step_user()
    assert step_init["type"] == "form"
    assert step_init["step_id"] == "user"

    # Virhe: invalid_power_thresholds (starting <= finishing)
    res_thresh = await flow.async_step_user({
        "name": "Pyykkäri",
        CONF_POWER_SENSOR: "sensor.power",
        CONF_STARTING_POWER: 5.0,
        CONF_FINISHING_POWER: 10.0,
    })
    assert res_thresh["type"] == "form"
    assert res_thresh["errors"]["base"] == "invalid_power_thresholds"

    # Virhe: same_sensor (power ja energy ovat sama sensori)
    res_same = await flow.async_step_user({
        "name": "Pyykkäri",
        CONF_POWER_SENSOR: "sensor.power",
        CONF_ENERGY_SENSOR: "sensor.power",
        CONF_STARTING_POWER: 20.0,
        CONF_FINISHING_POWER: 5.0,
    })
    assert res_same["type"] == "form"
    assert res_same["errors"]["base"] == "same_sensor"

    # Virhe: invalid_quiet_hours
    res_qh = await flow.async_step_user({
        "name": "Pyykkäri",
        CONF_POWER_SENSOR: "sensor.power",
        CONF_STARTING_POWER: 20.0,
        CONF_FINISHING_POWER: 5.0,
        CONF_QUIET_HOURS_START: "virheellinen",
        CONF_QUIET_HOURS_END: "07:00",
    })
    assert res_qh["type"] == "form"
    assert res_qh["errors"]["base"] == "invalid_quiet_hours"

    # Onnistunut luonti
    res_ok = await flow.async_step_user({
        "name": "Pyykkäri",
        CONF_POWER_SENSOR: "sensor.power",
        CONF_ENERGY_SENSOR: "sensor.energy",
        CONF_STARTING_POWER: 20.0,
        CONF_FINISHING_POWER: 5.0,
        CONF_QUIET_HOURS_START: "22:00",
        CONF_QUIET_HOURS_END: "07:00",
    })
    assert res_ok["type"] == "create_entry"
    assert res_ok["title"] == "Pyykkäri"
    assert res_ok["data"][CONF_POWER_SENSOR] == "sensor.power"


@pytest.mark.asyncio
async def test_options_flow():
    entry = ConfigEntry(
        entry_id="opt_test_entry",
        title="Pyykkäri",
        data={
            CONF_POWER_SENSOR: "sensor.power",
            CONF_STARTING_POWER: 10.0,
            CONF_FINISHING_POWER: 3.0,
        },
    )
    opt_flow = ApplianceMonitorConfigFlow.async_get_options_flow(entry)
    assert isinstance(opt_flow, ApplianceMonitorOptionsFlow)

    # Näytä oletuslomake
    step_init = await opt_flow.async_step_init()
    assert step_init["type"] == "form"
    assert step_init["step_id"] == "init"

    # Virhe: invalid_power_thresholds
    res_thresh = await opt_flow.async_step_init({
        CONF_STARTING_POWER: 2.0,
        CONF_FINISHING_POWER: 8.0,
    })
    assert res_thresh["type"] == "form"
    assert res_thresh["errors"]["base"] == "invalid_power_thresholds"

    # Virhe: invalid_quiet_hours
    res_qh = await opt_flow.async_step_init({
        CONF_STARTING_POWER: 25.0,
        CONF_FINISHING_POWER: 5.0,
        CONF_QUIET_HOURS_START: "25:00",
        CONF_QUIET_HOURS_END: "07:00",
    })
    assert res_qh["type"] == "form"
    assert res_qh["errors"]["base"] == "invalid_quiet_hours"

    # Onnistunut tallennus
    res_ok = await opt_flow.async_step_init({
        CONF_STARTING_POWER: 30.0,
        CONF_FINISHING_POWER: 6.0,
        CONF_QUIET_HOURS_START: "23:00",
        CONF_QUIET_HOURS_END: "06:00",
    })
    assert res_ok["type"] == "create_entry"
    assert res_ok["data"][CONF_STARTING_POWER] == 30.0
    assert res_ok["data"][CONF_QUIET_HOURS_START] == "23:00"
