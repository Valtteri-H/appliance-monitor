from enum import StrEnum


class Platform(StrEnum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SELECT = "select"
    BUTTON = "button"

EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"

class UnitOfTime(StrEnum):
    MINUTES = "min"
    SECONDS = "s"

class UnitOfPower(StrEnum):
    WATT = "W"

class UnitOfEnergy(StrEnum):
    KILO_WATT_HOUR = "kWh"

__all__ = [
    "EVENT_HOMEASSISTANT_STOP",
    "Platform",
    "UnitOfEnergy",
    "UnitOfPower",
    "UnitOfTime",
]
