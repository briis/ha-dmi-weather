"""The DMI Weather integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_DMI_URL, REFRESH_INTERVAL
from .coordinator import DMIConfigEntry, DMICoordinator
from .dmi_link import suggest_dmi_url

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: DMIConfigEntry) -> bool:
    """Set up DMI Weather from a config entry."""
    coordinator = DMICoordinator(hass, entry)
    # "Visit" link: the user's own dmi.dk link, else the nearest place (file read -> executor).
    coordinator.dmi_url = entry.options.get(CONF_DMI_URL) or await hass.async_add_executor_job(
        suggest_dmi_url, entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE]
    )
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
