"""Switch platform for Samsung TV WS."""

from __future__ import annotations

import logging
from typing import Any

from samsungtvws import exceptions

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import SamsungTvWsCoordinator
from .entity import SamsungTvWsEntity

SCAN_INTERVAL = UPDATE_INTERVAL
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung TV WS switches."""
    coordinator: SamsungTvWsCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.art_supported:
        async_add_entities([SamsungTvWsArtModeSwitch(coordinator)])


class SamsungTvWsArtModeSwitch(SamsungTvWsEntity, SwitchEntity):
    """Switch that controls Frame TV Art Mode."""

    _attr_icon = "mdi:image-frame"
    _attr_translation_key = "art_mode"

    def __init__(self, coordinator: SamsungTvWsCoordinator) -> None:
        """Initialize the Art Mode switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_art_mode"
        self._attr_is_on: bool | None = None
        self._art_available = True

    @property
    def available(self) -> bool:
        """Return whether this Art Mode switch is available."""
        return super().available and self._art_available

    @property
    def should_poll(self) -> bool:
        """Poll the Art websocket because it is separate from REST device info."""
        return True

    async def async_update(self) -> None:
        """Fetch the current Art Mode state."""
        try:
            mode = await self.coordinator.async_art_call("get_artmode")
        except (
            exceptions.ConnectionFailure,
            exceptions.HttpApiError,
            exceptions.ResponseError,
            exceptions.UnauthorizedError,
            OSError,
            TimeoutError,
        ) as err:
            if self._art_available:
                _LOGGER.warning(
                    "Unable to fetch Samsung Art Mode state (%s): %s",
                    type(err).__name__,
                    err,
                    exc_info=True,
                )
            self._art_available = False
            return

        self._art_available = True
        self._attr_is_on = _truthy(mode)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn Art Mode on."""
        await self.coordinator.async_art_call("set_artmode", True)
        self._attr_is_on = True
        self._art_available = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn Art Mode off."""
        await self.coordinator.async_art_call("set_artmode", False)
        self._attr_is_on = False
        self._art_available = True
        self.async_write_ha_state()


def _truthy(value: Any) -> bool:
    """Normalize Samsung Art Mode booleans."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "on", "true", "yes"}
    return bool(value)
