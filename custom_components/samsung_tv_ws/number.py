"""Number platform for Samsung TV WS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from samsungtvws import exceptions
import websocket

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SamsungTvWsCoordinator
from .entity import SamsungTvWsEntity

_CONNECTION_ERRORS = (
    exceptions.ConnectionFailure,
    exceptions.HttpApiError,
    OSError,
    TimeoutError,
    websocket.WebSocketException,
)


@dataclass(frozen=True, kw_only=True)
class SamsungTvWsArtNumberDescription(NumberEntityDescription):
    """Description for an Art Mode number entity."""

    get_method: str
    set_method: str
    value_converter: Callable[[float], int | float]


ART_NUMBER_DESCRIPTIONS: tuple[SamsungTvWsArtNumberDescription, ...] = (
    SamsungTvWsArtNumberDescription(
        key="art_brightness",
        translation_key="art_brightness",
        icon="mdi:brightness-6",
        get_method="get_brightness",
        set_method="set_brightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_converter=round,
    ),
    SamsungTvWsArtNumberDescription(
        key="art_color_temperature",
        translation_key="art_color_temperature",
        icon="mdi:thermometer-lines",
        get_method="get_color_temperature",
        set_method="set_color_temperature",
        native_min_value=-5,
        native_max_value=5,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_converter=round,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung TV WS numbers."""
    coordinator: SamsungTvWsCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.art_supported:
        return

    async_add_entities(
        [
            SamsungTvWsArtNumber(coordinator, description)
            for description in ART_NUMBER_DESCRIPTIONS
        ],
        True,
    )


class SamsungTvWsArtNumber(SamsungTvWsEntity, NumberEntity):
    """Number entity for an Art Mode setting."""

    def __init__(
        self,
        coordinator: SamsungTvWsCoordinator,
        description: SamsungTvWsArtNumberDescription,
    ) -> None:
        """Initialize the Art Mode number."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        self._attr_native_value: float | None = None
        self._setting_available = True

    @property
    def available(self) -> bool:
        """Return whether the number can be controlled."""
        return super().available and self._setting_available

    @property
    def should_poll(self) -> bool:
        """Poll Art websocket state separately from REST device info."""
        return True

    async def async_update(self) -> None:
        """Fetch the current Art Mode setting value."""
        try:
            value = await self.coordinator.async_art_call(
                self.entity_description.get_method
            )
        except exceptions.ResponseError:
            self._attr_native_value = None
            self._setting_available = True
            return
        except _CONNECTION_ERRORS:
            self._setting_available = False
            return

        self._attr_native_value = _coerce_float(value)
        self._setting_available = True

    async def async_set_native_value(self, value: float) -> None:
        """Set the Art Mode number value."""
        send_value = self.entity_description.value_converter(value)
        try:
            await self.coordinator.async_art_call(
                self.entity_description.set_method, send_value
            )
        except (exceptions.ResponseError, *_CONNECTION_ERRORS) as err:
            self._setting_available = not isinstance(err, _CONNECTION_ERRORS)
            raise HomeAssistantError(
                f"Failed to set Samsung Art setting: {err}"
            ) from err

        self._attr_native_value = float(send_value)
        self._setting_available = True
        self.async_write_ha_state()


def _coerce_float(value: Any) -> float | None:
    """Return a float value from a Samsung Art API payload."""
    if isinstance(value, dict):
        value = value.get("value")

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
