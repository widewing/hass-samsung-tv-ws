"""Select platform for Samsung TV WS."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from samsungtvws import exceptions
import websocket

from homeassistant.components.select import SelectEntity
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


@dataclass(frozen=True)
class AppOption:
    """A selectable TV app."""

    label: str
    app_id: str
    app_type: str


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
    entities: list[SelectEntity] = [SamsungTvWsAppSelect(coordinator)]
    if coordinator.art_supported:
        entities.append(SamsungTvWsArtworkSelect(coordinator))

    async_add_entities(entities, True)


class SamsungTvWsAppSelect(SamsungTvWsEntity, SelectEntity):
    """Select entity that launches installed TV apps."""

    _attr_icon = "mdi:apps"
    _attr_translation_key = "app_launcher"

    def __init__(self, coordinator: SamsungTvWsCoordinator) -> None:
        """Initialize the app launcher select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_app_launcher"
        self._attr_current_option: str | None = None
        self._attr_options: list[str] = []
        self._apps: dict[str, AppOption] = {}
        self._apps_available = True

    @property
    def available(self) -> bool:
        """Return whether app options are available."""
        return super().available and self._apps_available

    @property
    def should_poll(self) -> bool:
        """Refresh installed app options by polling."""
        return True

    async def async_update(self) -> None:
        """Refresh installed app options."""
        try:
            apps = await self.coordinator.async_tv_call("app_list")
        except (exceptions.ResponseError, *_CONNECTION_ERRORS):
            self._apps_available = False
            return

        if not apps:
            self._apps_available = False
            self._attr_options = []
            self._apps = {}
            return

        options = _build_app_options(apps)
        self._apps = {option.label: option for option in options}
        self._attr_options = [option.label for option in options]
        if self._attr_current_option not in self._apps:
            self._attr_current_option = None
        self._apps_available = True

    async def async_select_option(self, option: str) -> None:
        """Launch the selected app."""
        app = self._apps.get(option)
        if app is None:
            raise HomeAssistantError(f"Unknown Samsung TV app option: {option}")

        try:
            await self.coordinator.async_tv_call(
                "run_app", app.app_id, app_type=app.app_type
            )
        except (exceptions.ResponseError, *_CONNECTION_ERRORS) as err:
            self._apps_available = not isinstance(err, _CONNECTION_ERRORS)
            raise HomeAssistantError(f"Failed to launch Samsung TV app: {err}") from err

        self._attr_current_option = option
        self._apps_available = True
        self.async_write_ha_state()


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
        except exceptions.ResponseError:
            self._artworks_available = False
            self._attr_options = []
            self._artworks = {}
            return
        except _CONNECTION_ERRORS:
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
        except (exceptions.ResponseError, *_CONNECTION_ERRORS):
            return self._attr_current_option

        content_id = _string_value(current, "content_id", "contentId", "id")
        if not content_id:
            return self._attr_current_option

        for label, artwork in self._artworks.items():
            if artwork.content_id == content_id:
                return label

        return self._attr_current_option


def _build_app_options(apps: list[dict[str, Any]]) -> list[AppOption]:
    """Build unique select options for installed apps."""
    app_rows: list[tuple[str, str, str]] = []
    for app in apps:
        app_id = _string_value(app, "appId", "app_id", "id")
        if not app_id:
            continue

        name = _string_value(app, "name", "title") or app_id
        app_rows.append((name, app_id, _app_type(app.get("app_type"))))

    return [
        AppOption(label, app_id, app_type)
        for label, app_id, app_type in _unique_labels(app_rows)
    ]


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


def _app_type(value: Any) -> str:
    """Normalize Samsung app type values for launch_app."""
    if isinstance(value, str) and value in {"DEEP_LINK", "NATIVE_LAUNCH"}:
        return value
    return "DEEP_LINK" if value == 2 or str(value) == "2" else "NATIVE_LAUNCH"
