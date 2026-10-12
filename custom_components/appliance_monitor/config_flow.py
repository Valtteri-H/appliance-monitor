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
    CONF_STARTING_DELAY,
    CONF_STARTING_POWER,
    DEFAULT_FINISHING_DELAY,
    DEFAULT_FINISHING_POWER,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_STARTING_DELAY,
    DEFAULT_STARTING_POWER,
    DOMAIN,
    TYPE_CUSTOM,
    TYPE_DISHWASHER,
    TYPE_DRYER,
    TYPE_WASHING_MACHINE,
)

_LOGGER = logging.getLogger(__name__)


class ApplianceMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Appliance Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            starting = user_input.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER)
            finishing = user_input.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER)
            if starting <= finishing:
                errors["base"] = "invalid_power_thresholds"
            elif (
                user_input.get(CONF_ENERGY_SENSOR)
                and user_input.get(CONF_ENERGY_SENSOR) == user_input.get(CONF_POWER_SENSOR)
            ):
                errors["base"] = "same_sensor"
            else:
                # Check unique name / power sensor
                await self.async_set_unique_id(user_input[CONF_POWER_SENSOR])
                self._abort_if_unique_id_configured()

                title = user_input.get("name", "Appliance")
                return self.async_create_entry(title=title, data=user_input)

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
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=500.0, step=1.0, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_FINISHING_POWER, default=DEFAULT_FINISHING_POWER
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=50.0, step=0.5, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_STARTING_DELAY, default=DEFAULT_STARTING_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=600, step=5, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_FINISHING_DELAY, default=DEFAULT_FINISHING_DELAY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=30, max=1800, step=10, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, default=True
                ): selector.BooleanSelector(),
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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options or self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_STARTING_POWER,
                    default=current.get(CONF_STARTING_POWER, DEFAULT_STARTING_POWER),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1.0, max=500.0, step=1.0, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_FINISHING_POWER,
                    default=current.get(CONF_FINISHING_POWER, DEFAULT_FINISHING_POWER),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=50.0, step=0.5, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_STARTING_DELAY,
                    default=current.get(CONF_STARTING_DELAY, DEFAULT_STARTING_DELAY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=600, step=5, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_FINISHING_DELAY,
                    default=current.get(CONF_FINISHING_DELAY, DEFAULT_FINISHING_DELAY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=30, max=1800, step=10, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=current.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_ENABLE_ACTIONABLE_NOTIFICATIONS,
                    default=current.get(CONF_ENABLE_ACTIONABLE_NOTIFICATIONS, True),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
