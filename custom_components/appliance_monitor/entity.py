"""Base entity for Appliance Monitor integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


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
