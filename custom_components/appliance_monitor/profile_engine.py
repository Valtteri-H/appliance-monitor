"""Power signature analysis and adaptive program learning engine."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CycleSnapshot:
    """Snapshot of a single cycle execution."""

    duration_seconds: float = 0.0
    total_energy_kwh: float = 0.0
    max_power_w: float = 0.0
    heating_duration_seconds: float = 0.0
    heating_energy_kwh: float = 0.0
    weighing_pulses: int = 0
    high_spin_detected: bool = False
    timestamp: float = field(default_factory=time.time)
    program_name: str | None = None
    confirmed_by_user: bool = False

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
        """Incrementally update profile statistics with a new sample."""
        n = self.sample_count
        new_n = n + 1
        self.sample_count = new_n

        self.avg_duration_seconds = (
            self.avg_duration_seconds * n + sample.duration_seconds
        ) / new_n
        self.avg_total_energy_kwh = (
            self.avg_total_energy_kwh * n + sample.total_energy_kwh
        ) / new_n
        self.avg_heating_energy_kwh = (
            self.avg_heating_energy_kwh * n + sample.heating_energy_kwh
        ) / new_n
        self.avg_heating_duration_seconds = (
            self.avg_heating_duration_seconds * n + sample.heating_duration_seconds
        ) / new_n

        self.max_power_w = max(self.max_power_w, sample.max_power_w)

        spin_val = 1.0 if sample.high_spin_detected else 0.0
        self.high_spin_frequency = (self.high_spin_frequency * n + spin_val) / new_n

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProgramProfile:
        """Create profile from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProfileEngine:
    """Engine for tracking live signatures, matching against learned profiles and learning."""

    HEATING_POWER_THRESHOLD = 1500.0  # W (heating element active)
    SPIN_POWER_THRESHOLD = 350.0     # W (high speed motor spin)
    WEIGHING_MIN_POWER = 30.0        # W
    WEIGHING_MAX_POWER = 250.0       # W

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
        score = 0.0
        weights_sum = 0.0

        # Heating energy is the strongest signature for wash temperature (30/40/60/90)
        if profile.avg_heating_energy_kwh > 0.05:
            heat_diff = abs(current.heating_energy_kwh - profile.avg_heating_energy_kwh)
            heat_score = max(0.0, 1.0 - (heat_diff / (profile.avg_heating_energy_kwh * 0.4 + 0.1)))
            score += heat_score * 0.4
            weights_sum += 0.4

        # Heating duration
        if profile.avg_heating_duration_seconds > 60:
            h_dur_diff = abs(
                current.heating_duration_seconds - profile.avg_heating_duration_seconds
            )
            h_dur_score = max(
                0.0, 1.0 - (h_dur_diff / (profile.avg_heating_duration_seconds * 0.4 + 60))
            )
            score += h_dur_score * 0.2
            weights_sum += 0.2

        if not partial:
            # Full cycle duration score
            if profile.avg_duration_seconds > 0:
                dur_diff = abs(current.duration_seconds - profile.avg_duration_seconds)
                dur_score = max(
                    0.0, 1.0 - (dur_diff / (profile.avg_duration_seconds * 0.35 + 180))
                )
                score += dur_score * 0.3
                weights_sum += 0.3

            # Total energy score
            if profile.avg_total_energy_kwh > 0:
                en_diff = abs(current.total_energy_kwh - profile.avg_total_energy_kwh)
                en_score = max(
                    0.0, 1.0 - (en_diff / (profile.avg_total_energy_kwh * 0.35 + 0.1))
                )
                score += en_score * 0.1
                weights_sum += 0.1
        else:
            # In partial mode (cycle running), verify current duration hasn't far exceeded profile
            if (
                profile.avg_duration_seconds > 0
                and current.duration_seconds > profile.avg_duration_seconds * 1.3
            ):
                score *= 0.5

        if weights_sum == 0.0:
            return 0.0
        return min(1.0, max(0.0, score / weights_sum))

    def predict_program(
        self, current: CycleSnapshot, partial: bool = False
    ) -> tuple[str | None, float]:
        """Predict the program name and confidence score (0.0 - 1.0)."""
        if not self.profiles:
            return None, 0.0

        best_prog = None
        best_score = 0.0

        for name, profile in self.profiles.items():
            sim = self.calculate_similarity(current, profile, partial=partial)
            if sim > best_score:
                best_score = sim
                best_prog = name

        if best_score < 0.45:
            return None, best_score

        return best_prog, best_score

    def estimate_remaining_time(
        self, current: CycleSnapshot, predicted_program: str | None
    ) -> float | None:
        """Estimate remaining seconds in cycle based on predicted profile."""
        if not predicted_program or predicted_program not in self.profiles:
            return None

        profile = self.profiles[predicted_program]
        if profile.avg_duration_seconds <= 0:
            return None

        remaining = profile.avg_duration_seconds - current.duration_seconds
        return max(0.0, remaining)

    def learn_cycle(self, snapshot: CycleSnapshot, program_name: str) -> None:
        """Learn and store a completed cycle with user confirmed program name."""
        snapshot.program_name = program_name
        snapshot.confirmed_by_user = True
        self.history.append(snapshot)

        if program_name not in self.profiles:
            self.profiles[program_name] = ProgramProfile(name=program_name)

        self.profiles[program_name].update_with_sample(snapshot)

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
        return had_program

    def clear_all(self) -> None:
        """Clear all learned history and profiles."""
        self.profiles.clear()
        self.history.clear()

    def _rebuild_profiles_from_history(self) -> None:
        """Rebuild profiles from current history list."""
        self.profiles.clear()
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
