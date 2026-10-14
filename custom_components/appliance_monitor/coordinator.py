"""Coordinator and state machine for monitoring smart appliances."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .const import (
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
    DRYER_HEATING_THRESHOLD,
    MAX_DT_SECONDS,
    PHASE_DRYING,
    PHASE_IDLE,
    PHASE_RINSING,
    PHASE_SPINNING,
    PHASE_UNKNOWN,
    PHASE_WASHING_HEATING,
    PHASE_WEIGHING,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_RUNNING,
    TYPE_DISHWASHER,
    TYPE_DRYER,
    TYPE_WASHING_MACHINE,
)
from .profile_engine import CycleSnapshot, ProfileEngine

_LOGGER = logging.getLogger(__name__)


@dataclass
class ApplianceData:
    """Live state data container."""

    state: str = STATE_IDLE
    phase: str = PHASE_IDLE
    cycle_duration_seconds: float = 0.0
    cycle_energy_kwh: float = 0.0
    predicted_program: str | None = None
    prediction_confidence: float = 0.0
    estimated_remaining_seconds: float | None = None
    last_completed_cycle: CycleSnapshot | None = None


class ApplianceStateMachine:
    """Core state machine logic decoupled from Home Assistant internals."""

    def __init__(
        self,
        profile_engine: ProfileEngine,
        starting_power: float = DEFAULT_STARTING_POWER,
        finishing_power: float = DEFAULT_FINISHING_POWER,
        starting_delay: float = DEFAULT_STARTING_DELAY,
        finishing_delay: float = DEFAULT_FINISHING_DELAY,
        on_cycle_started: Callable[[], None] | None = None,
        on_cycle_finished: Callable[[CycleSnapshot], None] | None = None,
        appliance_type: str = TYPE_WASHING_MACHINE,
    ) -> None:
        self.profile_engine = profile_engine
        self.starting_power = starting_power
        self.finishing_power = finishing_power
        self.starting_delay = starting_delay
        self.finishing_delay = finishing_delay
        self.appliance_type = appliance_type
        self.pause_max_duration = 0.0

        self.on_cycle_started = on_cycle_started
        self.on_cycle_finished = on_cycle_finished
        self.data = ApplianceData()

        self._above_threshold_since: float | None = None
        self._below_threshold_since: float | None = None
        self._cycle_start_time: float | None = None
        self._cycle_start_energy: float | None = None
        self._current_snapshot: CycleSnapshot | None = None
        self._last_update_time: float | None = None

    def update_thresholds(
        self,
        starting_power: float,
        finishing_power: float,
        starting_delay: float,
        finishing_delay: float,
        pause_max_duration: float = 0.0,
        appliance_type: str | None = None,
    ) -> None:
        """Update operational thresholds on the fly without resetting state."""
        self.starting_power, self.finishing_power = starting_power, finishing_power
        self.starting_delay, self.finishing_delay = starting_delay, finishing_delay
        self.pause_max_duration = pause_max_duration
        if appliance_type is not None:
            self.appliance_type = appliance_type

    def update_power(
        self, power_w: float, current_time: float, energy_kwh: float | None = None
    ) -> None:
        """Process incoming power and energy readings."""
        power_w = max(0.0, power_w)
        dt = 0.0
        if self._last_update_time is not None:
            dt = min(max(0.0, current_time - self._last_update_time), MAX_DT_SECONDS)
        self._last_update_time = current_time

        if self.data.state in (STATE_RUNNING, STATE_PAUSED) and self._current_snapshot:
            self._update_cycle_progress(power_w, dt, current_time, energy_kwh)

        if self.data.state in (STATE_IDLE, STATE_FINISHED, STATE_OFF):
            self._handle_idle_state(power_w, current_time, energy_kwh)
        elif self.data.state in (STATE_RUNNING, STATE_PAUSED):
            self._handle_running_state(power_w, current_time)

    def _handle_idle_state(
        self, power_w: float, current_time: float, energy_kwh: float | None
    ) -> None:
        """Evaluate if appliance is starting up."""
        if power_w >= self.starting_power:
            if self._above_threshold_since is None:
                self._above_threshold_since = current_time
            if (current_time - self._above_threshold_since) >= self.starting_delay:
                self._start_cycle(current_time, energy_kwh)
        else:
            self._above_threshold_since = None

    def _start_cycle(self, current_time: float, energy_kwh: float | None) -> None:
        """Begin a new tracking cycle."""
        self.data.state = STATE_RUNNING
        if self.appliance_type == TYPE_DRYER:
            self.data.phase = PHASE_DRYING
        elif self.appliance_type == TYPE_DISHWASHER:
            self.data.phase = PHASE_RINSING
        else:
            self.data.phase = PHASE_WEIGHING

        self._cycle_start_time, self._cycle_start_energy = current_time, energy_kwh
        self._below_threshold_since = self._above_threshold_since = None
        self._current_snapshot = CycleSnapshot(timestamp=time.time())
        self.data.cycle_duration_seconds = self.data.cycle_energy_kwh = 0.0
        self.data.predicted_program = self.data.estimated_remaining_seconds = None
        self.data.prediction_confidence = 0.0

        if self.on_cycle_started:
            self.on_cycle_started()

    def _handle_running_state(self, power_w: float, current_time: float) -> None:
        """Evaluate running cycles, pauses and completion."""
        if power_w < self.finishing_power:
            self.data.state = STATE_PAUSED
            if self._below_threshold_since is None:
                self._below_threshold_since = current_time
            if (current_time - self._below_threshold_since) >= self.finishing_delay:
                self._finish_cycle(current_time)
        else:
            self.data.state = STATE_RUNNING
            self._below_threshold_since = None

    def _detect_phase(self, power_w: float, snapshot: CycleSnapshot) -> str:
        """Detect current appliance phase based on appliance type and telemetry."""
        if self.appliance_type == TYPE_DRYER:
            return PHASE_DRYING if power_w > self.finishing_power * 2 else PHASE_UNKNOWN

        if self.appliance_type == TYPE_DISHWASHER:
            if power_w >= ProfileEngine.HEATING_POWER_THRESHOLD:
                return PHASE_WASHING_HEATING
            est_dur = 0.0
            if self.data.predicted_program and self.data.predicted_program in self.profile_engine.profiles:
                est_dur = self.profile_engine.profiles[self.data.predicted_program].avg_duration_seconds
            if est_dur > 0 and snapshot.duration_seconds > est_dur * 0.6 and (15.0 <= power_w <= 600.0):
                return PHASE_DRYING
            return PHASE_RINSING

        if power_w >= ProfileEngine.HEATING_POWER_THRESHOLD:
            return PHASE_WASHING_HEATING
        if power_w >= ProfileEngine.SPIN_POWER_THRESHOLD:
            snapshot.high_spin_detected = True
            return PHASE_SPINNING
        if snapshot.duration_seconds < 240 and (
            ProfileEngine.WEIGHING_MIN_POWER <= power_w <= ProfileEngine.WEIGHING_MAX_POWER
        ):
            return PHASE_WEIGHING
        return PHASE_RINSING if snapshot.heating_duration_seconds > 60 else PHASE_UNKNOWN

    def _update_cycle_progress(
        self, power_w: float, dt: float, current_time: float, energy_kwh: float | None
    ) -> None:
        """Update metrics, phases and predictions while cycle is active."""
        snap = self._current_snapshot
        assert snap is not None

        snap.duration_seconds += dt
        self.data.cycle_duration_seconds = snap.duration_seconds
        snap.max_power_w = max(snap.max_power_w, power_w)

        if energy_kwh is not None and self._cycle_start_energy is not None:
            snap.total_energy_kwh = max(0.0, energy_kwh - self._cycle_start_energy)
        else:
            snap.total_energy_kwh += (power_w * dt) / 3_600_000.0
        self.data.cycle_energy_kwh = snap.total_energy_kwh

        h_thresh = DRYER_HEATING_THRESHOLD if self.appliance_type == TYPE_DRYER else ProfileEngine.HEATING_POWER_THRESHOLD
        if power_w >= h_thresh:
            snap.heating_duration_seconds += dt
            snap.heating_energy_kwh += (power_w * dt) / 3_600_000.0

        self.data.phase = self._detect_phase(power_w, snap)
        prog, conf = self.profile_engine.predict_program(snap, partial=True)
        self.data.predicted_program, self.data.prediction_confidence = prog, conf
        self.data.estimated_remaining_seconds = self.profile_engine.estimate_remaining_time(snap, prog)

    def _finish_cycle(self, current_time: float) -> None:
        """Finalize cycle and prepare snapshot for user confirmation."""
        self.data.state, self.data.phase = STATE_FINISHED, PHASE_IDLE
        self._below_threshold_since = None

        if self._current_snapshot:
            self._current_snapshot.duration_seconds = max(
                0.0, self._current_snapshot.duration_seconds - self.finishing_delay
            )
            self.data.cycle_duration_seconds = self._current_snapshot.duration_seconds
            prog, conf = self.profile_engine.predict_program(self._current_snapshot, partial=False)
            self._current_snapshot.program_name = self.data.predicted_program = prog
            self.data.prediction_confidence = conf
            self.data.last_completed_cycle = self._current_snapshot

            if self.on_cycle_finished:
                self.on_cycle_finished(self._current_snapshot)

    def time_until_transition(self, current_time: float) -> float | None:
        """Return seconds remaining until delayed transition, or None."""
        if (
            self.data.state in (STATE_IDLE, STATE_FINISHED, STATE_OFF)
            and self._above_threshold_since is not None
        ):
            return max(0.0, self.starting_delay - (current_time - self._above_threshold_since))
        if (
            self.data.state in (STATE_RUNNING, STATE_PAUSED)
            and self._below_threshold_since is not None
        ):
            return max(0.0, self.finishing_delay - (current_time - self._below_threshold_since))
        return None

    def export_active_state(self) -> dict[str, Any] | None:
        """Export active cycle state for persistent recovery across restarts."""
        if self.data.state not in (STATE_RUNNING, STATE_PAUSED) or not self._current_snapshot:
            return None
        return {
            "state": self.data.state,
            "phase": self.data.phase,
            "snapshot": self._current_snapshot.to_dict(),
            "cycle_duration_seconds": self.data.cycle_duration_seconds,
            "cycle_start_energy": self._cycle_start_energy,
            "cycle_energy_kwh": self.data.cycle_energy_kwh,
            "predicted_program": self.data.predicted_program,
            "prediction_confidence": self.data.prediction_confidence,
            "estimated_remaining_seconds": self.data.estimated_remaining_seconds,
        }

    def restore_active_state(self, data: dict[str, Any], current_monotonic: float) -> bool:
        """Restore active cycle state after HA restart."""
        if not data or "snapshot" not in data:
            return False
        try:
            self.data.state = data.get("state", STATE_RUNNING)
            self.data.phase = data.get("phase", PHASE_UNKNOWN)
            self._current_snapshot = CycleSnapshot.from_dict(data["snapshot"])
            self.data.cycle_duration_seconds = data.get(
                "cycle_duration_seconds", self._current_snapshot.duration_seconds
            )
            self._cycle_start_energy = data.get("cycle_start_energy")
            self.data.cycle_energy_kwh = data.get(
                "cycle_energy_kwh", self._current_snapshot.total_energy_kwh
            )
            self.data.predicted_program = data.get("predicted_program")
            self.data.prediction_confidence = data.get("prediction_confidence", 0.0)
            self.data.estimated_remaining_seconds = data.get("estimated_remaining_seconds")
            self._cycle_start_time = current_monotonic - self.data.cycle_duration_seconds
            self._last_update_time = current_monotonic
            self._below_threshold_since = self._above_threshold_since = None
            return True
        except Exception:
            _LOGGER.exception("Failed to restore active cycle state")
            return False

    def get_or_finalize_cycle_for_learning(self) -> CycleSnapshot | None:
        """Return last completed cycle, or finalize an active/paused cycle if user acts early."""
        if self._current_snapshot and self._current_snapshot.duration_seconds > 0:
            if self._below_threshold_since is not None and self._last_update_time is not None:
                below_dur = max(0.0, self._last_update_time - self._below_threshold_since)
                self._current_snapshot.duration_seconds = max(
                    1.0, self._current_snapshot.duration_seconds - min(below_dur, self.finishing_delay)
                )
            self.data.cycle_duration_seconds = self._current_snapshot.duration_seconds
            self.data.last_completed_cycle = self._current_snapshot
        return self.data.last_completed_cycle

    def reset_to_idle(self) -> None:
        """Reset finished or paused state back to idle while preserving completed cycle data."""
        if self._current_snapshot and self._current_snapshot.duration_seconds > 0:
            self.get_or_finalize_cycle_for_learning()
        self.data.state, self.data.phase = STATE_IDLE, PHASE_IDLE
        self.data.estimated_remaining_seconds = None
        self._above_threshold_since = self._below_threshold_since = self._current_snapshot = None
