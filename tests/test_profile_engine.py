"""Unit tests for the Appliance Monitor profile engine."""
import pytest

from custom_components.appliance_monitor.profile_engine import (
    CycleSnapshot,
    ProfileEngine,
)


def test_profile_engine_learning_and_prediction():
    engine = ProfileEngine()

    # Opitaan "Pika 30"
    quick_sample = CycleSnapshot(
        duration_seconds=1800.0,
        total_energy_kwh=0.35,
        max_power_w=2050.0,
        heating_duration_seconds=300.0,
        heating_energy_kwh=0.18,
        high_spin_detected=True,
    )
    engine.learn_cycle(quick_sample, "Pika 30")

    # Opitaan "Eco 40-60"
    eco_sample = CycleSnapshot(
        duration_seconds=9000.0,
        total_energy_kwh=0.85,
        max_power_w=2100.0,
        heating_duration_seconds=900.0,
        heating_energy_kwh=0.52,
        high_spin_detected=True,
    )
    engine.learn_cycle(eco_sample, "Eco 40-60")

    assert len(engine.profiles) == 2
    assert "Pika 30" in engine.profiles
    assert "Eco 40-60" in engine.profiles

    # Testataan ennustusta uudelle Pika 30 -syklille
    incoming_quick = CycleSnapshot(
        duration_seconds=1850.0,
        total_energy_kwh=0.36,
        max_power_w=2000.0,
        heating_duration_seconds=310.0,
        heating_energy_kwh=0.19,
        high_spin_detected=True,
    )
    prog, score = engine.predict_program(incoming_quick, partial=False)
    assert prog == "Pika 30"
    assert score > 0.85

    # Testataan ennustusta käynnissä olevalle syklille (lämmityksen perusteella)
    running_eco = CycleSnapshot(
        duration_seconds=2000.0,
        total_energy_kwh=0.55,
        max_power_w=2100.0,
        heating_duration_seconds=880.0,
        heating_energy_kwh=0.50,
        high_spin_detected=False,
    )
    prog_running, score_running = engine.predict_program(running_eco, partial=True)
    assert prog_running == "Eco 40-60"
    assert score_running > 0.70

    # Testataan jäljellä olevan ajan arviointia
    rem = engine.estimate_remaining_time(running_eco, prog_running)
    assert rem is not None
    assert rem == pytest.approx(7000.0, rel=1e-2)


def test_profile_engine_forget_and_delete():
    engine = ProfileEngine()

    sample1 = CycleSnapshot(
        duration_seconds=1800.0,
        total_energy_kwh=0.35,
        heating_energy_kwh=0.18,
        heating_duration_seconds=300.0,
    )
    engine.learn_cycle(sample1, "Väärä ohjelma")
    assert "Väärä ohjelma" in engine.profiles
    assert len(engine.history) == 1

    # Poistetaan viimeisin sykli
    removed = engine.forget_last_cycle()
    assert removed is not None
    assert removed.program_name == "Väärä ohjelma"
    assert len(engine.history) == 0
    assert "Väärä ohjelma" not in engine.profiles

    # Lisätään ja poistetaan koko profiili
    engine.learn_cycle(sample1, "Testi")
    assert engine.delete_program("Testi") is True
    assert "Testi" not in engine.profiles
    assert len(engine.history) == 0
