"""Samsung TV Art integration."""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PLATFORMS,
    STORAGE_DIR,
)
from .coordinator import SamsungTvArtConfig, SamsungTvArtCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Samsung TV Art."""
    hass.data.setdefault(DOMAIN, {})
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Samsung TV Art from a config entry."""
    token_file = _token_file_path(hass, entry)
    await hass.async_add_executor_job(
        _prepare_token_file,
        token_file,
        entry.data.get(CONF_TOKEN),
    )

    coordinator = SamsungTvArtCoordinator(
        hass,
        entry,
        SamsungTvArtConfig(
            host=entry.data[CONF_HOST],
            port=entry.data.get(CONF_PORT, DEFAULT_PORT),
            name=entry.data.get(CONF_NAME, DEFAULT_NAME),
            timeout=entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            token_file=token_file,
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.art_supported:
        _LOGGER.warning(
            "Samsung TV REST data does not report Art Mode support; Art Mode "
            "entities will not be created. FrameTVSupport=%r, isSupport=%r",
            coordinator.device.get("FrameTVSupport"),
            (coordinator.data or {}).get("isSupport"),
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Samsung TV Art config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove persisted token data for a deleted config entry."""
    await hass.async_add_executor_job(_remove_token_file, _token_file_path(hass, entry))


def _token_file_path(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Return this config entry's local token file path."""
    return hass.config.path(STORAGE_DIR, f"{entry.entry_id}.token")


def _prepare_token_file(token_file: str, token: str | None) -> None:
    """Create the token directory and seed an optional user-provided token."""
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    if token and not os.path.exists(token_file):
        with open(token_file, "w", encoding="utf-8") as file:
            file.write(str(token))


def _remove_token_file(token_file: str) -> None:
    """Remove the stored token file if it exists."""
    try:
        os.remove(token_file)
    except FileNotFoundError:
        pass
