"""The DMI Weather integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DMI_URL,
    CONF_LIGHTNING,
    CONF_LIGHTNING_RADIUS,
    CONF_OBSERVATIONS,
    DEFAULT_LIGHTNING_RADIUS,
    REFRESH_INTERVAL,
)
from .coordinator import (
    DMIConfigEntry,
    DMICoordinator,
    DMILightningCoordinator,
    DMIObservationCoordinator,
)
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
    # Observations and lightning are optional (options, default on). A failure in
    # either must not stop the forecast, so no first_refresh here.
    if entry.options.get(CONF_OBSERVATIONS, True):
        coordinator.observations = DMIObservationCoordinator(hass, entry)
        await coordinator.observations.async_refresh()
    if entry.options.get(CONF_LIGHTNING, True):
        coordinator.lightning = DMILightningCoordinator(
            hass, entry, entry.options.get(CONF_LIGHTNING_RADIUS, DEFAULT_LIGHTNING_RADIUS)
        )
        await coordinator.lightning.async_refresh()
    _remove_disabled_entities(hass, entry, coordinator)
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


def _remove_disabled_entities(
    hass: HomeAssistant, entry: DMIConfigEntry, coordinator: DMICoordinator
) -> None:
    """Remove sensors of data sources that are turned off (or have no station)."""
    remove_prefixes: list[str] = []
    if coordinator.observations is None or coordinator.observations.no_stations:
        remove_prefixes.append(f"{entry.entry_id}_observed_")
    if coordinator.lightning is None:
        # Only the strike sensors - not the forecast's "lightning_probability".
        remove_prefixes.append(f"{entry.entry_id}_lightning_strike")
    if not remove_prefixes:
        return
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id.startswith(tuple(remove_prefixes)):
            registry.async_remove(entity.entity_id)
