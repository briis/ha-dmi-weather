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
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pydmi import ATTRIBUTION, Forecast, ForecastHour, Lightning, Strike

from .coordinator import (
    DMIConfigEntry,
    DMICoordinator,
    DMILightningCoordinator,
    DMIObservationCoordinator,
)
from .entity import DMIEntity, dmi_device_info


@dataclass(frozen=True, kw_only=True)
class DMISensorDescription(SensorEntityDescription):
    """Sensor description with a value function on the current forecast hour."""

    value_fn: Callable[[ForecastHour], float | str | None] | None = None
    forecast_fn: Callable[[Forecast], datetime | None] | None = None


SENSORS: tuple[DMISensorDescription, ...] = (
    DMISensorDescription(
        key="temperature",
        suggested_display_precision=1,
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda h: h.temperature_c,
    ),
    DMISensorDescription(
        key="dew_point",
        suggested_display_precision=1,
        translation_key="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
        value_fn=lambda h: h.dew_point_c,
    ),
    DMISensorDescription(
        key="humidity",
        suggested_display_precision=0,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda h: h.humidity_pct,
    ),
    DMISensorDescription(
        key="pressure",
        suggested_display_precision=1,
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.HPA,
        value_fn=lambda h: h.pressure_hpa,
    ),
    DMISensorDescription(
        key="wind_speed",
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        value_fn=lambda h: h.wind_speed_ms,
    ),
    DMISensorDescription(
        key="wind_gust",
        suggested_display_precision=1,
        suggested_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        translation_key="wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        value_fn=lambda h: h.wind_gust_ms,
    ),
    DMISensorDescription(
        key="wind_bearing",
        suggested_display_precision=0,
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
        key="precipitation_probability",
        translation_key="precipitation_probability",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda h: h.precipitation_probability_pct,
    ),
    DMISensorDescription(
        key="cloud_cover",
        suggested_display_precision=0,
        translation_key="cloud_cover",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda h: h.cloud_cover_pct,
    ),
    DMISensorDescription(
        key="solar_radiation",
        suggested_display_precision=0,
        translation_key="solar_radiation",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        value_fn=lambda h: h.global_radiation_wm2,
    ),
    DMISensorDescription(
        key="visibility",
        suggested_display_precision=0,
        translation_key="visibility",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.METERS,
        entity_registry_enabled_default=False,
        value_fn=lambda h: h.visibility_m,
    ),
    DMISensorDescription(
        key="lightning_probability",
        suggested_display_precision=1,
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
    if coordinator.lightning is not None:
        async_add_entities(
            DMILightningSensor(coordinator, description) for description in LIGHTNING_SENSORS
        )
    if coordinator.observations is not None and not coordinator.observations.no_stations:
        async_add_entities(
            DMIObservationSensor(coordinator, description) for description in OBSERVATION_SENSORS
        )


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


# --- observed values (nearest DMI station) ------------------------------------


@dataclass(frozen=True, kw_only=True)
class DMIObservationSensorDescription(SensorEntityDescription):
    """`field` is the pydmi Observations field name."""

    field: str


def _obs(key, field, **kw) -> DMIObservationSensorDescription:
    return DMIObservationSensorDescription(
        key=key, translation_key=key, field=field, state_class=SensorStateClass.MEASUREMENT, **kw
    )


OBSERVATION_SENSORS: tuple[DMIObservationSensorDescription, ...] = (
    _obs(
        "observed_temperature",
        "temperature_c",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    _obs(
        "observed_dew_point",
        "dew_point_c",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    _obs(
        "observed_humidity",
        "humidity_pct",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    _obs(
        "observed_pressure",
        "pressure_hpa",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        suggested_display_precision=1,
    ),
    _obs(
        "observed_wind_speed",
        "wind_speed_ms",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_display_precision=1,
    ),
    _obs(
        "observed_wind_gust",
        "wind_gust_ms",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        suggested_display_precision=1,
    ),
    DMIObservationSensorDescription(
        key="observed_wind_bearing",
        translation_key="observed_wind_bearing",
        field="wind_bearing_deg",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=0,
    ),
    _obs(
        "observed_precipitation_10min",
        "precipitation_10min_mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        suggested_display_precision=1,
    ),
    _obs(
        "observed_precipitation_1h",
        "precipitation_1h_mm",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        suggested_display_precision=1,
    ),
    _obs(
        "observed_cloud_cover",
        "cloud_cover_pct",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    _obs(
        "observed_visibility",
        "visibility_m",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
    ),
    _obs(
        "observed_solar_radiation",
        "global_radiation_wm2",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        suggested_display_precision=0,
    ),
    _obs(
        "observed_sunshine",
        "sunshine_10min_min",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
    ),
)


class DMIObservationSensor(CoordinatorEntity[DMIObservationCoordinator], SensorEntity):
    """A measured value from the nearest DMI station that measures it."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: DMIObservationSensorDescription

    def __init__(
        self, forecast: DMICoordinator, description: DMIObservationSensorDescription
    ) -> None:
        assert forecast.observations is not None
        super().__init__(forecast.observations)
        self.entity_description = description
        self._attr_unique_id = f"{forecast.config_entry.entry_id}_{description.key}"
        self._attr_device_info = dmi_device_info(forecast)

    def _item(self):
        data = self.coordinator.data
        return data.values.get(self.entity_description.field) if data else None

    @property
    def available(self) -> bool:
        return super().available and self._item() is not None

    @property
    def native_value(self) -> float | None:
        item = self._item()
        return item.value if item else None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        item = self._item()
        if item is None:
            return None
        return {
            "station": item.station_name,
            "station_id": item.station_id,
            "distance_km": item.distance_km,
            "observed": item.observed.isoformat(),
        }


# --- lightning (DMI Lightning Data API) -----------------------------------------


@dataclass(frozen=True, kw_only=True)
class DMILightningSensorDescription(SensorEntityDescription):
    """`value_fn` reads the Lightning data; `strike_fn` picks a strike for attributes."""

    value_fn: Callable[[Lightning], float | int | datetime | None]
    strike_fn: Callable[[Lightning], Strike | None] | None = None


LIGHTNING_SENSORS: tuple[DMILightningSensorDescription, ...] = (
    DMILightningSensorDescription(
        key="lightning_strikes_1h",
        translation_key="lightning_strikes_1h",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="strikes",
        value_fn=lambda lt: lt.count_1h,
    ),
    DMILightningSensorDescription(
        key="lightning_strikes_10min",
        translation_key="lightning_strikes_10min",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="strikes",
        entity_registry_enabled_default=False,
        value_fn=lambda lt: lt.count_10min,
    ),
    DMILightningSensorDescription(
        key="lightning_strike_nearest_distance",
        translation_key="lightning_strike_nearest_distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        value_fn=lambda lt: lt.nearest.distance_km if lt.nearest else None,
        strike_fn=lambda lt: lt.nearest,
    ),
    DMILightningSensorDescription(
        key="lightning_strike_last",
        translation_key="lightning_strike_last",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda lt: lt.latest.observed if lt.latest else None,
        strike_fn=lambda lt: lt.latest,
    ),
)


class DMILightningSensor(CoordinatorEntity[DMILightningCoordinator], SensorEntity):
    """Lightning within the configured radius during the last hour."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description: DMILightningSensorDescription

    def __init__(
        self, forecast: DMICoordinator, description: DMILightningSensorDescription
    ) -> None:
        assert forecast.lightning is not None
        super().__init__(forecast.lightning)
        self.entity_description = description
        self._attr_unique_id = f"{forecast.config_entry.entry_id}_{description.key}"
        self._attr_device_info = dmi_device_info(forecast)

    @property
    def native_value(self) -> float | int | datetime | None:
        data = self.coordinator.data
        return self.entity_description.value_fn(data) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        data = self.coordinator.data
        attrs: dict[str, object] = {"radius_km": self.coordinator.api.radius_km}
        if data is None or self.entity_description.strike_fn is None:
            return attrs
        strike = self.entity_description.strike_fn(data)
        if strike is not None:
            attrs.update(
                distance_km=strike.distance_km,
                bearing_deg=strike.bearing_deg,
                observed=strike.observed.isoformat(),
                current_ka=strike.current_ka,
            )
        return attrs
