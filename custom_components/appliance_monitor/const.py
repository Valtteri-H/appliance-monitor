"""Constants for Appliance Monitor integration."""
from __future__ import annotations

DOMAIN = "appliance_monitor"
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "appliance_monitor"

# Configuration keys
CONF_POWER_SENSOR = "power_sensor"
CONF_ENERGY_SENSOR = "energy_sensor"
CONF_STARTING_POWER = "starting_power"
CONF_FINISHING_POWER = "finishing_power"
CONF_STARTING_DELAY = "starting_delay"
CONF_FINISHING_DELAY = "finishing_delay"
CONF_APPLIANCE_TYPE = "appliance_type"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_ENABLE_ACTIONABLE_NOTIFICATIONS = "enable_actionable_notifications"

# Appliance types
TYPE_WASHING_MACHINE = "washing_machine"
TYPE_DISHWASHER = "dishwasher"
TYPE_DRYER = "dryer"
TYPE_CUSTOM = "custom"

# Default values
DEFAULT_STARTING_POWER = 10.0  # W
DEFAULT_FINISHING_POWER = 3.0   # W
DEFAULT_STARTING_DELAY = 60     # seconds
DEFAULT_FINISHING_DELAY = 300   # 5 minutes
DEFAULT_NOTIFY_SERVICE = "notify.notify"

# Cycle states
STATE_OFF = "off"
STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_PAUSED = "paused"
STATE_FINISHED = "finished"

# Cycle phases
PHASE_IDLE = "idle"
PHASE_WEIGHING = "weighing"
PHASE_WASHING_HEATING = "heating"
PHASE_RINSING = "rinsing"
PHASE_SPINNING = "spinning"
PHASE_DRYING = "drying"
PHASE_UNKNOWN = "running"

# Events
EVENT_CYCLE_STARTED = "appliance_monitor_started"
EVENT_CYCLE_FINISHED = "appliance_monitor_finished"
EVENT_PROGRAM_PREDICTED = "appliance_monitor_program_predicted"
EVENT_PROGRAM_CONFIRMED = "appliance_monitor_program_confirmed"

# Actions for interactive notifications
ACTION_CONFIRM_PROGRAM = "APPLIANCE_MONITOR_CONFIRM"
ACTION_DISMISS = "APPLIANCE_MONITOR_DISMISS"
