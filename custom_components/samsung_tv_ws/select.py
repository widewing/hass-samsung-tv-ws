"""Select platform for Samsung TV WS."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
from typing import Any

from samsungtvws import exceptions

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import SamsungTvWsCoordinator
from .entity import SamsungTvWsEntity

SCAN_INTERVAL = UPDATE_INTERVAL
_LOGGER = logging.getLogger(__name__)

_CONNECTION_ERRORS = (
    exceptions.ConnectionFailure,
    exceptions.HttpApiError,
    OSError,
    TimeoutError,
)


@dataclass(frozen=True)
class ArtworkOption:
    """A selectable artwork."""

    label: str
    content_id: str
    category: str | None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung TV WS selects."""
    coordinator: SamsungTvWsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []
    if coordinator.art_supported:
        entities.append(SamsungTvWsArtworkSelect(coordinator))

    async_add_entities(entities, True)


class SamsungTvWsArtworkSelect(SamsungTvWsEntity, SelectEntity):
    """Select entity that displays available Frame TV artwork."""

    _attr_icon = "mdi:image-multiple"
    _attr_translation_key = "artwork"

    def __init__(self, coordinator: SamsungTvWsCoordinator) -> None:
        """Initialize the artwork select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_artwork"
        self._attr_current_option: str | None = None
        self._attr_options: list[str] = []
        self._artworks: dict[str, ArtworkOption] = {}
        self._artworks_available = True

    @property
    def available(self) -> bool:
        """Return whether artwork options are available."""
        return super().available and self._artworks_available

    @property
    def should_poll(self) -> bool:
        """Refresh artwork options by polling."""
        return True

    async def async_update(self) -> None:
        """Refresh artwork options and current artwork state."""
        try:
            artworks = await self.coordinator.async_art_call("available")
        except exceptions.ResponseError as err:
            if self._artworks_available:
                _LOGGER.warning("Unable to fetch Samsung artwork list: %s", err)
            self._artworks_available = False
            self._attr_options = []
            self._artworks = {}
            return
        except _CONNECTION_ERRORS as err:
            if self._artworks_available:
                _LOGGER.warning("Unable to fetch Samsung artwork list: %s", err)
            self._artworks_available = False
            return

        options = _build_artwork_options(artworks or [])
        self._artworks = {option.label: option for option in options}
        self._attr_options = [option.label for option in options]
        self._attr_current_option = await self._async_current_artwork_label()
        self._artworks_available = True

    async def async_select_option(self, option: str) -> None:
        """Display the selected artwork."""
        artwork = self._artworks.get(option)
        if artwork is None:
            raise HomeAssistantError(f"Unknown Samsung artwork option: {option}")

        try:
            await self.coordinator.async_art_call(
                "select_image",
                artwork.content_id,
                category=artwork.category,
                show=True,
            )
        except (exceptions.ResponseError, *_CONNECTION_ERRORS) as err:
            self._artworks_available = not isinstance(err, _CONNECTION_ERRORS)
            raise HomeAssistantError(
                f"Failed to select Samsung artwork: {err}"
            ) from err

        self._attr_current_option = option
        self._artworks_available = True
        self.async_write_ha_state()

    async def _async_current_artwork_label(self) -> str | None:
        """Return the current artwork option label when available."""
        if not self._artworks:
            return None

        try:
            current = await self.coordinator.async_art_call("get_current")
        except (exceptions.ResponseError, *_CONNECTION_ERRORS) as err:
            _LOGGER.debug(
                "Unable to fetch current Samsung artwork: %s", err, exc_info=True
            )
            return self._attr_current_option

        content_id = _string_value(current, "content_id", "contentId", "id")
        if not content_id:
            return self._attr_current_option

        for label, artwork in self._artworks.items():
            if artwork.content_id == content_id:
                return label

        return self._attr_current_option


def _build_artwork_options(artworks: list[dict[str, Any]]) -> list[ArtworkOption]:
    """Build unique select options for artwork content."""
    artwork_rows: list[tuple[str, str, str | None]] = []
    for artwork in artworks:
        content_id = _string_value(artwork, "content_id", "contentId", "id")
        if not content_id:
            continue

        name = (
            _string_value(artwork, "title", "name", "file_name", "fileName")
            or content_id
        )
        category = _string_value(artwork, "category_id", "categoryId", "category")
        artwork_rows.append((name, content_id, category))

    return [
        ArtworkOption(label, content_id, category)
        for label, content_id, category in _unique_labels(artwork_rows)
    ]


def _unique_labels(
    rows: list[tuple[str, str, str | None]]
) -> list[tuple[str, str, str | None]]:
    """Return rows with labels made unique by appending identifiers."""
    name_counts = Counter(row[0] for row in rows)
    used: set[str] = set()
    result: list[tuple[str, str, str | None]] = []

    for name, identifier, metadata in rows:
        label = name
        if name_counts[name] > 1:
            label = f"{name} ({identifier})"

        dedupe = label
        suffix = 2
        while dedupe in used:
            dedupe = f"{label} #{suffix}"
            suffix += 1

        used.add(dedupe)
        result.append((dedupe, identifier, metadata))

    return result


def _string_value(data: dict[str, Any] | Any, *keys: str) -> str | None:
    """Return the first non-empty string value from a mapping."""
    if not isinstance(data, dict):
        return None

    for key in keys:
        value = data.get(key)
        if value is not None and str(value):
            return str(value)

    return None
