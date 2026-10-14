"""Binary sensor platform for Appliance Monitor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_PAUSED, STATE_RUNNING
from .entity import ApplianceBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Appliance Monitor binary sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ApplianceRunningBinarySensor(coordinator, entry)])


class ApplianceRunningBinarySensor(ApplianceBaseEntity, BinarySensorEntity):
    """Binary sensor indicating if appliance is currently active."""

    _attr_translation_key = "running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_running"

    @property
    def is_on(self) -> bool:
        """Return true if appliance is actively running or paused mid-cycle."""
        return self.coordinator.sm.data.state in (STATE_RUNNING, STATE_PAUSED)
