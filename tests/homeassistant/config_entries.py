from . import ConfigEntry

__all__ = ["ConfigEntry", "ConfigFlow", "ConfigFlowResult", "OptionsFlow"]


class ConfigFlow:
    VERSION = 1

    def __init_subclass__(cls, domain: str = "", **kwargs):
        super().__init_subclass__(**kwargs)
        cls.DOMAIN = domain

    async def async_set_unique_id(self, unique_id: str):
        pass

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, title: str, data: dict):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, step_id: str, data_schema, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}


class OptionsFlow:
    _config_entry: ConfigEntry | None = None

    @property
    def config_entry(self) -> ConfigEntry:
        if self._config_entry is None:
            raise AttributeError("config_entry not initialized")
        return self._config_entry

    def async_create_entry(self, title: str, data: dict):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, step_id: str, data_schema, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}


class ConfigFlowResult(dict):
    pass
