"""Data update coordinator for DMI Weather."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pydmi import DMIError, DMIRateLimitError, Forecast
from pydmi.client_async import DMIForecastAsync

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type DMIConfigEntry = ConfigEntry[DMICoordinator]


class DMICoordinator(DataUpdateCoordinator[Forecast]):
    """Fetches the DMI forecast for one location."""

    config_entry: DMIConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DMIConfigEntry) -> None:
        self.dmi_url: str = "https://www.dmi.dk"
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = DMIForecastAsync(
            entry.data[CONF_LATITUDE],
            entry.data[CONF_LONGITUDE],
            session=async_get_clientsession(hass),
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Forecast:
        try:
            return await self.api.get_forecast()
        except DMIRateLimitError as err:
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            raise UpdateFailed(f"Error fetching DMI forecast: {err}") from err
