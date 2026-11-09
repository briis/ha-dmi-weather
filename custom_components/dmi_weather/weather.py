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

from pydmi import ForecastHour, derive_condition
from pydmi.const import PRECIP_THRESHOLD_MM

from .const import LIGHTNING_NEARBY_KM, LIGHTNING_RECENT
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
    """Current conditions (observed where possible, else forecast) plus forecasts."""

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

    async def async_added_to_hass(self) -> None:
        """Also re-render when new observations arrive."""
        await super().async_added_to_hass()
        for extra in (self.coordinator.observations, self.coordinator.lightning):
            if extra is not None:
                self.async_on_remove(extra.async_add_listener(self._handle_coordinator_update))

    @property
    def _now(self) -> ForecastHour | None:
        return self.coordinator.data.current()

    def _value(self, observed: str, forecast: str) -> float | None:
        """Observed value when available, otherwise the forecast for now."""
        obs = self.coordinator.observations
        if obs is not None and (value := obs.value(observed)) is not None:
            return value
        return getattr(self._now, forecast) if self._now else None

    @property
    def condition(self) -> str | None:
        """Derived from what is measured right now, the forecast fills the gaps."""
        now = self._now
        if now is None:
            return None
        obs = self.coordinator.observations
        precip_10min = obs.value("precipitation_10min_mm") if obs else None
        precip_rate = precip_10min * 6 if precip_10min is not None else now.precipitation_mm
        temperature = self._value("temperature_c", "temperature_c")
        precip_type = now.precipitation_type or (
            "snow" if temperature is not None and temperature <= 0 else "rain"
        )
        condition = derive_condition(
            precipitation_mm=precip_rate,
            precipitation_type=precip_type,
            cloud_cover_pct=self._value("cloud_cover_pct", "cloud_cover_pct"),
            visibility_m=self._value("visibility_m", "visibility_m"),
            lightning_probability_pct=now.lightning_probability_pct,
            wind_speed_ms=self._value("wind_speed_ms", "wind_speed_ms"),
            daylight=now.is_daylight,
        )
        # Lightning actually observed nearby beats the forecast's probability.
        if self._thunder_nearby():
            raining = precip_rate is not None and precip_rate >= PRECIP_THRESHOLD_MM
            return "lightning-rainy" if raining else "lightning"
        return condition

    def _thunder_nearby(self) -> bool:
        lightning = self.coordinator.lightning
        if lightning is None or not lightning.last_update_success or lightning.data is None:
            return False
        cutoff = dt_util.utcnow() - LIGHTNING_RECENT
        return any(
            s.distance_km <= LIGHTNING_NEARBY_KM and s.observed >= cutoff
            for s in lightning.data.strikes
        )

    @property
    def native_temperature(self) -> float | None:
        return self._value("temperature_c", "temperature_c")

    @property
    def native_dew_point(self) -> float | None:
        return self._value("dew_point_c", "dew_point_c")

    @property
    def humidity(self) -> float | None:
        return self._value("humidity_pct", "humidity_pct")

    @property
    def native_pressure(self) -> float | None:
        return self._value("pressure_hpa", "pressure_hpa")

    @property
    def native_wind_speed(self) -> float | None:
        return self._value("wind_speed_ms", "wind_speed_ms")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._value("wind_gust_ms", "wind_gust_ms")

    @property
    def wind_bearing(self) -> float | None:
        return self._value("wind_bearing_deg", "wind_bearing_deg")

    @property
    def cloud_coverage(self) -> float | None:
        return self._value("cloud_cover_pct", "cloud_cover_pct")

    @property
    def native_visibility(self) -> float | None:
        return self._value("visibility_m", "visibility_m")

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
                precipitation_probability=h.precipitation_probability_pct,
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
                precipitation_probability=d.precipitation_probability_pct,
                native_wind_speed=d.wind_speed_max_ms,
                native_wind_gust_speed=d.wind_gust_max_ms,
                wind_bearing=d.wind_bearing_deg,
                humidity=d.humidity_avg_pct,
                cloud_coverage=d.cloud_cover_avg_pct,
            )
            for d in self.coordinator.data.daily(tz)
        ]
