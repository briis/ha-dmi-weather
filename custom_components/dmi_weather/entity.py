"""Base entity for DMI Weather."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pydmi import ATTRIBUTION

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import DMICoordinator


class DMIEntity(CoordinatorEntity[DMICoordinator]):
    """Common device info and attribution (required by DMI's CC BY 4.0 licence)."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: DMICoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.dmi_url,
        )
