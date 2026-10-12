"""Select platform for program overrides and learning."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
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
    """Set up Appliance Monitor select entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([ApplianceProgramSelect(coordinator, entry)])


class ApplianceProgramSelect(CoordinatorEntity, SelectEntity):
    """Select entity allowing user to confirm or teach the last cycle's program."""

    _attr_has_entity_name = True
    _attr_translation_key = "program_select"

    def __init__(self, coordinator: Any, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_program_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Appliance Monitor",
            model="Smart Appliance Watcher",
        )
        self._current_selection: str | None = None

    @property
    def options(self) -> list[str]:
        """Return available learned programs plus presets."""
        known = list(self.coordinator.engine.profiles.keys())
        default_options = ["Eco 40-60", "Kirjopesu 40°C", "Valkopyykki 60°C", "Pika 30 min"]
        for d in default_options:
            if d not in known:
                known.append(d)
        return sorted(known)

    @property
    def current_option(self) -> str | None:
        """Return current selected program."""
        if self._current_selection:
            return self._current_selection
        return self.coordinator.sm.data.predicted_program

    async def async_select_option(self, option: str) -> None:
        """User selected a program for the last cycle."""
        self._current_selection = option
        last_cycle = self.coordinator.sm.data.last_completed_cycle
        if last_cycle:
            await self.coordinator.async_learn_cycle(last_cycle, option)
            _LOGGER.info("User confirmed cycle program as %s", option)
        self.async_write_ha_state()
