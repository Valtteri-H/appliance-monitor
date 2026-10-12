"""Text entity platform for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity, TextMode
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
    """Set up Appliance Monitor text entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ApplianceProgramText(coordinator, entry)])


class ApplianceProgramText(CoordinatorEntity, TextEntity):
    """Text entity allowing user to enter and learn custom program names."""

    _attr_has_entity_name = True
    _attr_translation_key = "program_text"
    _attr_mode = TextMode.TEXT

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        """Initialize text entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_program_text"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )
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
        last_cycle = self.coordinator.sm.data.last_completed_cycle
        if last_cycle:
            await self.coordinator.async_learn_cycle(last_cycle, clean_name)
            _LOGGER.info(
                "User taught new program '%s' via text entity for %s",
                clean_name,
                self.entry.title,
            )
        else:
            # If no completed cycle yet, still register profile so it appears in select options
            if clean_name not in self.coordinator.engine.profiles:
                from .profile_engine import ProgramProfile

                self.coordinator.engine.profiles[clean_name] = ProgramProfile(name=clean_name)
                await self.coordinator.async_save_data()
                _LOGGER.info(
                    "User registered new program profile '%s' for %s",
                    clean_name,
                    self.entry.title,
                )

        self.async_write_ha_state()
