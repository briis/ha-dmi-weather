"""Sensors for DMI Weather.

Mirrors the current forecast hour as individual sensors, so the DMI values can
be plotted next to your own weather station in history graphs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from pydmi import Forecast, ForecastHour

from .coordinator import DMIConfigEntry, DMICoordinator
from .entity import DMIEntity


@dataclass(frozen=True, kw_only=True)
class DMISensorDescription(SensorEntityDescription):
    """Sensor description with a value function on the current forecast hour."""

    value_fn: Callable[[ForecastHour], float | str | None] | None = None
    forecast_fn: Callable[[Forecast], datetime | None] | None = None


SENSORS: tuple[DMISensorDescription, ...] = (
    DMISensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda h: h.temperature_c,
    ),
    DMISensorDescription(
        key="dew_point",
        translation_key="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
        value_fn=lambda h: h.dew_point_c,
    ),
    DMISensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda h: h.humidity_pct,
    ),
    DMISensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
        value_fn=lambda h: h.pressure_hpa,
    ),
    DMISensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        value_fn=lambda h: h.wind_speed_ms,
    ),
    DMISensorDescription(
        key="wind_gust",
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        value_fn=lambda h: h.wind_gust_ms,
    ),
    DMISensorDescription(
        key="wind_bearing",
        translation_key="wind_bearing",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        native_unit_of_measurement=DEGREE,
        value_fn=lambda h: h.wind_bearing_deg,
    ),
    DMISensorDescription(
        key="precipitation_next_hour",
        translation_key="precipitation_next_hour",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        suggested_display_precision=1,
        value_fn=lambda h: h.precipitation_mm,
    ),
    DMISensorDescription(
        key="cloud_cover",
        translation_key="cloud_cover",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda h: h.cloud_cover_pct,
    ),
    DMISensorDescription(
        key="solar_radiation",
        translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        value_fn=lambda h: h.global_radiation_wm2,
    ),
    DMISensorDescription(
        key="visibility",
        translation_key="visibility",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_registry_enabled_default=False,
        value_fn=lambda h: h.visibility_m,
    ),
    DMISensorDescription(
        key="lightning_probability",
        translation_key="lightning_probability",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
        value_fn=lambda h: h.lightning_probability_pct,
    ),
    DMISensorDescription(
        key="condition",
        translation_key="condition",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "clear-night",
            "cloudy",
            "fog",
            "hail",
            "lightning",
            "lightning-rainy",
            "partlycloudy",
            "pouring",
            "rainy",
            "snowy",
            "snowy-rainy",
            "sunny",
            "windy",
            "windy-variant",
        ],
        value_fn=lambda h: h.condition,
    ),
    DMISensorDescription(
        key="model_run",
        translation_key="model_run",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        forecast_fn=lambda f: f.model_run,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DMIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up DMI sensors."""
    coordinator = entry.runtime_data
    async_add_entities(DMISensor(coordinator, description) for description in SENSORS)


class DMISensor(DMIEntity, SensorEntity):
    """A single value from the current DMI forecast hour."""

    entity_description: DMISensorDescription

    def __init__(self, coordinator: DMICoordinator, description: DMISensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> float | str | datetime | None:
        forecast = self.coordinator.data
        if self.entity_description.forecast_fn is not None:
            return self.entity_description.forecast_fn(forecast)
        hour = forecast.current()
        if hour is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(hour)
