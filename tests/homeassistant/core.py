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
        self.states = MockStates()
        self.bus = MockBus()
        self.config_entries = MockConfigEntries()
        self.services = MockServices()

    def async_create_task(self, coro):
        import asyncio
        return asyncio.create_task(coro)

class MockStates:
    def __init__(self):
        self._states = {}

    def get(self, entity_id: str):
        return self._states.get(entity_id)

    def set(self, entity_id: str, state: str):
        class MockState:
            def __init__(self, s):
                self.state = s
        self._states[entity_id] = MockState(state)

class MockBus:
    def __init__(self):
        self.fired = []
        self._listeners = {}

    def async_listen(self, event_type: str, listener: Callable):
        self._listeners.setdefault(event_type, []).append(listener)
        return lambda: self._listeners[event_type].remove(listener)

    def async_fire(self, event_type: str, event_data: dict[str, Any] | None = None):
        self.fired.append((event_type, event_data))
        for listener in self._listeners.get(event_type, []):
            listener(Event(event_type, event_data or {}))

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

    def async_remove(self, domain: str, service: str) -> None:
        self._services.pop((domain, service), None)

    async def async_call(self, domain: str, service: str, service_data: dict[str, Any] | None = None):
        self.calls.append((domain, service, service_data))
        handler = self._services.get((domain, service))
        if handler:
            class MockCall:
                def __init__(self, data):
                    self.data = data
            await handler(MockCall(service_data or {}))

__all__ = ["Event", "HomeAssistant", "callback"]
