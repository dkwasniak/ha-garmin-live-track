from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GarminConfigEntry
from .const import CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME, DOMAIN, INTEGRATION_VERSION
from .coordinator import GarminLiveTrackCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([StopTrackingButton(entry.runtime_data, entry)])


class StopTrackingButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "stop_tracking"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: GarminLiveTrackCoordinator, entry: GarminConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_stop_tracking"
        name = entry.data.get(CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Garmin",
            model="LiveTrack",
            sw_version=INTEGRATION_VERSION,
        )

    async def async_press(self) -> None:
        self._coordinator.stop_session()
        await self._coordinator.async_refresh()
