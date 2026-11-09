"""The DMI Weather integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import REFRESH_INTERVAL
from .coordinator import DMIConfigEntry, DMICoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: DMIConfigEntry) -> bool:
    """Set up DMI Weather from a config entry."""
    coordinator = DMICoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _refresh_entities(_now: datetime) -> None:
        """Re-render entities so interpolated "now" values move between API calls.

        Uses the forecast already in memory - this does not contact DMI.
        """
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_interval(hass, _refresh_entities, REFRESH_INTERVAL))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DMIConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
