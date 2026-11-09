"""Data update coordinator for DMI Weather."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
    FORECAST_MAX_STALE,
    FORECAST_RETRY_INTERVAL,
    LIGHTNING_UPDATE_INTERVAL,
    OBS_UPDATE_INTERVAL,
    PROBABILITY_RETRY_INTERVAL,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type DMIConfigEntry = ConfigEntry[DMICoordinator]


@dataclass
class DMIClients:
    """pydmi clients for one config entry, kept across reloads.

    Changing an option reloads the entry. Reusing the clients keeps their caches,
    so a reload does not re-request the forecast, ensemble and observations from
    DMI in one burst - only what actually changed (e.g. a new lightning radius).
    """

    forecast: DMIForecastAsync | None = None
    observations: DMIObservationsAsync | None = None
    lightning: DMILightningAsync | None = None


def get_clients(hass: HomeAssistant, entry: ConfigEntry) -> DMIClients:
    store: dict[str, DMIClients] = hass.data.setdefault(DOMAIN, {})
    return store.setdefault(entry.entry_id, DMIClients())


def forget_clients(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)


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
        clients = get_clients(hass, entry)
        if clients.forecast is None:
            clients.forecast = DMIForecastAsync(
                entry.data[CONF_LATITUDE],
                entry.data[CONF_LONGITUDE],
                session=async_get_clientsession(hass),
                update_interval=UPDATE_INTERVAL,
            )
        self.api = clients.forecast

    def _stale_forecast(self, err: DMIError) -> Forecast | None:
        """The last good forecast, if recent enough to keep showing."""
        cached = self.api.cached
        if cached is None or dt_util.utcnow() - cached.fetched_at > FORECAST_MAX_STALE:
            return None
        if not cached.hourly():
            return None
        _LOGGER.warning(
            "DMI forecast update failed, keeping the forecast from %s and retrying in %s: %s",
            dt_util.as_local(cached.fetched_at).strftime("%H:%M"),
            FORECAST_RETRY_INTERVAL,
            err,
        )
        self.update_interval = FORECAST_RETRY_INTERVAL
        return cached

    async def _async_update_data(self) -> Forecast:
        try:
            forecast = await self.api.get_forecast()
        except DMIRateLimitError as err:
            if (stale := self._stale_forecast(err)) is not None:
                return stale
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            # One failed call must not make everything unavailable.
            if (stale := self._stale_forecast(err)) is not None:
                return stale
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
        clients = get_clients(hass, entry)
        if clients.observations is None:
            clients.observations = DMIObservationsAsync(
                entry.data[CONF_LATITUDE],
                entry.data[CONF_LONGITUDE],
                session=async_get_clientsession(hass),
                update_interval=OBS_UPDATE_INTERVAL,
            )
        self.api = clients.observations
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
        clients = get_clients(hass, entry)
        if clients.lightning is None or clients.lightning.radius_km != radius_km:
            clients.lightning = DMILightningAsync(
                entry.data[CONF_LATITUDE],
                entry.data[CONF_LONGITUDE],
                session=async_get_clientsession(hass),
                radius_km=radius_km,
                update_interval=LIGHTNING_UPDATE_INTERVAL,
            )
        self.api = clients.lightning

    async def _async_update_data(self) -> Lightning:
        try:
            return await self.api.get_lightning()
        except DMIRateLimitError as err:
            raise UpdateFailed(
                f"DMI rate limit reached: {err}", retry_after=err.retry_after
            ) from err
        except DMIError as err:
            raise UpdateFailed(f"Error fetching DMI lightning data: {err}") from err
