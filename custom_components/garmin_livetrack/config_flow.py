from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NOTIFY_SERVICE,
    CONF_POLL_INTERVAL,
    CONF_TRACKER_NAME,
    CONF_ZONE_ENTITY,
    CONF_ZONE_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TRACKER_NAME,
    DEFAULT_ZONE_POLL_INTERVAL,
    DOMAIN,
)

CONF_WEBHOOK_ID = "webhook_id"


class GarminLiveTrackConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._webhook_id: str = secrets.token_hex(16)
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._user_input = user_input
            return await self.async_step_webhook()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_TRACKER_NAME, default=DEFAULT_TRACKER_NAME): str,
                    vol.Optional(CONF_NOTIFY_SERVICE, default=""): str,
                }
            ),
        )

    async def async_step_webhook(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=self._user_input.get(CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME),
                data={
                    CONF_WEBHOOK_ID: self._webhook_id,
                    CONF_TRACKER_NAME: self._user_input.get(CONF_TRACKER_NAME, DEFAULT_TRACKER_NAME),
                    CONF_NOTIFY_SERVICE: self._user_input.get(CONF_NOTIFY_SERVICE, ""),
                },
            )

        webhook_url = webhook.async_generate_url(self.hass, self._webhook_id)
        return self.async_show_form(
            step_id="webhook",
            data_schema=vol.Schema({}),
            description_placeholders={"webhook_url": webhook_url},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GarminLiveTrackOptionsFlow()


class GarminLiveTrackOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NOTIFY_SERVICE,
                        default=options.get(
                            CONF_NOTIFY_SERVICE,
                            self.config_entry.data.get(CONF_NOTIFY_SERVICE, ""),
                        ),
                    ): str,
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                    vol.Optional(
                        CONF_ZONE_ENTITY,
                        default=options.get(CONF_ZONE_ENTITY, ""),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="zone")
                    ),
                    vol.Required(
                        CONF_ZONE_POLL_INTERVAL,
                        default=options.get(CONF_ZONE_POLL_INTERVAL, DEFAULT_ZONE_POLL_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=60)),
                }
            ),
        )
