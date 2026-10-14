"""Interactive and actionable notifications for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

from .const import (
    ACTION_CONFIRM_PROGRAM,
    ACTION_DISMISS,
)
from .profile_engine import CycleSnapshot

_LOGGER = logging.getLogger(__name__)


def parse_time_str(time_str: str | None) -> tuple[int, int] | None:
    """Parse 'HH:MM' or 'HH:MM:SS' time into (hour, minute)."""
    if not time_str or not isinstance(time_str, str):
        return None
    parts = time_str.strip().split(":")
    if len(parts) not in (2, 3):
        return None
    if not all(p.isdigit() for p in parts):
        return None
    try:
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        if len(parts) == 3 and not (0 <= int(parts[2]) <= 59):
            return None
        return (hour, minute)
    except (ValueError, TypeError):
        return None


def is_within_quiet_hours(
    now_hm: tuple[int, int], start_str: str | None, end_str: str | None
) -> bool:
    """Check if (hour, minute) falls within quiet hours (handles cross-midnight)."""
    start = parse_time_str(start_str)
    end = parse_time_str(end_str)
    if start is None or end is None or start == end:
        return False

    now_m = now_hm[0] * 60 + now_hm[1]
    start_m = start[0] * 60 + start[1]
    end_m = end[0] * 60 + end[1]

    if start_m < end_m:
        return start_m <= now_m < end_m
    return now_m >= start_m or now_m < end_m


def seconds_until_quiet_hours_end(now_hm: tuple[int, int], end_str: str | None) -> float:
    """Calculate seconds until quiet hours end (minimum 60.0s)."""
    end = parse_time_str(end_str)
    if end is None:
        return 60.0

    now_m = now_hm[0] * 60 + now_hm[1]
    end_m = end[0] * 60 + end[1]

    if end_m > now_m:
        diff_minutes = end_m - now_m
    else:
        diff_minutes = (24 * 60) - now_m + end_m

    return max(60.0, float(diff_minutes * 60.0))


def build_cycle_summary_message(
    appliance_name: str,
    snapshot: CycleSnapshot,
    lang: str = "fi",
    is_reminder: bool = False,
) -> tuple[str, str]:
    """Generate title and body text for finished cycle."""
    duration_min = round(snapshot.duration_seconds / 60.0)
    energy_kwh = round(snapshot.total_energy_kwh, 2)
    suggested = snapshot.program_name

    if lang == "fi":
        title = (
            f"Muistutus: {appliance_name} on valmis!"
            if is_reminder
            else f"{appliance_name} on valmis!"
        )
        parts = [f"Pesu kesti {duration_min} min"]
        if energy_kwh > 0.0:
            parts.append(f"sähköä kului {energy_kwh} kWh")
        body = ", ".join(parts) + "."
        if suggested:
            body += f" (Tunnistettu ohjelma: {suggested})"
    else:
        title = (
            f"Reminder: {appliance_name} is finished!"
            if is_reminder
            else f"{appliance_name} is finished!"
        )
        parts = [f"Cycle duration {duration_min} min"]
        if energy_kwh > 0.0:
            parts.append(f"energy {energy_kwh} kWh")
        body = ", ".join(parts) + "."
        if suggested:
            body += f" (Detected program: {suggested})"

    return title, body


def build_actionable_notification_payload(
    appliance_name: str,
    entry_id: str,
    snapshot: CycleSnapshot,
    known_programs: list[str],
    lang: str = "fi",
    is_reminder: bool = False,
) -> dict[str, Any]:
    """Build Home Assistant mobile app notification service data."""
    title, message = build_cycle_summary_message(
        appliance_name, snapshot, lang=lang, is_reminder=is_reminder
    )

    # Offer quick confirmation actions
    actions = []
    # If a predicted program is present, offer it as primary quick button
    if snapshot.program_name:
        actions.append(
            {
                "action": f"{ACTION_CONFIRM_PROGRAM}_{entry_id}_{snapshot.program_name}",
                "title": f"✓ {snapshot.program_name}",
            }
        )

    # Add other top known programs up to 2
    for prog in known_programs:
        if prog != snapshot.program_name and len(actions) < 3:
            actions.append(
                {
                    "action": f"{ACTION_CONFIRM_PROGRAM}_{entry_id}_{prog}",
                    "title": prog,
                }
            )

    actions.append(
        {
            "action": f"{ACTION_DISMISS}_{entry_id}",
            "title": "Sulje" if lang == "fi" else "Dismiss",
        }
    )

    return {
        "title": title,
        "message": message,
        "data": {
            "tag": f"appliance_monitor_{entry_id}",
            "actions": actions,
        },
    }
