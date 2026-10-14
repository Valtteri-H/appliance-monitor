from collections.abc import Callable
from typing import Any


def async_track_state_change_event(hass: Any, entity_ids: list[str] | set[str], action: Callable) -> Callable:
    def _listener(event: Any) -> None:
        if event.data.get("entity_id") in entity_ids:
            action(event)

    return hass.bus.async_listen("state_changed", _listener)


def async_call_later(hass: Any, delay: float, action: Callable) -> Callable:
    callbacks = getattr(hass, "_scheduled_callbacks", None)
    item = (delay, action)
    if callbacks is not None:
        callbacks.append(item)

    def unsub() -> None:
        if callbacks is not None and item in callbacks:
            callbacks.remove(item)

    return unsub
