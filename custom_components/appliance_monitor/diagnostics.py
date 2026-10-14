"""Diagnostics support for Appliance Monitor."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    item = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = item.get("coordinator")
    engine = item.get("engine")

    state_data: dict[str, Any] = {}
    if coordinator and hasattr(coordinator, "sm"):
        state_data = asdict(coordinator.sm.data)
        state_data["active_cycle_export"] = coordinator.sm.export_active_state()

    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "state_machine": state_data,
        "learned_data": engine.export_data() if engine else {},
    }
