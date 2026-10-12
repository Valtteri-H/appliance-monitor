# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-10-12

### Added
- Text entity platform (`text.<appliance>_program_text`) for entering and learning custom program names.

## [1.0.1] - 2026-10-12

### Added
- `hacs.json` for HACS validation.
- `services.yaml` describing `delete_program` and `clear_history` services and required fields.
- `starting_delay` configuration field in Config Flow and Options Flow.
- Validation rejecting identical power and energy sensor selections, or starting threshold below finishing threshold.
- Actionable notification listener (`mobile_app_notification_action`) for program confirmation actions.
- `SensorDeviceClass.ENUM` for status and phase sensors.

### Changed
- `manifest.json`: updated `iot_class` to `calculated`.
- `profile_engine.py`: capped cycle history at 100 entries to prevent unbounded storage growth.
- `coordinator.py`: monotonic time tracking to prevent clock drift issues, and non-negative clamping on incoming power values.
- `__init__.py`: added `asyncio.Lock` around store writes and protected notification dispatch from exceptions.

## [1.0.0] - 2026-10-12

### Added
- Power signature profiling for heating cycles and spin stages.
- State machine for cycle detection and pause handling.
- Sensors for status, phase, program, remaining time, duration, and energy.
- Config Flow and Options Flow with English and Finnish translations.
- Actionable mobile notifications.
- Services for profile deletion and history resets.
- Unit and integration tests.
