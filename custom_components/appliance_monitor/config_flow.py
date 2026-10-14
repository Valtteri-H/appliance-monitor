"""Config flow and Options flow for Appliance Monitor."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_APPLIANCE_TYPE,
    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
    CONF_ENERGY_SENSOR,
    CONF_FINISHING_DELAY,
    CONF_FINISHING_POWER,
    CONF_NOTIFY_SERVICE,
    CONF_POWER_SENSOR,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    CONF_REMINDER_INTERVAL,
    CONF_STARTING_DELAY,
    CONF_STARTING_POWER,
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_REMINDER_INTERVAL,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
    DOMAIN,
    TYPE_CUSTOM,
    TYPE_DISHWASHER,
    TYPE_DRYER,
    TYPE_WASHING_MACHINE,
)
from .notifications import parse_time_str

_LOGGER = logging.getLogger(__name__)


def _num_sel(min_v: float, max_v: float, step: float, unit: str) -> selector.NumberSelector:
    """Helper to create a box number selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_v, max=max_v, step=step, unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _validate_config_input(
    user_input: dict[str, Any], is_options: bool = False
) -> dict[str, str]:
    """Validate user input for config flow or options flow."""
    errors: dict[str, str] = {}
    starting = user_input.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER)
    finishing = user_input.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER)
    if starting is not None and finishing is not None and starting <= finishing:
        errors["base"] = "invalid_power_thresholds"
    elif (
        not is_options
        and user_input.get(CONF_ENERGY_SENSOR)
        and user_input.get(CONF_ENERGY_SENSOR) == user_input.get(CONF_POWER_SENSOR)
    ):
        errors["base"] = "same_sensor"
    else:
        q_start = user_input.get(CONF_QUIET_HOURS_START)
        q_end = user_input.get(CONF_QUIET_HOURS_END)
        has_start = bool(isinstance(q_start, str) and q_start.strip())
        has_end = bool(isinstance(q_end, str) and q_end.strip())
        if (has_start or has_end) and not (
            has_start and has_end and parse_time_str(q_start) and parse_time_str(q_end)
        ):
            errors["base"] = "invalid_quiet_hours"
    return errors


class ApplianceMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Appliance Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_config_input(user_input, is_options=False)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_POWER_SENSOR])
                self._abort_if_unique_id_configured()

                title = user_input.get("name", "Appliance")
                return self.async_create_entry(title=title, data=user_input)

        current = user_input or {}
        data_schema = vol.Schema(
            {
                vol.Required("name", default="Pyykinpesukone"): selector.TextSelector(),
                vol.Required(CONF_POWER_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ENERGY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(
                    CONF_APPLIANCE_TYPE, default=TYPE_WASHING_MACHINE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            TYPE_WASHING_MACHINE,
                            TYPE_DISHWASHER,
                            TYPE_DRYER,
                            TYPE_CUSTOM,
                        ],
                        translation_key="appliance_type",
                    )
                ),
                vol.Optional(
                    CONF_STARTING_POWER, default=DEFAULT_STARTING_POWER
                ): _num_sel(1.0, 500.0, 1.0, "W"),
                vol.Optional(
                    CONF_FINISHING_POWER, default=DEFAULT_FINISHING_POWER
                ): _num_sel(0.5, 50.0, 0.5, "W"),
                vol.Optional(
                    CONF_STARTING_DELAY, default=DEFAULT_STARTING_DELAY
                ): _num_sel(5, 600, 5, "s"),
                vol.Optional(
                    CONF_FINISHING_DELAY, default=DEFAULT_FINISHING_DELAY
                ): _num_sel(30, 1800, 10, "s"),
                vol.Optional(
                    CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, default=True
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_QUIET_HOURS_START, default=current.get(CONF_QUIET_HOURS_START, "")
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_QUIET_HOURS_END, default=current.get(CONF_QUIET_HOURS_END, "")
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_REMINDER_INTERVAL,
                    default=current.get(CONF_REMINDER_INTERVAL, DEFAULT_REMINDER_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=240, step=5, unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ApplianceMonitorOptionsFlow:
        """Get options flow."""
        return ApplianceMonitorOptionsFlow(config_entry)


class ApplianceMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Appliance Monitor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_config_input(user_input, is_options=True)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current = {**(self.config_entry.options or self.config_entry.data), **(user_input or {})}

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_STARTING_POWER,
                    default=current.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER),
                ): _num_sel(1.0, 500.0, 1.0, "W"),
                vol.Optional(
                    CONF_FINISHING_POWER,
                    default=current.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER),
                ): _num_sel(0.5, 50.0, 0.5, "W"),
                vol.Optional(
                    CONF_STARTING_DELAY,
                    default=current.get(CONF_STARTING_DELAY, DEFAULT_STARTING_DELAY),
                ): _num_sel(5, 600, 5, "s"),
                vol.Optional(
                    CONF_FINISHING_DELAY,
                    default=current.get(CONF_FINISHING_DELAY, DEFAULT_FINISHING_DELAY),
                ): _num_sel(30, 1800, 10, "s"),
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=current.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
                    default=current.get(CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, True),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_QUIET_HOURS_START,
                    default=current.get(CONF_QUIET_HOURS_START, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_QUIET_HOURS_END,
                    default=current.get(CONF_QUIET_HOURS_END, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_REMINDER_INTERVAL,
                    default=current.get(CONF_REMINDER_INTERVAL, DEFAULT_REMINDER_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=240, step=5, unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema, errors=errors)
