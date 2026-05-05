"""Coordinator and API helpers for Samsung TV WS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import json
import logging
from typing import Any, TypeVar

import aiohttp
from samsungtvws import SamsungTVWS, exceptions
from samsungtvws.async_rest import SamsungTVAsyncRest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_TIMEOUT, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T")


@dataclass(frozen=True)
class SamsungTvWsConfig:
    """Runtime connection settings."""

    host: str
    port: int
    name: str
    timeout: int
    token_file: str


class SamsungTvWsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Samsung TV device information and run commands."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        config: SamsungTvWsConfig,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.config_entry = config_entry
        self.config = config
        self.session = async_get_clientsession(hass)

    @property
    def unique_id(self) -> str:
        """Return the stable unique id for this TV."""
        return self.config_entry.unique_id or device_identifier(
            self.data, self.config.host
        )

    @property
    def device(self) -> dict[str, Any]:
        """Return the nested device payload from the REST response."""
        return device_payload(self.data)

    @property
    def art_supported(self) -> bool:
        """Return whether the TV reports Frame TV / Art Mode support."""
        return art_supported(self.data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch fresh device info."""
        try:
            return await self.async_get_device_info()
        except (
            aiohttp.ClientError,
            exceptions.HttpApiError,
            TimeoutError,
            OSError,
        ) as err:
            msg = f"Unable to fetch Samsung TV device info: {err}"
            raise UpdateFailed(msg) from err

    async def async_get_device_info(self) -> dict[str, Any]:
        """Fetch device information from the REST API."""
        rest_api = SamsungTVAsyncRest(
            host=self.config.host,
            port=self.config.port,
            timeout=self.config.timeout,
            session=self.session,
        )
        return await rest_api.rest_device_info()

    async def async_tv_call(
        self, method: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Run a SamsungTVWS method in the executor."""
        return await self._async_executor_call(self._tv_call, method, *args, **kwargs)

    async def async_art_call(
        self, method: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Run a SamsungTVArt method in the executor."""
        return await self._async_executor_call(self._art_call, method, *args, **kwargs)

    async def _async_executor_call(
        self,
        func: Callable[..., _T],
        method: str,
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        """Run a blocking library call in Home Assistant's executor."""
        job = partial(func, method, *args, **kwargs)
        return await self.hass.async_add_executor_job(job)

    def _make_tv(self) -> SamsungTVWS:
        """Create a SamsungTVWS client for one blocking operation."""
        return SamsungTVWS(
            self.config.host,
            token_file=self.config.token_file,
            port=self.config.port,
            timeout=self.config.timeout,
            name=self.config.name,
        )

    def _tv_call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a normal TV method."""
        tv = self._make_tv()
        try:
            return getattr(tv, method)(*args, **kwargs)
        finally:
            tv.close()

    def _art_call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an Art Mode method."""
        tv = self._make_tv()
        art = tv.art()
        try:
            return getattr(art, method)(*args, **kwargs)
        finally:
            art.close()
            tv.close()


async def async_validate_connection(
    hass: HomeAssistant,
    host: str,
    port: int,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Validate that the TV REST API can be reached."""
    rest_api = SamsungTVAsyncRest(
        host=host,
        port=port,
        timeout=timeout,
        session=async_get_clientsession(hass),
    )
    return await rest_api.rest_device_info()


def device_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return the nested Samsung REST device payload."""
    if not data:
        return {}
    device = data.get("device")
    return device if isinstance(device, dict) else {}


def device_name(data: dict[str, Any] | None, fallback: str) -> str:
    """Return a friendly TV name."""
    device = device_payload(data)
    name = device.get("name") or (data or {}).get("name")
    return str(name or fallback)


def device_identifier(data: dict[str, Any] | None, fallback: str) -> str:
    """Return the best stable identifier available from the TV."""
    device = device_payload(data)
    for key in ("duid", "id", "udn", "wifiMac"):
        value = device.get(key)
        if value and str(value).lower() != "none":
            return str(value)

    if data:
        value = data.get("id")
        if value:
            return str(value)

    return fallback


def art_supported(data: dict[str, Any] | None) -> bool:
    """Return true when the REST payload reports Frame TV support."""
    device = device_payload(data)
    support = device.get("FrameTVSupport")
    if support is not None:
        return _truthy(support)

    raw_support = (data or {}).get("isSupport")
    if isinstance(raw_support, str):
        try:
            parsed = json.loads(raw_support)
        except json.JSONDecodeError:
            parsed = {}
        support = parsed.get("FrameTVSupport")

    return _truthy(support)


def _truthy(value: Any) -> bool:
    """Normalize Samsung string booleans."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "on", "true", "yes"}
    return bool(value)
