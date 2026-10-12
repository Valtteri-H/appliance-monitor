from collections.abc import Callable
from typing import Any


def callback(func: Callable) -> Callable:
    return func

class Event:
    def __init__(self, event_type: str, data: dict[str, Any] | None = None):
        self.event_type = event_type
        self.data = data or {}

class HomeAssistant:
    def __init__(self):
        self.data = {}
        self.states = {}
        self.bus = MockBus()
        self.config_entries = MockConfigEntries()
        self.services = MockServices()

    def async_create_task(self, coro):
        import asyncio
        return asyncio.create_task(coro)

class MockBus:
    def __init__(self):
        self.fired = []

    def async_fire(self, event_type: str, event_data: dict[str, Any] | None = None):
        self.fired.append((event_type, event_data))

class MockConfigEntries:
    async def async_forward_entry_setups(self, entry, platforms):
        return True

    async def async_unload_platforms(self, entry, platforms):
        return True

    async def async_reload(self, entry_id):
        return True

class MockServices:
    def __init__(self):
        self.calls = []
        self._services = {}

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self._services

    def async_register(self, domain: str, service: str, handler: Any) -> None:
        self._services[(domain, service)] = handler

    async def async_call(self, domain: str, service: str, service_data: dict[str, Any] | None = None):
        self.calls.append((domain, service, service_data))
        handler = self._services.get((domain, service))
        if handler:
            class MockCall:
                def __init__(self, data):
                    self.data = data
            await handler(MockCall(service_data or {}))

__all__ = ["Event", "HomeAssistant", "callback"]
