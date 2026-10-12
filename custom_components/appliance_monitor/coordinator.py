"""Coordinator and state machine for monitoring smart appliances."""
from __future__ import annotations

import logging
from collections.abc import Callable

from .const import (
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
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
)
from .profile_engine import CycleSnapshot, ProfileEngine

_LOGGER = logging.getLogger(__name__)


class ApplianceData:
    """Live state data container."""

    def __init__(self) -> None:
        self.state: str = STATE_IDLE
        self.phase: str = PHASE_IDLE
        self.current_power_w: float = 0.0
        self.current_energy_kwh: float = 0.0
        self.cycle_duration_seconds: float = 0.0
        self.cycle_energy_kwh: float = 0.0
        self.predicted_program: str | None = None
        self.prediction_confidence: float = 0.0
        self.estimated_remaining_seconds: float | None = None
        self.last_completed_cycle: CycleSnapshot | None = None


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
    ) -> None:
        self.profile_engine = profile_engine
        self.starting_power = starting_power
        self.finishing_power = finishing_power
        self.starting_delay = starting_delay
        self.finishing_delay = finishing_delay

        self.on_cycle_started = on_cycle_started
        self.on_cycle_finished = on_cycle_finished

        self.data = ApplianceData()

        # Internal timing and thresholds
        self._above_threshold_since: float | None = None
        self._below_threshold_since: float | None = None
        self._cycle_start_time: float | None = None
        self._cycle_start_energy: float | None = None

        # Tracking live cycle details
        self._current_snapshot: CycleSnapshot | None = None
        self._last_update_time: float | None = None
        self._consecutive_zero_updates: int = 0

    def update_power(
        self, power_w: float, current_time: float, energy_kwh: float | None = None
    ) -> None:
        """Process incoming power and energy readings."""
        power_w = max(0.0, power_w)
        self.data.current_power_w = power_w
        if energy_kwh is not None:
            self.data.current_energy_kwh = max(0.0, energy_kwh)

        dt = 0.0
        if self._last_update_time is not None:
            dt = max(0.0, current_time - self._last_update_time)
        self._last_update_time = current_time

        # Power tracking in running or paused state
        if self.data.state in (STATE_RUNNING, STATE_PAUSED) and self._current_snapshot:
            self._update_cycle_progress(power_w, dt, current_time, energy_kwh)

        # State transition logic
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

            duration_above = current_time - self._above_threshold_since
            if duration_above >= self.starting_delay:
                # Transition to RUNNING
                self._start_cycle(current_time, energy_kwh)
        else:
            self._above_threshold_since = None

    def _start_cycle(self, current_time: float, energy_kwh: float | None) -> None:
        """Begin a new tracking cycle."""
        self.data.state = STATE_RUNNING
        self.data.phase = PHASE_WEIGHING
        self._cycle_start_time = current_time
        self._cycle_start_energy = energy_kwh
        self._below_threshold_since = None
        self._above_threshold_since = None

        self._current_snapshot = CycleSnapshot(timestamp=current_time)
        self.data.cycle_duration_seconds = 0.0
        self.data.cycle_energy_kwh = 0.0
        self.data.predicted_program = None
        self.data.prediction_confidence = 0.0
        self.data.estimated_remaining_seconds = None

        if self.on_cycle_started:
            self.on_cycle_started()

    def _handle_running_state(self, power_w: float, current_time: float) -> None:
        """Evaluate running cycles, pauses and completion."""
        if power_w < self.finishing_power:
            # Power is below finishing threshold -> mark paused
            self.data.state = STATE_PAUSED
            if self._below_threshold_since is None:
                self._below_threshold_since = current_time

            duration_below = current_time - self._below_threshold_since
            if duration_below >= self.finishing_delay:
                # Cycle has legitimately finished!
                self._finish_cycle(current_time)
        else:
            # Active power restored
            self.data.state = STATE_RUNNING
            self._below_threshold_since = None

    def _update_cycle_progress(
        self, power_w: float, dt: float, current_time: float, energy_kwh: float | None
    ) -> None:
        """Update metrics, phases and predictions while cycle is active."""
        snapshot = self._current_snapshot
        assert snapshot is not None

        if self._cycle_start_time is not None:
            snapshot.duration_seconds = max(0.0, current_time - self._cycle_start_time)
            self.data.cycle_duration_seconds = snapshot.duration_seconds

        # Peak power
        snapshot.max_power_w = max(snapshot.max_power_w, power_w)

        # Energy tracking
        if energy_kwh is not None and self._cycle_start_energy is not None:
            snapshot.total_energy_kwh = max(0.0, energy_kwh - self._cycle_start_energy)
        else:
            # Approximate kWh from W and dt
            snapshot.total_energy_kwh += (power_w * dt) / 3_600_000.0

        self.data.cycle_energy_kwh = snapshot.total_energy_kwh

        # Heating phase tracking
        if power_w >= ProfileEngine.HEATING_POWER_THRESHOLD:
            snapshot.heating_duration_seconds += dt
            snapshot.heating_energy_kwh += (power_w * dt) / 3_600_000.0
            self.data.phase = PHASE_WASHING_HEATING
        elif power_w >= ProfileEngine.SPIN_POWER_THRESHOLD:
            snapshot.high_spin_detected = True
            self.data.phase = PHASE_SPINNING
        elif snapshot.duration_seconds < 240 and (
            ProfileEngine.WEIGHING_MIN_POWER <= power_w <= ProfileEngine.WEIGHING_MAX_POWER
        ):
            self.data.phase = PHASE_WEIGHING
            snapshot.weighing_pulses += 1
        elif snapshot.heating_duration_seconds > 60:
            self.data.phase = PHASE_RINSING
        else:
            self.data.phase = PHASE_UNKNOWN

        # Update real-time prediction
        prog, conf = self.profile_engine.predict_program(snapshot, partial=True)
        self.data.predicted_program = prog
        self.data.prediction_confidence = conf
        self.data.estimated_remaining_seconds = self.profile_engine.estimate_remaining_time(
            snapshot, prog
        )

    def _finish_cycle(self, current_time: float) -> None:
        """Finalize cycle and prepare snapshot for user confirmation."""
        self.data.state = STATE_FINISHED
        self.data.phase = PHASE_IDLE
        self._below_threshold_since = None

        if self._current_snapshot:
            # Deduct the finishing delay from duration
            self._current_snapshot.duration_seconds = max(
                0.0, self._current_snapshot.duration_seconds - self.finishing_delay
            )
            self.data.cycle_duration_seconds = self._current_snapshot.duration_seconds

            final_prog, final_conf = self.profile_engine.predict_program(
                self._current_snapshot, partial=False
            )
            self._current_snapshot.program_name = final_prog
            self.data.predicted_program = final_prog
            self.data.prediction_confidence = final_conf
            self.data.last_completed_cycle = self._current_snapshot

            if self.on_cycle_finished:
                self.on_cycle_finished(self._current_snapshot)

    def reset_to_idle(self) -> None:
        """Reset finished state back to idle (e.g. user unloaded appliance)."""
        self.data.state = STATE_IDLE
        self.data.phase = PHASE_IDLE
        self.data.estimated_remaining_seconds = None
        self._above_threshold_since = None
        self._below_threshold_since = None
        if self._current_snapshot:
            self._current_snapshot = None
