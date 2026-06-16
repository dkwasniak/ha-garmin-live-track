from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GarminConfigEntry
from .const import CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME, DOMAIN, INTEGRATION_VERSION
from .coordinator import GarminLiveTrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([GarminTracker(entry.runtime_data, entry)])


class GarminTracker(CoordinatorEntity[GarminLiveTrackCoordinator], TrackerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:run"

    def __init__(self, coordinator: GarminLiveTrackCoordinator, entry: GarminConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_tracker"
        name = entry.data.get(CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Garmin",
            model="LiveTrack",
            sw_version=INTEGRATION_VERSION,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.data.active and self.coordinator.data.lat is not None

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self.coordinator.data.lat

    @property
    def longitude(self) -> float | None:
        return self.coordinator.data.lon

    @property
    def location_accuracy(self) -> int:
        return 10

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {
            "session_url": data.session_url,
            "session_status": data.session_status,
            "speed": data.speed,
            "altitude": data.altitude,
            "heart_rate": data.heart_rate,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
