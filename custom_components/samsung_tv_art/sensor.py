"""Sensor platform for Samsung TV Art."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SamsungTvArtCoordinator
from .entity import SamsungTvArtEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Samsung TV Art sensors."""
    coordinator: SamsungTvArtCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SamsungTvArtDeviceInfoSensor(coordinator)])


class SamsungTvArtDeviceInfoSensor(SamsungTvArtEntity, SensorEntity):
    """Diagnostic sensor exposing Samsung TV device information."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:television"
    _attr_translation_key = "device_info"

    def __init__(self, coordinator: SamsungTvArtCoordinator) -> None:
        """Initialize the device info sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id}_device_info"

    @property
    def native_value(self) -> str:
        """Return the current TV power state when available."""
        device = self.coordinator.device
        return str(device.get("PowerState") or "online")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the raw REST payload as diagnostic attributes."""
        data = self.coordinator.data or {}
        device = self.coordinator.device
        return {
            "art_supported": self.coordinator.art_supported,
            "device": device,
            "remote": data.get("remote"),
            "type": data.get("type"),
            "uri": data.get("uri"),
            "version": data.get("version"),
        }
