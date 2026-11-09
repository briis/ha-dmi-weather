"""Weather entity for DMI Weather."""

from __future__ import annotations

from homeassistant.components.weather import (
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from pydmi import ForecastHour

from .coordinator import DMIConfigEntry, DMICoordinator
from .entity import DMIEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DMIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the DMI weather entity."""
    async_add_entities([DMIWeather(entry.runtime_data)])


class DMIWeather(DMIEntity, SingleCoordinatorWeatherEntity[DMICoordinator]):
    """Current conditions (from the current forecast hour) plus forecasts."""

    _attr_name = None  # use the device name
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_visibility_unit = UnitOfLength.METERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )

    def __init__(self, coordinator: DMICoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id

    @property
    def _now(self) -> ForecastHour | None:
        return self.coordinator.data.current()

    @property
    def condition(self) -> str | None:
        return self._now.condition if self._now else None

    @property
    def native_temperature(self) -> float | None:
        return self._now.temperature_c if self._now else None

    @property
    def native_dew_point(self) -> float | None:
        return self._now.dew_point_c if self._now else None

    @property
    def humidity(self) -> float | None:
        return self._now.humidity_pct if self._now else None

    @property
    def native_pressure(self) -> float | None:
        return self._now.pressure_hpa if self._now else None

    @property
    def native_wind_speed(self) -> float | None:
        return self._now.wind_speed_ms if self._now else None

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._now.wind_gust_ms if self._now else None

    @property
    def wind_bearing(self) -> float | None:
        return self._now.wind_bearing_deg if self._now else None

    @property
    def cloud_coverage(self) -> float | None:
        return self._now.cloud_cover_pct if self._now else None

    @property
    def native_visibility(self) -> float | None:
        return self._now.visibility_m if self._now else None

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        return [
            Forecast(
                datetime=h.datetime.isoformat(),
                condition=h.condition,
                native_temperature=h.temperature_c,
                native_dew_point=h.dew_point_c,
                humidity=h.humidity_pct,
                native_pressure=h.pressure_hpa,
                native_wind_speed=h.wind_speed_ms,
                native_wind_gust_speed=h.wind_gust_ms,
                wind_bearing=h.wind_bearing_deg,
                native_precipitation=h.precipitation_mm,
                cloud_coverage=h.cloud_cover_pct,
            )
            for h in self.coordinator.data.hourly()
        ]

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        tz = dt_util.get_default_time_zone()
        return [
            Forecast(
                datetime=dt_util.start_of_local_day(d.date).isoformat(),
                condition=d.condition,
                native_temperature=d.temperature_max_c,
                native_templow=d.temperature_min_c,
                native_precipitation=d.precipitation_mm,
                native_wind_speed=d.wind_speed_max_ms,
                native_wind_gust_speed=d.wind_gust_max_ms,
                wind_bearing=d.wind_bearing_deg,
                humidity=d.humidity_avg_pct,
                cloud_coverage=d.cloud_cover_avg_pct,
            )
            for d in self.coordinator.data.daily(tz)
        ]
