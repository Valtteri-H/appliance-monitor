"""Tests for notifications formatting."""
from custom_components.appliance_monitor.notifications import (
    build_actionable_notification_payload,
    build_cycle_summary_message,
)
from custom_components.appliance_monitor.profile_engine import CycleSnapshot


def test_notifications_formatting_finnish():
    snap = CycleSnapshot(
        duration_seconds=3600.0,
        total_energy_kwh=0.854,
        program_name="Eco 40-60",
    )
    title, body = build_cycle_summary_message("Pyykinpesukone", snap, lang="fi")
    assert title == "Pyykinpesukone on valmis!"
    assert "60 min" in body
    assert "0.85 kWh" in body
    assert "Eco 40-60" in body

    payload = build_actionable_notification_payload(
        "Pyykinpesukone",
        "entry_123",
        snap,
        known_programs=["Eco 40-60", "Pika 30"],
        lang="fi",
    )
    assert payload["data"]["tag"] == "appliance_monitor_entry_123"
    actions = payload["data"]["actions"]
    assert len(actions) >= 2
    assert actions[0]["title"] == "✓ Eco 40-60"
    assert actions[-1]["title"] == "Sulje"
