"""Button platform for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Appliance Monitor buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            ApplianceResetButton(coordinator, entry),
            ApplianceForgetButton(coordinator, entry),
        ]
    )


class ApplianceResetButton(CoordinatorEntity, ButtonEntity):
    """Button to reset state machine from finished back to idle."""

    _attr_has_entity_name = True
    _attr_translation_key = "reset"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )

    async def async_press(self) -> None:
        """Handle button press."""
        self.coordinator.sm.reset_to_idle()
        self.coordinator.async_update_listeners()
        _LOGGER.info("Appliance state manually reset to idle")


class ApplianceForgetButton(CoordinatorEntity, ButtonEntity):
    """Button to delete the latest cycle record if falsely classified."""

    _attr_has_entity_name = True
    _attr_translation_key = "forget_last"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_forget_last"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )

    async def async_press(self) -> None:
        """Handle button press."""
        removed = await self.coordinator.async_forget_last_cycle()
        if removed:
            _LOGGER.info("Successfully removed last cycle from learned profiles")
        self.coordinator.async_update_listeners()
