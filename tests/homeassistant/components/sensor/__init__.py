from enum import StrEnum


class SensorDeviceClass(StrEnum):
    DURATION = "duration"
    ENERGY = "energy"
    POWER = "power"
    ENUM = "enum"

class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"

class SensorEntity:
    pass
