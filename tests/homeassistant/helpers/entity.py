from enum import StrEnum


class EntityCategory(StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


class DeviceInfo:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
