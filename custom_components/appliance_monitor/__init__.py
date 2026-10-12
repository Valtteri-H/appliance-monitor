"""Appliance Monitor custom component setup."""
from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ACTION_CONFIRM_PROGRAM,
    ACTION_DISMISS,
    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
    CONF_ENERGY_SENSOR,
    CONF_FINISHING_DELAY,
    CONF_FINISHING_POWER,
    CONF_NOTIFY_SERVICE,
    CONF_POWER_SENSOR,
    CONF_STARTING_DELAY,
    CONF_STARTING_POWER,
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
    DOMAIN,
    EVENT_CYCLE_FINISHED,
    EVENT_CYCLE_STARTED,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .coordinator import ApplianceStateMachine
from .notifications import build_actionable_notification_payload
from .profile_engine import CycleSnapshot, ProfileEngine

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Appliance Monitor from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}_{entry.entry_id}")
    saved_data = await store.async_load() or {}

    engine = ProfileEngine(saved_data)

    config = {**entry.data, **entry.options}
    power_entity = config[CONF_POWER_SENSOR]
    energy_entity = config.get(CONF_ENERGY_SENSOR)
    notify_service = config.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)
    enable_notifications = config.get(CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, True)

    coordinator = ApplianceCoordinator(
        hass,
        entry=entry,
        engine=engine,
        store=store,
        power_entity=power_entity,
        energy_entity=energy_entity,
        notify_service=notify_service,
        enable_notifications=enable_notifications,
        starting_power=config.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER),
        finishing_power=config.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER),
        starting_delay=config.get(CONF_STARTING_DELAY, DEFAULT_STARTING_DELAY),
        finishing_delay=config.get(CONF_FINISHING_DELAY, DEFAULT_FINISHING_DELAY),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "engine": engine,
        "store": store,
    }

    await coordinator.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services once
    if not hass.services.has_service(DOMAIN, "delete_program"):
        async def handle_delete_program(call: Any) -> None:
            program_name = str(call.data.get("program_name", "")).strip()
            target_entry_id = call.data.get("entry_id")
            if not target_entry_id or not program_name:
                _LOGGER.warning("Missing entry_id or program_name in delete_program")
                return

            item = hass.data.get(DOMAIN, {}).get(target_entry_id)
            if not item:
                _LOGGER.warning("Entry %s not found for delete_program", target_entry_id)
                return

            coord = item.get("coordinator")
            if coord:
                coord.engine.delete_program(program_name)
                await coord.async_save_data()
                coord.async_update_listeners()
                _LOGGER.info("Deleted program %s from entry %s", program_name, target_entry_id)

        async def handle_clear_history(call: Any) -> None:
            target_entry_id = call.data.get("entry_id")
            if not target_entry_id:
                _LOGGER.warning("Missing entry_id in clear_history")
                return

            item = hass.data.get(DOMAIN, {}).get(target_entry_id)
            if not item:
                _LOGGER.warning("Entry %s not found for clear_history", target_entry_id)
                return

            coord = item.get("coordinator")
            if coord:
                coord.engine.clear_all()
                await coord.async_save_data()
                coord.async_update_listeners()
                _LOGGER.info("Cleared all history for entry %s", target_entry_id)

        hass.services.async_register(DOMAIN, "delete_program", handle_delete_program)
        hass.services.async_register(DOMAIN, "clear_history", handle_clear_history)

    # Listen to actionable notifications
    @callback
    def _async_handle_notification_action(event: Event) -> None:
        action = event.data.get("action", "")
        if action.startswith(f"{ACTION_CONFIRM_PROGRAM}_{entry.entry_id}_"):
            prog_name = action.replace(f"{ACTION_CONFIRM_PROGRAM}_{entry.entry_id}_", "")
            last_cycle = coordinator.sm.data.last_completed_cycle
            if last_cycle:
                hass.async_create_task(coordinator.async_learn_cycle(last_cycle, prog_name))
                _LOGGER.info("Confirmed program '%s' via notification for %s", prog_name, entry.title)
        elif action == f"{ACTION_DISMISS}_{entry.entry_id}":
            coordinator.sm.reset_to_idle()
            coordinator.async_update_listeners()

    entry.async_on_unload(
        hass.bus.async_listen("mobile_app_notification_action", _async_handle_notification_action)
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Appliance Monitor config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator_data and "coordinator" in coordinator_data:
            await coordinator_data["coordinator"].async_unload()

        # Remove global services when last entry is unloaded
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, "delete_program")
            hass.services.async_remove(DOMAIN, "clear_history")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class ApplianceCoordinator(DataUpdateCoordinator):
    """Coordinator handling live sensor listening and state machine synchronization."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        engine: ProfileEngine,
        store: Store,
        power_entity: str,
        energy_entity: str | None,
        notify_service: str,
        enable_notifications: bool,
        starting_power: float,
        finishing_power: float,
        starting_delay: float,
        finishing_delay: float,
    ) -> None:
        super().__init__(hass, _LOGGER, name=f"Appliance Monitor ({entry.title})")
        self.entry = entry
        self.engine = engine
        self.store = store
        self.power_entity = power_entity
        self.energy_entity = energy_entity
        self.notify_service = notify_service
        self.enable_notifications = enable_notifications
        self._save_lock = asyncio.Lock()

        self.sm = ApplianceStateMachine(
            profile_engine=engine,
            starting_power=starting_power,
            finishing_power=finishing_power,
            starting_delay=starting_delay,
            finishing_delay=finishing_delay,
            on_cycle_started=self._handle_cycle_started,
            on_cycle_finished=self._handle_cycle_finished,
        )
        self._unsub_trackers: list[Any] = []

    async def async_setup(self) -> None:
        """Subscribe to sensor state updates."""
        entities = [self.power_entity]
        if self.energy_entity:
            entities.append(self.energy_entity)

        self._unsub_trackers.append(
            async_track_state_change_event(
                self.hass, entities, self._async_handle_state_event
            )
        )

    async def async_unload(self) -> None:
        """Unsubscribe all listeners and save store."""
        for unsub in self._unsub_trackers:
            unsub()
        self._unsub_trackers.clear()
        await self.async_save_data()

    async def async_save_data(self) -> None:
        """Save engine state with concurrency protection."""
        async with self._save_lock:
            await self.store.async_save(self.engine.export_data())

    @callback
    def _async_handle_state_event(self, event: Event) -> None:
        """Handle incoming state changes from HA power and energy sensors."""
        now = time.monotonic()

        def _safe_float(val: Any) -> float | None:
            try:
                f = float(val)
                if math.isfinite(f) and f >= 0.0:
                    return f
            except (ValueError, TypeError):
                pass
            return None

        power_state = self.hass.states.get(self.power_entity)
        if not power_state or power_state.state in ("unavailable", "unknown"):
            # Do not treat transient sensor unavailability as zero power drop
            return

        power_val = _safe_float(power_state.state)
        if power_val is None:
            return

        energy_val = None
        if self.energy_entity:
            energy_state = self.hass.states.get(self.energy_entity)
            if energy_state and energy_state.state not in ("unavailable", "unknown"):
                energy_val = _safe_float(energy_state.state)

        self.sm.update_power(power_val, now, energy_kwh=energy_val)
        self.async_update_listeners()

    def _handle_cycle_started(self) -> None:
        """Fired when cycle begins."""
        self.hass.bus.async_fire(
            EVENT_CYCLE_STARTED,
            {"entry_id": self.entry.entry_id, "name": self.entry.title},
        )
        self.async_update_listeners()

    def _handle_cycle_finished(self, snapshot: CycleSnapshot) -> None:
        """Fired when cycle finishes."""
        self.hass.bus.async_fire(
            EVENT_CYCLE_FINISHED,
            {
                "entry_id": self.entry.entry_id,
                "name": self.entry.title,
                "duration_minutes": round(snapshot.duration_seconds / 60.0, 1),
                "energy_kwh": round(snapshot.total_energy_kwh, 3),
                "predicted_program": snapshot.program_name,
            },
        )

        if self.enable_notifications and self.notify_service:
            self.hass.async_create_task(self._async_send_notification(snapshot))

        self.async_update_listeners()

    async def _async_send_notification(self, snapshot: CycleSnapshot) -> None:
        """Send notification via configured notify service."""
        payload = build_actionable_notification_payload(
            appliance_name=self.entry.title,
            entry_id=self.entry.entry_id,
            snapshot=snapshot,
            known_programs=list(self.engine.profiles.keys()),
        )
        service_parts = self.notify_service.split(".", 1)
        if len(service_parts) == 2:
            domain, service = service_parts
            try:
                await self.hass.services.async_call(domain, service, payload)
            except (OSError, RuntimeError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to send notification via %s: %s", self.notify_service, err
                )

    async def async_learn_cycle(self, snapshot: CycleSnapshot, program_name: str) -> None:
        """Teach engine and persist to storage."""
        if snapshot.confirmed_by_user and snapshot.program_name == program_name:
            return  # Prevent duplicate learning of identical sample
        self.engine.learn_cycle(snapshot, program_name)
        await self.async_save_data()
        self.async_update_listeners()

    async def async_forget_last_cycle(self) -> CycleSnapshot | None:
        """Delete last learned cycle and persist."""
        removed = self.engine.forget_last_cycle()
        await self.async_save_data()
        self.async_update_listeners()
        return removed
