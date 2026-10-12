"""Binary sensor platform for Appliance Monitor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATE_RUNNING


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Appliance Monitor binary sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ApplianceRunningBinarySensor(coordinator, entry)])


class ApplianceRunningBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating if appliance is currently active."""

    _attr_has_entity_name = True
    _attr_translation_key = "running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_running"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )

    @property
    def is_on(self) -> bool:
        """Return true if appliance is actively running or paused mid-cycle."""
        return self.coordinator.sm.data.state in (STATE_RUNNING, "paused")
