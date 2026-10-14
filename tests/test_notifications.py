"""Tests for notifications formatting."""
from custom_components.appliance_monitor.notifications import (
    build_actionable_notification_payload,
    build_cycle_summary_message,
    is_within_quiet_hours,
    parse_time_str,
    seconds_until_quiet_hours_end,
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
    assert actions[0]["action"] == "APPLIANCE_MONITOR_CONFIRM_entry_123_Eco 40-60"
    assert actions[-1]["title"] == "Sulje"
    assert actions[-1]["action"] == "APPLIANCE_MONITOR_DISMISS_entry_123"


def test_quiet_hours_and_parsing():
    # Kelvolliset
    assert parse_time_str("22:00") == (22, 0)
    assert parse_time_str("07:30:00") == (7, 30)

    # Virheelliset
    assert parse_time_str("") is None
    assert parse_time_str("25:00") is None
    assert parse_time_str("abc") is None
    assert parse_time_str(None) is None
    assert parse_time_str("12:60") is None
    assert parse_time_str("12:30:99") is None

    # is_within_quiet_hours saman vuorokauden välillä ('09:00'-'17:00')
    assert is_within_quiet_hours((8, 59), "09:00", "17:00") is False
    assert is_within_quiet_hours((9, 0), "09:00", "17:00") is True
    assert is_within_quiet_hours((12, 0), "09:00", "17:00") is True
    assert is_within_quiet_hours((16, 59), "09:00", "17:00") is True
    assert is_within_quiet_hours((17, 0), "09:00", "17:00") is False
    assert is_within_quiet_hours((18, 0), "09:00", "17:00") is False

    # is_within_quiet_hours keskiyön yli ('22:00'-'07:00')
    assert is_within_quiet_hours((23, 30), "22:00", "07:00") is True
    assert is_within_quiet_hours((2, 15), "22:00", "07:00") is True
    assert is_within_quiet_hours((12, 0), "22:00", "07:00") is False
    assert is_within_quiet_hours((21, 59), "22:00", "07:00") is False
    assert is_within_quiet_hours((22, 0), "22:00", "07:00") is True
    assert is_within_quiet_hours((6, 59), "22:00", "07:00") is True
    assert is_within_quiet_hours((7, 0), "22:00", "07:00") is False

    # Virheelliset hiljaiset tunnit
    assert is_within_quiet_hours((12, 0), "invalid", "07:00") is False
    assert is_within_quiet_hours((12, 0), "07:00", "07:00") is False

    # seconds_until_quiet_hours_end
    # Keskiyön yli: klo 23:30 -> 07:00 (30 min + 420 min = 450 min = 27000.0s)
    assert seconds_until_quiet_hours_end((23, 30), "07:00") == 27000.0
    # Saman vuorokauden sisällä: klo 02:00 -> 07:00 (5 h = 300 min = 18000.0s)
    assert seconds_until_quiet_hours_end((2, 0), "07:00") == 18000.0
    # Saman vuorokauden väli: klo 10:00 -> 17:00 (7 h = 420 min = 25200.0s)
    assert seconds_until_quiet_hours_end((10, 0), "17:00") == 25200.0
    # Virheellinen end_str palauttaa oletuksen 60.0s
    assert seconds_until_quiet_hours_end((10, 0), None) == 60.0
    # Jos aika on täsmälleen loppuaika, seuraavaan loppuun on 24h (86400.0s)
    assert seconds_until_quiet_hours_end((7, 0), "07:00") == 86400.0


def test_notifications_english_and_reminder():
    snap = CycleSnapshot(
        duration_seconds=7200.0,
        total_energy_kwh=1.25,
        program_name="Cotton 60",
    )

    # Englanti ilman muistutusta
    title_en, body_en = build_cycle_summary_message(
        "Washing machine", snap, lang="en", is_reminder=False
    )
    assert title_en == "Washing machine is finished!"
    assert "Cycle duration 120 min" in body_en
    assert "energy 1.25 kWh" in body_en
    assert "Detected program: Cotton 60" in body_en

    # Englanti muistutuksella
    title_rem, body_rem = build_cycle_summary_message(
        "Washing machine", snap, lang="en", is_reminder=True
    )
    assert title_rem == "Reminder: Washing machine is finished!"
    assert "Cycle duration 120 min" in body_rem

    # Suomi muistutuksella
    title_fi_rem, _ = build_cycle_summary_message(
        "Pyykinpesukone", snap, lang="fi", is_reminder=True
    )
    assert title_fi_rem == "Muistutus: Pyykinpesukone on valmis!"

    # Actionable payload englanniksi ja muistutuksella
    payload = build_actionable_notification_payload(
        "Washing machine",
        "entry_abc",
        snap,
        known_programs=["Cotton 60", "Synthetic 40", "Quick 30"],
        lang="en",
        is_reminder=True,
    )
    assert payload["title"] == "Reminder: Washing machine is finished!"
    actions = payload["data"]["actions"]
    # Ensimmäinen toiminto: ennustettu ohjelma
    assert actions[0]["title"] == "✓ Cotton 60"
    assert actions[0]["action"] == "APPLIANCE_MONITOR_CONFIRM_entry_abc_Cotton 60"
    # Tunnettu lisäohjelma
    assert actions[1]["title"] == "Synthetic 40"
    assert actions[1]["action"] == "APPLIANCE_MONITOR_CONFIRM_entry_abc_Synthetic 40"
    # Viimeinen toiminto: Dismiss
    assert actions[-1]["title"] == "Dismiss"
    assert actions[-1]["action"] == "APPLIANCE_MONITOR_DISMISS_entry_abc"

