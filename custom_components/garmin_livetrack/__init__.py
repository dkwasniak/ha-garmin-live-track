from __future__ import annotations

import logging

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import get_url

from .config_flow import CONF_WEBHOOK_ID
from .const import CONF_NOTIFY_SERVICE, CONF_POLL_INTERVAL, CONF_TRACKER_NAME, DEFAULT_POLL_INTERVAL, DOMAIN
from .coordinator import GarminLiveTrackCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["device_tracker", "sensor", "button"]

GarminConfigEntry = ConfigEntry[GarminLiveTrackCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GarminConfigEntry) -> bool:
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    coordinator = GarminLiveTrackCoordinator(hass, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    notify_service = entry.options.get(
        CONF_NOTIFY_SERVICE, entry.data.get(CONF_NOTIFY_SERVICE, "")
    )
    tracker_name = entry.data.get(CONF_TRACKER_NAME, "Garmin")

    webhook.async_register(
        hass,
        DOMAIN,
        "Garmin LiveTrack",
        webhook_id,
        _make_webhook_handler(hass, coordinator, notify_service, tracker_name),
    )

    entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GarminConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: GarminConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _make_webhook_handler(hass, coordinator, notify_service, tracker_name):
    async def _handle_webhook(hass, webhook_id, request):
        try:
            data = await request.json()
        except Exception:
            _LOGGER.warning("Garmin LiveTrack webhook: failed to parse JSON")
            return

        session_id = data.get("session_id")
        session_url = data.get("session_url")
        token = data.get("token")

        if not session_id or not session_url:
            _LOGGER.warning("Garmin LiveTrack webhook: missing session_id or session_url")
            return

        coordinator.start_session(session_id, session_url, token)
        await coordinator.async_refresh()

        if notify_service:
            service_parts = notify_service.split(".")
            domain = service_parts[0] if len(service_parts) == 2 else "notify"
            service = service_parts[1] if len(service_parts) == 2 else notify_service
            try:
                await hass.services.async_call(
                    domain,
                    service,
                    {
                        "title": f"Garmin LiveTrack — {tracker_name}",
                        "message": "Aktywność rozpoczęta. Kliknij aby śledzić.",
                        "data": {"url": session_url},
                    },
                )
            except Exception as err:
                _LOGGER.warning("Failed to send notification: %s", err)

    return _handle_webhook
