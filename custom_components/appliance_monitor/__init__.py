"""Appliance Monitor custom component setup."""
from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ACTION_CONFIRM_PROGRAM,
    ACTION_DISMISS,
    CONF_APPLIANCE_TYPE,
    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
    CONF_ENERGY_SENSOR,
    CONF_FINISHING_DELAY,
    CONF_FINISHING_POWER,
    CONF_NOTIFY_SERVICE,
    CONF_POWER_SENSOR,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_REMINDER_INTERVAL,
    CONF_STARTING_DELAY,
    CONF_STARTING_POWER,
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_REMINDER_INTERVAL,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
    DOMAIN,
    EVENT_CYCLE_FINISHED,
    EVENT_CYCLE_STARTED,
    STATE_FINISHED,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
    TYPE_WASHING_MACHINE,
)
from .coordinator import ApplianceStateMachine
from .notifications import (
    build_actionable_notification_payload,
    is_within_quiet_hours,
    seconds_until_quiet_hours_end,
)
from .profile_engine import CycleSnapshot, ProfileEngine

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.TEXT,
]


def _safe_float(val: Any) -> float | None:
    try:
        f = float(val)
        return f if math.isfinite(f) and f >= 0.0 else None
    except (ValueError, TypeError):
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Appliance Monitor from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}_{entry.entry_id}")
    saved_data = await store.async_load() or {}
    engine = ProfileEngine(saved_data)
    cfg = {**entry.data, **entry.options}

    coordinator = ApplianceCoordinator(
        hass,
        entry=entry,
        engine=engine,
        store=store,
        power_entity=cfg[CONF_POWER_SENSOR],
        energy_entity=cfg.get(CONF_ENERGY_SENSOR),
        notify_service=cfg.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
        enable_notifications=cfg.get(CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, True),
        starting_power=cfg.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER),
        finishing_power=cfg.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER),
        starting_delay=cfg.get(CONF_STARTING_DELAY, DEFAULT_STARTING_DELAY),
        finishing_delay=cfg.get(CONF_FINISHING_DELAY, DEFAULT_FINISHING_DELAY),
        appliance_type=cfg.get(CONF_APPLIANCE_TYPE, TYPE_WASHING_MACHINE),
        quiet_hours_start=cfg.get(CONF_QUIET_HOURS_START),
        quiet_hours_end=cfg.get(CONF_QUIET_HOURS_END),
        reminder_interval=cfg.get(CONF_REMINDER_INTERVAL, DEFAULT_REMINDER_INTERVAL),
    )
    if saved_data.get("active_cycle"):
        coordinator.sm.restore_active_state(saved_data["active_cycle"], time.monotonic())

    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, "engine": engine, "store": store}
    await coordinator.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "delete_program"):
        async def handle_delete_program(call: Any) -> None:
            prog = str(call.data.get("program_name", "")).strip()
            item = hass.data.get(DOMAIN, {}).get(call.data.get("entry_id"))
            if item and item.get("coordinator") and prog:
                item["coordinator"].engine.delete_program(prog)
                await item["coordinator"].async_save_data()
                item["coordinator"].async_update_listeners()

        async def handle_clear_history(call: Any) -> None:
            item = hass.data.get(DOMAIN, {}).get(call.data.get("entry_id"))
            if item and item.get("coordinator"):
                item["coordinator"].engine.clear_all()
                await item["coordinator"].async_save_data()
                item["coordinator"].async_update_listeners()

        hass.services.async_register(DOMAIN, "delete_program", handle_delete_program)
        hass.services.async_register(DOMAIN, "clear_history", handle_clear_history)

    @callback
    def _async_handle_notification_action(event: Event) -> None:
        action = event.data.get("action", "")
        prefix = f"{ACTION_CONFIRM_PROGRAM}_{entry.entry_id}_"
        if action.startswith(prefix):
            coordinator._cancel_reminder()
            last_cycle = coordinator.sm.data.last_completed_cycle
            if last_cycle:
                hass.async_create_task(coordinator.async_learn_cycle(last_cycle, action[len(prefix):]))
        elif action == f"{ACTION_DISMISS}_{entry.entry_id}":
            coordinator.reset_to_idle()

    entry.async_on_unload(
        hass.bus.async_listen("mobile_app_notification_action", _async_handle_notification_action)
    )
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Appliance Monitor config entry."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if data and "coordinator" in data:
            await data["coordinator"].async_unload()
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, "delete_program")
            hass.services.async_remove(DOMAIN, "clear_history")
        return True
    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options on the fly without reloading."""
    item = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if item and "coordinator" in item:
        item["coordinator"].update_config(entry)


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
        appliance_type: str = TYPE_WASHING_MACHINE,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
        reminder_interval: float = 0,
    ) -> None:
        super().__init__(hass, _LOGGER, name=f"Appliance Monitor ({entry.title})")
        self.entry, self.engine, self.store = entry, engine, store
        self.power_entity, self.energy_entity = power_entity, energy_entity
        self.notify_service, self.enable_notifications = notify_service, enable_notifications
        self.quiet_hours_start, self.quiet_hours_end = quiet_hours_start, quiet_hours_end
        self.reminder_interval = float(reminder_interval or 0)
        self._save_lock = asyncio.Lock()
        self._transition_unsub: Callable[[], None] | None = None
        self._reminder_unsub: Callable[[], None] | None = None
        self._quiet_unsub: Callable[[], None] | None = None
        self._unsub_trackers: list[Any] = []
        self.sm = ApplianceStateMachine(
            profile_engine=engine,
            starting_power=starting_power,
            finishing_power=finishing_power,
            starting_delay=starting_delay,
            finishing_delay=finishing_delay,
            on_cycle_started=self._handle_cycle_started,
            on_cycle_finished=self._handle_cycle_finished,
            appliance_type=appliance_type,
        )

    def update_config(self, entry: ConfigEntry) -> None:
        """Update options dynamically without resetting cycle."""
        self.entry = entry
        cfg = {**entry.data, **entry.options}
        self.notify_service = cfg.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)
        self.enable_notifications = cfg.get(CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, True)
        self.quiet_hours_start = cfg.get(CONF_QUIET_HOURS_START)
        self.quiet_hours_end = cfg.get(CONF_QUIET_HOURS_END)
        self.reminder_interval = float(cfg.get(CONF_REMINDER_INTERVAL, DEFAULT_REMINDER_INTERVAL) or 0)
        self.sm.update_thresholds(
            starting_power=cfg.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER),
            finishing_power=cfg.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER),
            starting_delay=cfg.get(CONF_STARTING_DELAY, DEFAULT_STARTING_DELAY),
            finishing_delay=cfg.get(CONF_FINISHING_DELAY, DEFAULT_FINISHING_DELAY),
            appliance_type=cfg.get(CONF_APPLIANCE_TYPE, TYPE_WASHING_MACHINE),
        )
        self.async_update_listeners()

    async def async_setup(self) -> None:
        """Subscribe to sensor state updates."""
        entities = [self.power_entity] + ([self.energy_entity] if self.energy_entity else [])
        self._unsub_trackers.append(
            async_track_state_change_event(self.hass, entities, self._async_handle_state_event)
        )

    async def async_unload(self) -> None:
        """Unsubscribe all listeners and save store."""
        self._cancel_transition_timer()
        self._cancel_reminder()
        self._cancel_quiet_unsub()
        for unsub in self._unsub_trackers:
            unsub()
        self._unsub_trackers.clear()
        await self.async_save_data()

    async def async_save_data(self) -> None:
        """Save engine state with concurrency protection."""
        async with self._save_lock:
            data = self.engine.export_data()
            data["active_cycle"] = self.sm.export_active_state()
            await self.store.async_save(data)

    def _cancel_transition_timer(self) -> None:
        if self._transition_unsub:
            self._transition_unsub()
            self._transition_unsub = None

    def _cancel_reminder(self) -> None:
        if self._reminder_unsub:
            self._reminder_unsub()
            self._reminder_unsub = None

    def _cancel_quiet_unsub(self) -> None:
        if self._quiet_unsub:
            self._quiet_unsub()
            self._quiet_unsub = None

    def reset_to_idle(self) -> None:
        """Reset to idle and cancel reminders."""
        self._cancel_reminder()
        self._cancel_quiet_unsub()
        self.sm.reset_to_idle()
        self.async_update_listeners()

    def _get_sensor_values(self) -> tuple[float | None, float | None]:
        pst = self.hass.states.get(self.power_entity)
        if not pst or pst.state in ("unavailable", "unknown"):
            return None, None
        pval = _safe_float(pst.state)
        if pval is None:
            return None, None
        eval_ = None
        if self.energy_entity:
            est = self.hass.states.get(self.energy_entity)
            if est and est.state not in ("unavailable", "unknown"):
                eval_ = _safe_float(est.state)
        return pval, eval_

    @callback
    def _async_handle_state_event(self, event: Event) -> None:
        """Handle incoming state changes from HA power and energy sensors."""
        self._process_power_reading()

    @callback
    def _async_check_delayed_transition(self, _now: Any = None) -> None:
        """Check transition when timer expires."""
        self._transition_unsub = None
        self._process_power_reading()

    def _process_power_reading(self) -> None:
        power_val, energy_val = self._get_sensor_values()
        if power_val is None:
            return
        now = time.monotonic()
        self.sm.update_power(power_val, now, energy_kwh=energy_val)
        self.async_update_listeners()
        self._cancel_transition_timer()
        wait_sec = self.sm.time_until_transition(now)
        if wait_sec is not None:
            self._transition_unsub = async_call_later(
                self.hass, wait_sec + 0.05, self._async_check_delayed_transition
            )

    def _handle_cycle_started(self) -> None:
        self._cancel_reminder()
        self._cancel_quiet_unsub()
        self.hass.bus.async_fire(
            EVENT_CYCLE_STARTED, {"entry_id": self.entry.entry_id, "name": self.entry.title}
        )
        self.async_update_listeners()

    def _handle_cycle_finished(self, snapshot: CycleSnapshot) -> None:
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
        self.hass.async_create_task(self.async_save_data())
        self._cancel_reminder()
        self._cancel_quiet_unsub()
        if self.enable_notifications and self.notify_service:
            lt = time.localtime()
            now_hm = (lt.tm_hour, lt.tm_min)
            if is_within_quiet_hours(now_hm, self.quiet_hours_start, self.quiet_hours_end):
                delay = seconds_until_quiet_hours_end(now_hm, self.quiet_hours_end)
                self._quiet_unsub = async_call_later(
                    self.hass,
                    delay,
                    lambda _now: self.hass.async_create_task(self._async_send_notification(snapshot)),
                )
            else:
                self.hass.async_create_task(self._async_send_notification(snapshot))
            if self.reminder_interval > 0:
                self._reminder_unsub = async_call_later(
                    self.hass, self.reminder_interval * 60.0, self._async_send_reminder
                )
        self.async_update_listeners()

    @callback
    def _async_send_reminder(self, _now: Any = None) -> None:
        self._reminder_unsub = None
        last_cycle = self.sm.data.last_completed_cycle
        if self.sm.data.state != STATE_FINISHED or not last_cycle or last_cycle.confirmed_by_user:
            return
        if self.enable_notifications and self.notify_service:
            lt = time.localtime()
            if not is_within_quiet_hours((lt.tm_hour, lt.tm_min), self.quiet_hours_start, self.quiet_hours_end):
                self.hass.async_create_task(self._async_send_notification(last_cycle, is_reminder=True))
        if self.reminder_interval > 0:
            self._reminder_unsub = async_call_later(
                self.hass, self.reminder_interval * 60.0, self._async_send_reminder
            )

    async def _async_send_notification(self, snapshot: CycleSnapshot, is_reminder: bool = False) -> None:
        lang = "fi" if str(getattr(self.hass.config, "language", "fi")).lower().startswith("fi") else "en"
        payload = build_actionable_notification_payload(
            appliance_name=self.entry.title,
            entry_id=self.entry.entry_id,
            snapshot=snapshot,
            known_programs=list(self.engine.profiles.keys()),
            lang=lang,
            is_reminder=is_reminder,
        )
        parts = self.notify_service.split(".", 1)
        if len(parts) == 2:
            try:
                await self.hass.services.async_call(parts[0], parts[1], payload)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Failed to send notification via %s: %s", self.notify_service, err)

    async def async_learn_cycle(self, snapshot: CycleSnapshot, program_name: str) -> None:
        self._cancel_reminder()
        self._cancel_quiet_unsub()
        self.sm.data.last_completed_cycle = snapshot
        if snapshot.confirmed_by_user and snapshot.program_name == program_name:
            return
        self.engine.learn_cycle(snapshot, program_name)
        await self.async_save_data()
        self.async_update_listeners()

    async def async_forget_last_cycle(self) -> CycleSnapshot | None:
        self.sm.data.last_completed_cycle = None
        removed = self.engine.forget_last_cycle()
        await self.async_save_data()
        self.async_update_listeners()
        return removed
