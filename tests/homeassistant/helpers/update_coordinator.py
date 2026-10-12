class DataUpdateCoordinator:
    def __init__(self, hass, logger, name=""):
        self.hass = hass
        self.logger = logger
        self.name = name
        self._listeners = []

    def async_update_listeners(self):
        for l in self._listeners:
            l()

class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)

    def async_write_ha_state(self):
        pass
