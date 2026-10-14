"""Minimal mocks of Home Assistant classes for fast standalone testing."""
from collections.abc import Callable
from enum import StrEnum

from .core import (
    Event,
    HomeAssistant,
    MockBus,
    MockConfigEntries,
    MockServices,
    MockStates,
    callback,
)


class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SELECT = "select"
    BUTTON = "button"
    TEXT = "text"


EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"


class UnitOfTime(StrEnum):
    MINUTES = "min"
    SECONDS = "s"


class UnitOfPower(StrEnum):
    WATT = "W"


class UnitOfEnergy(StrEnum):
    KILO_WATT_HOUR = "kWh"


class ConfigEntry:
    def __init__(
        self,
        entry_id: str = "test_entry",
        title: str = "Test",
        data: dict | None = None,
        options: dict | None = None,
    ):
        self.entry_id = entry_id
        self.title = title
        self.data = data or {}
        self.options = options or {}
        self._update_listeners = []
        self._unload_callbacks = []

    def add_update_listener(self, listener: Callable):
        self._update_listeners.append(listener)
        return lambda: self._update_listeners.remove(listener)

    def async_on_unload(self, callback: Callable):
        self._unload_callbacks.append(callback)


__all__ = [
    "EVENT_HOMEASSISTANT_STOP",
    "ConfigEntry",
    "Event",
    "HomeAssistant",
    "MockBus",
    "MockConfigEntries",
    "MockServices",
    "MockStates",
    "Platform",
    "UnitOfEnergy",
    "UnitOfPower",
    "UnitOfTime",
    "callback",
]
