# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- **Power Signature Engine (`profile_engine.py`):**
  - Adaptive cycle profiling based on heating energy, motor spin phases, and pulse characteristics.
  - Automatic wash program matching with confidence scores.
  - Real-time remaining cycle time estimation (ETA).
- **Failsafe State Machine (`coordinator.py`):**
  - Robust noise and transient spike filtering.
  - Soaking and pause phase handling (`paused`) preventing premature cycle finish notifications.
- **Entity Suite:**
  - `sensor.<appliance>_status` (`idle`, `running`, `paused`, `finished`).
  - `sensor.<appliance>_phase` (`weighing`, `heating`, `rinsing`, `spinning`, `drying`).
  - `sensor.<appliance>_program` (detected or confirmed program name).
  - `sensor.<appliance>_remaining_time` (estimated minutes left).
  - `sensor.<appliance>_cycle_duration` (active or last cycle duration in minutes).
  - `sensor.<appliance>_cycle_energy` (active or last cycle energy consumption in kWh).
  - `binary_sensor.<appliance>_running` (simple on/off state for automations).
  - `select.<appliance>_program_select` (interactive UI selector to teach or confirm programs).
  - `button.<appliance>_reset` (manual reset to idle state).
  - `button.<appliance>_forget_last` (delete misclassified cycle from learned history).
- **Interactive Notifications (`notifications.py`):**
  - Actionable mobile notifications upon cycle finish with quick-select buttons for program verification.
- **Home Assistant Services:**
  - `appliance_monitor.delete_program` (remove learned program profile).
  - `appliance_monitor.clear_history` (reset all recorded cycle histories).
- **UI Configuration:**
  - Full Config Flow and Options Flow with multi-language support (English and Finnish).
- **Testing & Quality Assurance:**
  - Unit and integration tests covering cycle tracking, signature learning, and event flows.
