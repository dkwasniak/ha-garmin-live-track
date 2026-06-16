from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    GARMIN_API_HEADERS,
    GARMIN_API_URL,
    DEFAULT_POLL_INTERVAL,
    SESSION_TIMEOUT_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class GarminLiveTrackData:
    lat: float | None = None
    lon: float | None = None
    speed: float | None = None
    altitude: float | None = None
    heart_rate: int | None = None
    last_updated: datetime | None = None
    session_id: str | None = None
    session_url: str | None = None
    session_started: datetime | None = None
    active: bool = False


class GarminLiveTrackCoordinator(DataUpdateCoordinator[GarminLiveTrackData]):
    def __init__(self, hass: HomeAssistant, poll_interval: int = DEFAULT_POLL_INTERVAL) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self.data = GarminLiveTrackData()

    def start_session(self, session_id: str, session_url: str) -> None:
        self.data.session_id = session_id
        self.data.session_url = session_url
        self.data.session_started = datetime.now(tz=timezone.utc)
        self.data.active = True
        _LOGGER.info("LiveTrack session started: %s", session_id)

    def stop_session(self) -> None:
        self.data.session_id = None
        self.data.session_url = None
        self.data.session_started = None
        self.data.active = False
        self.data.lat = None
        self.data.lon = None
        self.data.speed = None
        self.data.altitude = None
        self.data.heart_rate = None
        _LOGGER.info("LiveTrack session stopped")

    def _is_session_expired(self) -> bool:
        if not self.data.session_started:
            return False
        age = datetime.now(tz=timezone.utc) - self.data.session_started
        return age > timedelta(hours=SESSION_TIMEOUT_HOURS)

    async def _async_update_data(self) -> GarminLiveTrackData:
        if not self.data.session_id or not self.data.active:
            return self.data

        if self._is_session_expired():
            _LOGGER.info("LiveTrack session expired, stopping")
            self.stop_session()
            return self.data

        url = GARMIN_API_URL.format(session_id=self.data.session_id)
        params = {"requestTime": int(time.time() * 1000)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=GARMIN_API_HEADERS,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 404:
                        _LOGGER.debug("No trackpoints yet for session %s", self.data.session_id)
                        return self.data

                    if resp.status != 200:
                        raise UpdateFailed(f"Garmin API returned {resp.status}")

                    body = await resp.json()
                    trackpoints = (body.get("trackPointList") or {}).get("trackPoints") or []
                    if not trackpoints:
                        return self.data

                    latest = trackpoints[-1]
                    self.data.lat = latest.get("lat")
                    self.data.lon = latest.get("lon")
                    self.data.speed = latest.get("speed")
                    self.data.altitude = latest.get("altitude")
                    self.data.heart_rate = latest.get("heartRate")
                    self.data.last_updated = datetime.now(tz=timezone.utc)

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Garmin API: {err}") from err

        return self.data
