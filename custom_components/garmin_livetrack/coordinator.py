from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    GARMIN_API_HEADERS,
    GARMIN_API_URL,
    GARMIN_PAGE_HEADERS,
    GARMIN_SESSION_URL,
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
    last_track_point_time: datetime | None = None
    session_id: str | None = None
    token: str | None = None
    session_url: str | None = None
    session_started: datetime | None = None
    session_ended: datetime | None = None
    active: bool = False

    @property
    def session_status(self) -> str:
        if self.active:
            return "active"
        if self.session_ended:
            return "ended"
        return "no_active_session"


class GarminLiveTrackCoordinator(DataUpdateCoordinator[GarminLiveTrackData]):
    def __init__(self, hass: HomeAssistant, poll_interval: int = DEFAULT_POLL_INTERVAL) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self.data = GarminLiveTrackData()
        self._cookie_jar = aiohttp.CookieJar()
        self._csrf_token: str | None = None

    def start_session(
        self, session_id: str, session_url: str, token: str | None = None
    ) -> None:
        self.data.session_id = session_id
        self.data.token = token or _extract_token_from_url(session_url)
        self.data.session_url = session_url
        self.data.session_started = datetime.now(tz=timezone.utc)
        self.data.session_ended = None
        self.data.last_track_point_time = None
        self.data.active = True
        self._cookie_jar = aiohttp.CookieJar()
        self._csrf_token = None
        _LOGGER.info("LiveTrack session started: %s", session_id)

    def stop_session(self) -> None:
        self.data.session_id = None
        self.data.token = None
        self.data.session_url = None
        self.data.session_started = None
        self.data.session_ended = None
        self.data.last_track_point_time = None
        self.data.active = False
        self._clear_position_data()
        self._cookie_jar = aiohttp.CookieJar()
        self._csrf_token = None
        _LOGGER.info("LiveTrack session stopped")

    def _mark_session_ended(self, ended: datetime | None = None) -> None:
        self.data.active = False
        self.data.session_ended = ended or datetime.now(tz=timezone.utc)
        self._clear_position_data()
        _LOGGER.info("LiveTrack session ended: %s", self.data.session_id)

    def _clear_position_data(self) -> None:
        self.data.lat = None
        self.data.lon = None
        self.data.speed = None
        self.data.altitude = None
        self.data.heart_rate = None
        self.data.last_updated = None
        self.data.last_track_point_time = None

    def _is_session_expired(self) -> bool:
        reference_time = self.data.session_ended or self.data.session_started
        if not reference_time:
            return False
        age = datetime.now(tz=timezone.utc) - reference_time
        return age > timedelta(hours=SESSION_TIMEOUT_HOURS)

    async def _async_update_data(self) -> GarminLiveTrackData:
        if not self.data.session_id:
            return self.data

        if not self.data.active:
            if self._is_session_expired():
                _LOGGER.info("LiveTrack ended session expired, clearing")
                self.stop_session()
            return self.data

        if not self.data.token:
            _LOGGER.warning("LiveTrack session has no token, cannot poll Garmin API")
            return self.data

        if self._is_session_expired():
            _LOGGER.info("LiveTrack session expired, stopping")
            self.stop_session()
            return self.data

        url = GARMIN_API_URL.format(session_id=self.data.session_id)
        begin = self.data.last_track_point_time or (
            self.data.session_started - timedelta(minutes=5)
            if self.data.session_started
            else datetime.now(tz=timezone.utc)
        )
        params = {
            "token": self.data.token,
            "begin": _format_garmin_time(begin or datetime.now(tz=timezone.utc)),
        }

        try:
            async with aiohttp.ClientSession(cookie_jar=self._cookie_jar) as session:
                if not self._csrf_token:
                    await self._async_bootstrap_garmin_session(session)

                session_data = await self._async_fetch_garmin_session(session)
                ended = _get_session_end_time(session_data)
                if ended and ended <= datetime.now(tz=timezone.utc):
                    self._mark_session_ended(ended)
                    if self._is_session_expired():
                        self.stop_session()
                    return self.data

                for attempt in range(2):
                    headers = {
                        **GARMIN_API_HEADERS,
                        "Referer": self.data.session_url or "",
                        "Livetrack-Csrf-Token": self._csrf_token or "",
                    }
                    async with session.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 403 and attempt == 0:
                            self._cookie_jar.clear()
                            self._csrf_token = None
                            await self._async_bootstrap_garmin_session(session)
                            continue

                        if resp.status == 404:
                            _LOGGER.debug(
                                "No trackpoints yet for session %s", self.data.session_id
                            )
                            return self.data

                        if resp.status != 200:
                            raise UpdateFailed(f"Garmin API returned {resp.status}")

                        body = await resp.json()
                        trackpoints = body.get("trackPoints") or []
                        if not trackpoints:
                            return self.data

                        latest = trackpoints[-1]
                        position = latest.get("position") or {}
                        self.data.lat = position.get("lat")
                        self.data.lon = position.get("lon")
                        self.data.speed = latest.get(
                            "speedMetersPerSec", latest.get("speed")
                        )
                        self.data.altitude = latest.get("altitude")
                        self.data.heart_rate = latest.get(
                            "heartRateBeatsPerMin", latest.get("heartRate")
                        )
                        if latest.get("dateTime"):
                            self.data.last_track_point_time = _parse_garmin_time(
                                latest["dateTime"]
                            )
                        self.data.last_updated = datetime.now(tz=timezone.utc)
                        return self.data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Garmin API: {err}") from err

        return self.data

    async def _async_bootstrap_garmin_session(
        self, session: aiohttp.ClientSession
    ) -> None:
        if not self.data.session_url:
            raise UpdateFailed("LiveTrack session URL is missing")

        async with session.get(
            self.data.session_url,
            headers=GARMIN_PAGE_HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"Garmin session page returned {resp.status}")

            html = await resp.text()
            self._csrf_token = _extract_csrf_token(html)
            if not self._csrf_token:
                raise UpdateFailed("Garmin session page did not include a CSRF token")

    async def _async_fetch_garmin_session(
        self, session: aiohttp.ClientSession
    ) -> dict:
        url = GARMIN_SESSION_URL.format(session_id=self.data.session_id)
        headers = {
            **GARMIN_API_HEADERS,
            "Referer": self.data.session_url or "",
            "Livetrack-Csrf-Token": self._csrf_token or "",
        }
        params = {"token": self.data.token}

        async with session.get(
            url,
            headers=headers,
            params=params,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 403:
                self._cookie_jar.clear()
                self._csrf_token = None
                await self._async_bootstrap_garmin_session(session)
                headers["Livetrack-Csrf-Token"] = self._csrf_token or ""
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as retry_resp:
                    if retry_resp.status != 200:
                        raise UpdateFailed(
                            f"Garmin session API returned {retry_resp.status}"
                        )
                    return await retry_resp.json()

            if resp.status != 200:
                raise UpdateFailed(f"Garmin session API returned {resp.status}")
            return await resp.json()


def _extract_token_from_url(session_url: str) -> str | None:
    match = re.search(r"/token/([A-Za-z0-9]+)", session_url)
    return match.group(1) if match else None


def _extract_csrf_token(html: str) -> str | None:
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    return match.group(1) if match else None


def _get_session_end_time(session_data: dict) -> datetime | None:
    end = session_data.get("end")
    if not end:
        return None
    return _parse_garmin_time(end)


def _parse_garmin_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_garmin_time(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )
