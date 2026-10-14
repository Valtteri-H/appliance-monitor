"""Power signature analysis and adaptive program learning engine."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .const import EMA_ALPHA


def _diff_score(val1: float, val2: float, tolerance: float) -> float:
    return max(0.0, 1.0 - (abs(val1 - val2) / tolerance))


@dataclass
class CycleSnapshot:
    """Snapshot of a single cycle execution."""

    duration_seconds: float = 0.0
    total_energy_kwh: float = 0.0
    max_power_w: float = 0.0
    heating_duration_seconds: float = 0.0
    heating_energy_kwh: float = 0.0
    high_spin_detected: bool = False
    timestamp: float = field(default_factory=time.time)
    program_name: str | None = None
    confirmed_by_user: bool = False
    cycle_id: str = ""

    def __post_init__(self) -> None:
        """Ensure cycle_id is populated."""
        if not self.cycle_id:
            self.cycle_id = f"cycle_{time.time_ns()}_{id(self)}"

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CycleSnapshot:
        """Create snapshot from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProgramProfile:
    """Aggregated learned profile for a specific program."""

    name: str
    sample_count: int = 0
    avg_duration_seconds: float = 0.0
    avg_total_energy_kwh: float = 0.0
    avg_heating_energy_kwh: float = 0.0
    avg_heating_duration_seconds: float = 0.0
    max_power_w: float = 0.0
    high_spin_frequency: float = 0.0  # 0.0 - 1.0

    def update_with_sample(self, sample: CycleSnapshot) -> None:
        """Incrementally update profile statistics with a new sample using EMA."""
        spin_val = 1.0 if sample.high_spin_detected else 0.0
        n, alpha = self.sample_count, EMA_ALPHA
        self.sample_count += 1
        if n == 0:
            self.avg_duration_seconds = sample.duration_seconds
            self.avg_total_energy_kwh = sample.total_energy_kwh
            self.avg_heating_energy_kwh = sample.heating_energy_kwh
            self.avg_heating_duration_seconds = sample.heating_duration_seconds
            self.max_power_w = sample.max_power_w
            self.high_spin_frequency = spin_val
            return

        def _ema(avg: float, val: float) -> float:
            return (1.0 - alpha) * avg + alpha * val

        self.avg_duration_seconds = _ema(self.avg_duration_seconds, sample.duration_seconds)
        self.avg_total_energy_kwh = _ema(self.avg_total_energy_kwh, sample.total_energy_kwh)
        self.avg_heating_energy_kwh = _ema(self.avg_heating_energy_kwh, sample.heating_energy_kwh)
        self.avg_heating_duration_seconds = _ema(
            self.avg_heating_duration_seconds, sample.heating_duration_seconds
        )
        self.max_power_w = max(self.max_power_w, sample.max_power_w)
        self.high_spin_frequency = _ema(self.high_spin_frequency, spin_val)

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgramProfile:
        """Create profile from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


MAX_HISTORY_CYCLES = 100


class ProfileEngine:
    """Engine for tracking live signatures, matching against learned profiles and learning."""

    HEATING_POWER_THRESHOLD = 1500.0  # W (heating element active)
    SPIN_POWER_THRESHOLD = 350.0  # W (high speed motor spin)
    WEIGHING_MIN_POWER = 30.0  # W
    WEIGHING_MAX_POWER = 250.0  # W

    def __init__(self, saved_profiles: dict[str, Any] | None = None) -> None:
        """Initialize the profile engine."""
        self.profiles: dict[str, ProgramProfile] = {}
        self.history: list[CycleSnapshot] = []

        if saved_profiles:
            for name, p_data in saved_profiles.get("profiles", {}).items():
                self.profiles[name] = ProgramProfile.from_dict(p_data)
            for h_data in saved_profiles.get("history", []):
                self.history.append(CycleSnapshot.from_dict(h_data))

    def calculate_similarity(
        self, current: CycleSnapshot, profile: ProgramProfile, partial: bool = False
    ) -> float:
        """Calculate match score between current cycle and learned profile (0.0 to 1.0)."""
        score, weights_sum = 0.0, 0.0
        cur_spin = 1.0 if current.high_spin_detected else 0.0

        if partial:
            if profile.avg_heating_energy_kwh > 0.05 or current.heating_energy_kwh > 0.05:
                score += _diff_score(
                    current.heating_energy_kwh, profile.avg_heating_energy_kwh,
                    profile.avg_heating_energy_kwh * 0.4 + 0.1
                ) * 0.45
                score += _diff_score(
                    current.heating_duration_seconds, profile.avg_heating_duration_seconds,
                    profile.avg_heating_duration_seconds * 0.4 + 60.0
                ) * 0.25
                weights_sum += 0.70
                if profile.max_power_w > 10.0:
                    score += _diff_score(
                        current.max_power_w, profile.max_power_w, profile.max_power_w * 0.35 + 50.0
                    ) * 0.20
                    weights_sum += 0.20
                within_dur = profile.avg_duration_seconds <= 0 or current.duration_seconds <= profile.avg_duration_seconds * 1.3
                if within_dur and (profile.high_spin_frequency > 0 or current.high_spin_detected):
                    score += max(0.0, 1.0 - abs(cur_spin - profile.high_spin_frequency)) * 0.10
                    weights_sum += 0.10
            else:
                if profile.max_power_w > 10.0:
                    score += _diff_score(
                        current.max_power_w, profile.max_power_w, profile.max_power_w * 0.35 + 50.0
                    ) * 0.50
                    weights_sum += 0.50
                if profile.avg_duration_seconds > 0 and profile.avg_total_energy_kwh > 0:
                    ratio = min(1.0, current.duration_seconds / profile.avg_duration_seconds)
                    expected_energy = profile.avg_total_energy_kwh * ratio
                    score += _diff_score(
                        current.total_energy_kwh, expected_energy, expected_energy * 0.4 + 0.05
                    ) * 0.30
                    weights_sum += 0.30
                elif profile.avg_total_energy_kwh > 0:
                    score += _diff_score(
                        current.total_energy_kwh, profile.avg_total_energy_kwh,
                        profile.avg_total_energy_kwh * 0.4 + 0.05
                    ) * 0.30
                    weights_sum += 0.30
                score += max(0.0, 1.0 - abs(cur_spin - profile.high_spin_frequency)) * 0.20
                weights_sum += 0.20

            if profile.avg_duration_seconds > 0 and current.duration_seconds > profile.avg_duration_seconds * 1.3:
                score *= 0.5
        else:
            if profile.avg_heating_energy_kwh > 0.05:
                score += _diff_score(
                    current.heating_energy_kwh, profile.avg_heating_energy_kwh,
                    profile.avg_heating_energy_kwh * 0.4 + 0.1
                ) * 0.30
                weights_sum += 0.30
            if profile.avg_heating_duration_seconds > 60:
                score += _diff_score(
                    current.heating_duration_seconds, profile.avg_heating_duration_seconds,
                    profile.avg_heating_duration_seconds * 0.4 + 60.0
                ) * 0.15
                weights_sum += 0.15
            if profile.avg_duration_seconds > 0:
                score += _diff_score(
                    current.duration_seconds, profile.avg_duration_seconds,
                    profile.avg_duration_seconds * 0.35 + 180.0
                ) * 0.20
                weights_sum += 0.20
            if profile.avg_total_energy_kwh > 0:
                score += _diff_score(
                    current.total_energy_kwh, profile.avg_total_energy_kwh,
                    profile.avg_total_energy_kwh * 0.35 + 0.1
                ) * 0.10
                weights_sum += 0.10
            if profile.max_power_w > 10.0:
                score += _diff_score(
                    current.max_power_w, profile.max_power_w, profile.max_power_w * 0.35 + 50.0
                ) * 0.15
                weights_sum += 0.15
            score += max(0.0, 1.0 - abs(cur_spin - profile.high_spin_frequency)) * 0.10
            weights_sum += 0.10

        return 0.0 if weights_sum == 0.0 else min(1.0, max(0.0, score / weights_sum))

    def predict_program(
        self, current: CycleSnapshot, partial: bool = False
    ) -> tuple[str | None, float]:
        """Predict the program name and confidence score (0.0 - 1.0)."""
        if not self.profiles:
            return None, 0.0
        best_prog, best_score = None, 0.0
        for name, profile in self.profiles.items():
            sim = self.calculate_similarity(current, profile, partial=partial)
            if sim > best_score:
                best_score, best_prog = sim, name
        return (best_prog, best_score) if best_score >= 0.45 else (None, best_score)

    def estimate_remaining_time(
        self, current: CycleSnapshot, predicted_program: str | None
    ) -> float | None:
        """Estimate remaining seconds in cycle based on predicted profile."""
        if not predicted_program or predicted_program not in self.profiles:
            return None
        profile = self.profiles[predicted_program]
        if profile.avg_duration_seconds <= 0:
            return None
        return max(0.0, profile.avg_duration_seconds - current.duration_seconds)

    def register_program(self, name: str) -> bool:
        """Register an empty program profile if not existing."""
        clean_name = name.strip()
        if not clean_name or clean_name in self.profiles:
            return False
        self.profiles[clean_name] = ProgramProfile(name=clean_name)
        return True

    def record_completed_cycle(self, snapshot: CycleSnapshot, confirmed_program: str) -> None:
        """Record or update a completed cycle and rebuild profiles."""
        snapshot.program_name = confirmed_program
        snapshot.confirmed_by_user = True

        existing_index = None
        for i, h in enumerate(self.history):
            if (snapshot.cycle_id and h.cycle_id and h.cycle_id == snapshot.cycle_id) or (h is snapshot):
                existing_index = i
                break

        if existing_index is None and self.history:
            last = self.history[-1]
            if (
                snapshot.timestamp and last.timestamp == snapshot.timestamp
                and abs(snapshot.duration_seconds - last.duration_seconds) < 1.0
            ):
                existing_index = len(self.history) - 1

        if existing_index is not None:
            self.history[existing_index] = snapshot
        else:
            self.history.append(snapshot)
            self._prune_history()

        self._rebuild_profiles_from_history()

    def learn_cycle(self, snapshot: CycleSnapshot, program_name: str) -> None:
        """Learn and store a completed cycle with user confirmed program name."""
        self.record_completed_cycle(snapshot, program_name)

    def _prune_history(self) -> None:
        """Prune history while keeping at least 5 latest samples per program."""
        while len(self.history) > MAX_HISTORY_CYCLES:
            counts: dict[str, int] = {}
            for h in self.history:
                counts[h.program_name or ""] = counts.get(h.program_name or "", 0) + 1
            candidates = {p: c for p, c in counts.items() if c > 5} or counts
            target_prog = max(candidates.keys(), key=lambda p: candidates[p])
            for i, h in enumerate(self.history):
                if (h.program_name or "") == target_prog:
                    self.history.pop(i)
                    break

    def forget_last_cycle(self) -> CycleSnapshot | None:
        """Remove the latest cycle from history and rebuild profiles."""
        if not self.history:
            return None
        removed = self.history.pop()
        self._rebuild_profiles_from_history()
        return removed

    def delete_program(self, program_name: str) -> bool:
        """Delete an entire program profile and all associated history cycles."""
        had_program = program_name in self.profiles
        self.history = [h for h in self.history if h.program_name != program_name]
        self._rebuild_profiles_from_history()
        self.profiles.pop(program_name, None)
        return had_program

    def clear_all(self) -> None:
        """Clear all learned history and profiles."""
        self.profiles.clear()
        self.history.clear()

    def _rebuild_profiles_from_history(self) -> None:
        """Rebuild profiles from history, preserving registered empty profiles."""
        empty_profiles = {
            name: ProgramProfile(name=name)
            for name, p in self.profiles.items()
            if p.sample_count == 0
        }
        self.profiles = empty_profiles
        for sample in self.history:
            if sample.program_name:
                if sample.program_name not in self.profiles:
                    self.profiles[sample.program_name] = ProgramProfile(name=sample.program_name)
                self.profiles[sample.program_name].update_with_sample(sample)

    def export_data(self) -> dict[str, Any]:
        """Export all profiles and history for persistent HA storage."""
        return {
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
            "history": [h.to_dict() for h in self.history],
        }
