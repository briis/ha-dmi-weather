"""Data update coordinator for DMI Weather."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pydmi import (
    DMIError,
    DMIInvalidLocationError,
    DMIRateLimitError,
    Forecast,
    Lightning,
    Observations,
)
from pydmi.client_async import DMIForecastAsync, DMILightningAsync, DMIObservationsAsync

from .const import (
    DOMAIN,
    LIGHTNING_UPDATE_INTERVAL,
    OBS_UPDATE_INTERVAL,
    PROBABILITY_RETRY_INTERVAL,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type DMIConfigEntry = ConfigEntry[DMICoordinator]


class DMICoordinator(DataUpdateCoordinator[Forecast]):
    """Fetches the DMI forecast for one location."""

    config_entry: DMIConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DMIConfigEntry) -> None:
        self.dmi_url: str = "https://www.dmi.dk"
        self.observations: DMIObservationCoordinator | None = None
        self.lightning: DMILightningCoordinator | None = None
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
            forecast = await self.api.get_forecast()
        except DMIRateLimitError as err:
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            raise UpdateFailed(f"Error fetching DMI forecast: {err}") from err
        # Retry soon while the chance of precipitation is missing (only the
        # ensemble is re-requested), otherwise back to the normal interval.
        self.update_interval = (
            PROBABILITY_RETRY_INTERVAL if self.api.probability_pending else UPDATE_INTERVAL
        )
        return forecast


class DMIObservationCoordinator(DataUpdateCoordinator[Observations | None]):
    """Fetches observations from the nearest DMI stations every 10 minutes.

    Optional: if it fails, the weather entity falls back to the forecast.
    """

    config_entry: DMIConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DMIConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_observations",
            update_interval=OBS_UPDATE_INTERVAL,
        )
        self.api = DMIObservationsAsync(
            entry.data[CONF_LATITUDE],
            entry.data[CONF_LONGITUDE],
            session=async_get_clientsession(hass),
            update_interval=OBS_UPDATE_INTERVAL,
        )
        self.no_stations = False

    async def _async_update_data(self) -> Observations | None:
        try:
            return await self.api.get_observations()
        except DMIInvalidLocationError as err:
            # No station nearby: stop polling, the forecast is used instead.
            _LOGGER.info("No DMI observations for this location: %s", err)
            self.no_stations = True
            self.update_interval = None
            return None
        except DMIRateLimitError as err:
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            raise UpdateFailed(f"Error fetching DMI observations: {err}") from err

    def value(self, name: str) -> float | None:
        """Observed value, or None if unavailable or stale."""
        if not self.last_update_success or self.data is None:
            return None
        return self.data.get(name)


class DMILightningCoordinator(DataUpdateCoordinator[Lightning]):
    """Lightning strikes within a radius, every 5 minutes. Optional."""

    config_entry: DMIConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DMIConfigEntry, radius_km: float) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_lightning",
            update_interval=LIGHTNING_UPDATE_INTERVAL,
        )
        self.api = DMILightningAsync(
            entry.data[CONF_LATITUDE],
            entry.data[CONF_LONGITUDE],
            session=async_get_clientsession(hass),
            radius_km=radius_km,
            update_interval=LIGHTNING_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> Lightning:
        try:
            return await self.api.get_lightning()
        except DMIRateLimitError as err:
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            raise UpdateFailed(f"Error fetching DMI lightning data: {err}") from err
