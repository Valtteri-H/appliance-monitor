"""Button platform for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ApplianceBaseEntity

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


class ApplianceResetButton(ApplianceBaseEntity, ButtonEntity):
    """Button to reset state machine from finished back to idle."""

    _attr_translation_key = "reset"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_reset"

    async def async_press(self) -> None:
        """Handle button press."""
        self.coordinator.reset_to_idle()
        _LOGGER.info("Appliance state manually reset to idle")


class ApplianceForgetButton(ApplianceBaseEntity, ButtonEntity):
    """Button to delete the latest cycle record if falsely classified."""

    _attr_translation_key = "forget_last"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_forget_last"

    async def async_press(self) -> None:
        """Handle button press."""
        removed = await self.coordinator.async_forget_last_cycle()
        if removed:
            _LOGGER.info("Successfully removed last cycle from learned profiles")
