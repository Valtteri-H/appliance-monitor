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


def build_cycle_summary_message(
    appliance_name: str, snapshot: CycleSnapshot, lang: str = "fi"
) -> tuple[str, str]:
    """Generate title and body text for finished cycle."""
    duration_min = round(snapshot.duration_seconds / 60.0)
    energy_kwh = round(snapshot.total_energy_kwh, 2)
    suggested = snapshot.program_name

    if lang == "fi":
        title = f"{appliance_name} on valmis!"
        parts = [f"Pesu kesti {duration_min} min"]
        if energy_kwh > 0.0:
            parts.append(f"sähköä kului {energy_kwh} kWh")
        body = ", ".join(parts) + "."
        if suggested:
            body += f" (Tunnistettu ohjelma: {suggested})"
    else:
        title = f"{appliance_name} is finished!"
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
) -> dict[str, Any]:
    """Build Home Assistant mobile app notification service data."""
    title, message = build_cycle_summary_message(appliance_name, snapshot, lang=lang)

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
