"""Text entity platform for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity, TextMode
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
    """Set up Appliance Monitor text entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ApplianceProgramText(coordinator, entry)])


class ApplianceProgramText(ApplianceBaseEntity, TextEntity):
    """Text entity allowing user to enter and learn custom program names."""

    _attr_translation_key = "program_text"
    _attr_mode = TextMode.TEXT
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        """Initialize text entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_program_text"
        self._attr_native_value = ""

    @property
    def native_value(self) -> str:
        """Return current text value."""
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        """Set new program name and learn cycle."""
        clean_name = value.strip()
        if not clean_name:
            return

        self._attr_native_value = clean_name
        last_cycle = self.coordinator.sm.get_or_finalize_cycle_for_learning()
        if last_cycle:
            await self.coordinator.async_learn_cycle(last_cycle, clean_name)
            _LOGGER.info(
                "User taught new program '%s' via text entity for %s",
                clean_name,
                self.entry.title,
            )
        else:
            if self.coordinator.engine.register_program(clean_name):
                await self.coordinator.async_save_data()
                self.coordinator.async_update_listeners()
                _LOGGER.info(
                    "User registered new program profile '%s' for %s",
                    clean_name,
                    self.entry.title,
                )

        self.async_write_ha_state()
