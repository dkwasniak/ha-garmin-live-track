from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GarminConfigEntry
from .const import CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME, DOMAIN, INTEGRATION_VERSION
from .coordinator import GarminLiveTrackCoordinator, GarminLiveTrackData


@dataclass(frozen=True, kw_only=True)
class GarminSensorDescription(SensorEntityDescription):
    value_fn: Callable[[GarminLiveTrackData], Any]


SENSORS: tuple[GarminSensorDescription, ...] = (
    GarminSensorDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.speed,
    ),
    GarminSensorDescription(
        key="heart_rate",
        translation_key="heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heart-pulse",
        value_fn=lambda d: d.heart_rate,
    ),
    GarminSensorDescription(
        key="altitude",
        translation_key="altitude",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.altitude,
    ),
    GarminSensorDescription(
        key="session_url",
        translation_key="session_url",
        device_class=SensorDeviceClass.URL,
        icon="mdi:map-marker-path",
        value_fn=lambda d: d.session_url,
    ),
    GarminSensorDescription(
        key="last_updated",
        translation_key="last_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.last_updated,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarminConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    name = entry.data.get(CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME)
    async_add_entities(
        GarminSensor(coordinator, entry, description, name)
        for description in SENSORS
    )


class GarminSensor(CoordinatorEntity[GarminLiveTrackCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: GarminSensorDescription

    def __init__(
        self,
        coordinator: GarminLiveTrackCoordinator,
        entry: GarminConfigEntry,
        description: GarminSensorDescription,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Garmin",
            model="LiveTrack",
            sw_version=INTEGRATION_VERSION,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
