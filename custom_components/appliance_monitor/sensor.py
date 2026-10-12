"""Sensor platform for Appliance Monitor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    PHASE_DRYING,
    PHASE_IDLE,
    PHASE_RINSING,
    PHASE_SPINNING,
    PHASE_UNKNOWN,
    PHASE_WASHING_HEATING,
    PHASE_WEIGHING,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_RUNNING,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Appliance Monitor sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            ApplianceStatusSensor(coordinator, entry),
            AppliancePhaseSensor(coordinator, entry),
            ApplianceProgramSensor(coordinator, entry),
            ApplianceRemainingSensor(coordinator, entry),
            ApplianceDurationSensor(coordinator, entry),
            ApplianceEnergySensor(coordinator, entry),
        ]
    )


class ApplianceBaseEntity(CoordinatorEntity):
    """Base entity for Appliance Monitor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )


class ApplianceStatusSensor(ApplianceBaseEntity, SensorEntity):
    """Current cycle status (idle, running, paused, finished)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "status"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_options = [STATE_OFF, STATE_IDLE, STATE_RUNNING, STATE_PAUSED, STATE_FINISHED]

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.sm.data.state


class AppliancePhaseSensor(ApplianceBaseEntity, SensorEntity):
    """Current wash/cycle phase (weighing, heating, spinning, etc)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "phase"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_phase"
        self._attr_options = [
            PHASE_IDLE,
            PHASE_WEIGHING,
            PHASE_WASHING_HEATING,
            PHASE_RINSING,
            PHASE_SPINNING,
            PHASE_DRYING,
            PHASE_UNKNOWN,
        ]

    @property
    def native_value(self) -> str:
        """Return the current phase."""
        return self.coordinator.sm.data.phase


class ApplianceProgramSensor(ApplianceBaseEntity, SensorEntity):
    """Detected or active program."""

    _attr_translation_key = "program"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program"

    @property
    def native_value(self) -> str | None:
        """Return predicted program."""
        return self.coordinator.sm.data.predicted_program

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return confidence and details."""
        return {
            "confidence": round(self.coordinator.sm.data.prediction_confidence * 100, 1),
        }


class ApplianceRemainingSensor(ApplianceBaseEntity, SensorEntity):
    """Estimated remaining duration in minutes."""

    _attr_translation_key = "remaining_time"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_remaining_time"

    @property
    def native_value(self) -> int | None:
        """Return remaining minutes."""
        rem_sec = self.coordinator.sm.data.estimated_remaining_seconds
        if rem_sec is None:
            return None
        return round(rem_sec / 60.0)


class ApplianceDurationSensor(ApplianceBaseEntity, SensorEntity):
    """Cycle duration in minutes."""

    _attr_translation_key = "cycle_duration"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cycle_duration"

    @property
    def native_value(self) -> int:
        """Return cycle duration."""
        return round(self.coordinator.sm.data.cycle_duration_seconds / 60.0)


class ApplianceEnergySensor(ApplianceBaseEntity, SensorEntity):
    """Cycle energy consumption in kWh."""

    _attr_translation_key = "cycle_energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cycle_energy"

    @property
    def native_value(self) -> float:
        """Return energy in kWh."""
        return round(self.coordinator.sm.data.cycle_energy_kwh, 3)
