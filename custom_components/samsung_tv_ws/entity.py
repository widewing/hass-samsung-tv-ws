"""Base entities for Samsung TV WS."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungTvWsCoordinator


class SamsungTvWsEntity(CoordinatorEntity[SamsungTvWsCoordinator]):
    """Base Samsung TV WS entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SamsungTvWsCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device registry metadata."""
        device = self.coordinator.device
        info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self.coordinator.unique_id)},
            "manufacturer": "Samsung",
            "name": device.get("name") or self.coordinator.config_entry.title,
        }

        model = device.get("modelName") or device.get("model")
        if model:
            info["model"] = str(model)

        firmware = device.get("firmwareVersion")
        if firmware and str(firmware).lower() != "unknown":
            info["sw_version"] = str(firmware)

        configuration_url = (self.coordinator.data or {}).get("uri")
        if configuration_url:
            info["configuration_url"] = str(configuration_url)

        mac = device.get("wifiMac")
        if mac and str(mac).lower() != "none":
            info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(str(mac)))}

        return info
