"""Config flow for Samsung TV Art."""

from __future__ import annotations

from typing import Any

import aiohttp
from samsungtvws import exceptions
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .coordinator import (
    async_validate_connection,
    device_identifier,
    device_name,
)


class CannotConnect(Exception):
    """Raised when the TV cannot be reached."""


class SamsungTvArtConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Samsung TV Art."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            timeout = int(user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))

            try:
                info = await _async_validate_input(self.hass, host, port, timeout)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                unique_id = device_identifier(info, host)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host, CONF_PORT: port}
                )

                data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_NAME: str(user_input.get(CONF_NAME) or DEFAULT_NAME),
                    CONF_TIMEOUT: timeout,
                }
                token = str(user_input.get(CONF_TOKEN) or "").strip()
                if token:
                    data[CONF_TOKEN] = token

                return self.async_create_entry(
                    title=device_name(info, host),
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )


async def _async_validate_input(
    hass: HomeAssistant,
    host: str,
    port: int,
    timeout: int,
) -> dict[str, Any]:
    """Validate user input against the TV REST API."""
    try:
        return await async_validate_connection(hass, host, port, timeout)
    except (
        aiohttp.ClientError,
        exceptions.HttpApiError,
        TimeoutError,
        OSError,
    ) as err:
        raise CannotConnect from err


def _user_schema(user_input: dict[str, Any] | None) -> vol.Schema:
    """Return the config flow form schema."""
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Optional(
                CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Optional(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Optional(CONF_TOKEN, default=defaults.get(CONF_TOKEN, "")): str,
        }
    )
