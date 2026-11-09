"""Setup, entities and config flow tests."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.dmi_weather.const import CONF_DMI_URL, DOMAIN
from custom_components.dmi_weather.dmi_link import suggest_dmi_url
from pydmi import DMIConnectionError, DMIInvalidLocationError

from .conftest import make_lightning_data, make_observations_data


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DMI Roskilde",
        unique_id="55.64_12.08",
        data={CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_and_entities(hass: HomeAssistant, mock_dmi) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED

    weather = hass.states.get("weather.dmi_roskilde")
    assert weather is not None
    assert weather.state == "cloudy"
    assert weather.attributes["temperature"] == 7.0
    assert weather.attributes["pressure"] == 1023.2
    assert weather.attributes["attribution"].startswith("Data from DMI")

    assert hass.states.get("sensor.dmi_roskilde_temperature").state == "7.0"
    assert hass.states.get("sensor.dmi_roskilde_solar_radiation").state == "30.0"
    assert hass.states.get("sensor.dmi_roskilde_condition").state == "cloudy"
    assert hass.states.get("sensor.dmi_roskilde_model_run") is not None
    # disabled by default
    assert hass.states.get("sensor.dmi_roskilde_visibility") is None

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_forecasts(hass: HomeAssistant, mock_dmi) -> None:
    await _setup(hass)
    for kind in ("hourly", "daily"):
        resp = await hass.services.async_call(
            WEATHER_DOMAIN,
            SERVICE_GET_FORECASTS,
            {"entity_id": "weather.dmi_roskilde", "type": kind},
            blocking=True,
            return_response=True,
        )
        fc = resp["weather.dmi_roskilde"]["forecast"]
        assert fc, kind
        assert fc[0]["temperature"] is not None
    hourly = (
        await hass.services.async_call(
            WEATHER_DOMAIN,
            SERVICE_GET_FORECASTS,
            {"entity_id": "weather.dmi_roskilde", "type": "hourly"},
            blocking=True,
            return_response=True,
        )
    )["weather.dmi_roskilde"]["forecast"]
    assert hourly[0]["condition"] == "cloudy"
    assert any(h["condition"] == "rainy" for h in hourly)


async def test_setup_retry_on_error(hass: HomeAssistant, mock_dmi) -> None:
    mock_dmi.get_forecast = AsyncMock(side_effect=DMIConnectionError("down"))
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_flow(hass: HomeAssistant, mock_dmi) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.dmi_weather.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Home", CONF_LOCATION: {CONF_LATITUDE: 55.6412, CONF_LONGITUDE: 12.0803}},
        )
        # step 2: dmi.dk link, pre-filled with the nearest place
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "settings"
        suggested = next(
            k.description["suggested_value"]
            for k in result["data_schema"].schema
            if k == CONF_DMI_URL
        )
        assert suggested == "https://www.dmi.dk/lokation/show/DK/2614481/Roskilde"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_DMI_URL: suggested}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["data"] == {CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08}
    assert result["options"] == {
        CONF_DMI_URL: suggested,
        "observations": True,
        "lightning": True,
        "lightning_radius": 50,
    }


async def test_config_flow_rejects_non_dmi_link(hass: HomeAssistant, mock_dmi) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "Home", CONF_LOCATION: {CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08}},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DMI_URL: "https://example.com/weather"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_DMI_URL: "invalid_url"}


def test_suggest_dmi_url() -> None:
    assert suggest_dmi_url(55.7357, 12.1516) == (
        "https://www.dmi.dk/lokation/show/DK/2620997/Gunds%C3%B8magle"
    )
    assert suggest_dmi_url(52.37, 4.90) == "https://www.dmi.dk"  # Amsterdam: no Danish place nearby


async def test_device_link_and_options(hass: HomeAssistant, mock_dmi) -> None:
    entry = await _setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    # entries created before this option existed get the nearest place automatically
    assert device.configuration_url == "https://www.dmi.dk/lokation/show/DK/2614481/Roskilde"

    own = "https://www.dmi.dk/lokation/show/DK/2620997/Gunds%C3%B8magle"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_DMI_URL: own}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()  # options flow reloads the entry
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.configuration_url == own


async def test_config_flow_invalid_location(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.dmi_weather.config_flow.DMIForecastAsync",
        side_effect=DMIInvalidLocationError("outside"),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Cape Town", CONF_LOCATION: {CONF_LATITUDE: -33.9, CONF_LONGITUDE: 18.4}},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_location"}


async def test_units_and_icons(hass: HomeAssistant, mock_dmi) -> None:
    await _setup(hass)
    for name in ("wind_speed", "wind_gust"):
        state = hass.states.get(f"sensor.dmi_roskilde_{name}")
        assert state.attributes["unit_of_measurement"] == "m/s", name


async def test_current_values_refresh_without_api_calls(hass: HomeAssistant, mock_dmi) -> None:
    await _setup(hass)
    calls = mock_dmi.get_forecast.await_count
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
    await hass.async_block_till_done()
    assert mock_dmi.get_forecast.await_count == calls  # refresh is local only


async def test_precipitation_probability(
    hass: HomeAssistant, mock_dmi, forecast_with_probability
) -> None:
    mock_dmi.get_forecast = AsyncMock(return_value=forecast_with_probability)
    await _setup(hass)
    assert hass.states.get("sensor.dmi_roskilde_chance_of_precipitation").state == "30.0"
    resp = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {"entity_id": "weather.dmi_roskilde", "type": "hourly"},
        blocking=True,
        return_response=True,
    )
    assert resp["weather.dmi_roskilde"]["forecast"][0]["precipitation_probability"] == 30.0


async def test_polls_faster_while_probability_missing(hass: HomeAssistant, mock_dmi) -> None:
    mock_dmi.probability_pending = True
    entry = await _setup(hass)
    assert entry.runtime_data.update_interval == timedelta(minutes=5)

    mock_dmi.probability_pending = False
    await entry.runtime_data.async_refresh()
    assert entry.runtime_data.update_interval == timedelta(minutes=30)


async def test_setup_check_skips_ensemble(hass: HomeAssistant, mock_dmi) -> None:
    with patch("custom_components.dmi_weather.config_flow.DMIForecastAsync") as flow_cls:
        flow_cls.return_value.get_forecast = AsyncMock()
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Home", CONF_LOCATION: {CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08}},
        )
    assert flow_cls.call_args.kwargs["include_precipitation_probability"] is False


async def test_weather_uses_observations(hass: HomeAssistant, mock_dmi, mock_obs) -> None:
    await _setup(hass)
    state = hass.states.get("weather.dmi_roskilde")
    assert state.attributes["temperature"] == 6.6  # observed, not forecast 7.0
    assert state.attributes["humidity"] == 81  # 80.7 observed
    assert state.state == "cloudy"

    sensor = hass.states.get("sensor.dmi_roskilde_observed_temperature")
    assert sensor.state == "6.6"
    assert sensor.attributes["station"] == "Roskilde Lufthavn"
    assert sensor.attributes["distance_km"] == 17.1
    assert (
        hass.states.get("sensor.dmi_roskilde_observed_solar_radiation").attributes["station"]
        == "Sjælsmark"
    )
    # forecast sensors still there
    assert hass.states.get("sensor.dmi_roskilde_temperature").state == "7.0"


async def test_observed_rain_sets_condition(hass: HomeAssistant, mock_dmi, mock_obs) -> None:
    mock_obs.get_observations = AsyncMock(
        return_value=make_observations_data(precipitation_10min_mm=0.2)
    )  # 1.2 mm/h
    await _setup(hass)
    assert hass.states.get("weather.dmi_roskilde").state == "rainy"


async def test_falls_back_to_forecast_without_observations(hass: HomeAssistant, mock_dmi) -> None:
    entry = await _setup(hass)  # observation client fails (autouse fixture)
    assert entry.state is ConfigEntryState.LOADED
    state = hass.states.get("weather.dmi_roskilde")
    assert state.attributes["temperature"] == 7.0  # forecast
    assert hass.states.get("sensor.dmi_roskilde_observed_temperature").state == "unavailable"


async def test_missing_single_value_falls_back(hass: HomeAssistant, mock_dmi, mock_obs) -> None:
    mock_obs.get_observations = AsyncMock(return_value=make_observations_data(pressure_hpa=None))
    await _setup(hass)
    state = hass.states.get("weather.dmi_roskilde")
    assert state.attributes["pressure"] == 1023.2  # forecast value (observed is 1020.9)
    assert state.attributes["temperature"] == 6.6  # still observed
    assert hass.states.get("sensor.dmi_roskilde_observed_pressure").state == "unavailable"


async def test_no_stations_nearby(hass: HomeAssistant, mock_dmi, mock_obs) -> None:
    mock_obs.get_observations = AsyncMock(side_effect=DMIInvalidLocationError("none"))
    entry = await _setup(hass)
    assert entry.runtime_data.observations.no_stations
    assert entry.runtime_data.observations.update_interval is None  # stops polling
    assert hass.states.get("sensor.dmi_roskilde_observed_temperature") is None  # not created
    assert hass.states.get("weather.dmi_roskilde").attributes["temperature"] == 7.0


async def test_lightning_sensors(hass: HomeAssistant, mock_dmi, mock_obs, mock_lightning) -> None:
    mock_lightning.get_lightning = AsyncMock(
        return_value=make_lightning_data([(35.0, 3), (12.0, 40)])
    )
    await _setup(hass)
    assert hass.states.get("sensor.dmi_roskilde_lightning_strikes_last_hour").state == "2"
    nearest = hass.states.get("sensor.dmi_roskilde_nearest_lightning_strike")
    assert nearest.state == "12.0"
    assert nearest.attributes["bearing_deg"] == 45
    assert nearest.attributes["radius_km"] == 50.0
    last = hass.states.get("sensor.dmi_roskilde_last_lightning_strike")
    assert last.attributes["distance_km"] == 35.0
    # 35 km away is not "here": condition stays cloudy
    assert hass.states.get("weather.dmi_roskilde").state == "cloudy"


async def test_thunder_nearby_sets_condition(
    hass: HomeAssistant, mock_dmi, mock_obs, mock_lightning
) -> None:
    mock_lightning.get_lightning = AsyncMock(return_value=make_lightning_data([(8.0, 5)]))
    await _setup(hass)
    assert hass.states.get("weather.dmi_roskilde").state == "lightning"


async def test_no_strikes_states(hass: HomeAssistant, mock_dmi, mock_obs, mock_lightning) -> None:
    await _setup(hass)
    assert hass.states.get("sensor.dmi_roskilde_lightning_strikes_last_hour").state == "0"
    assert hass.states.get("sensor.dmi_roskilde_nearest_lightning_strike").state == "unknown"


async def test_options_turn_off_sources_and_remove_sensors(
    hass: HomeAssistant, mock_dmi, mock_obs, mock_lightning
) -> None:
    entry = await _setup(hass)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_observed_temperature")
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_lightning_strikes_1h")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DMI_URL: "", "observations": False, "lightning": False, "lightning_radius": 50},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()  # reload

    assert entry.runtime_data.observations is None
    assert entry.runtime_data.lightning is None
    assert not registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_observed_temperature"
    )
    assert not registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_lightning_strikes_1h"
    )
    # the forecast's lightning probability sensor is NOT a lightning-strike sensor
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_lightning_probability")
    # weather now uses the forecast
    assert hass.states.get("weather.dmi_roskilde").attributes["temperature"] == 7.0


async def test_lightning_radius_option(hass: HomeAssistant, mock_dmi, mock_lightning) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="DMI Roskilde",
        unique_id="55.64_12.08",
        data={CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08},
        options={"lightning_radius": 120},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.dmi_weather.coordinator.DMILightningAsync") as cls:
        cls.return_value.get_lightning = AsyncMock(return_value=make_lightning_data())
        cls.return_value.radius_km = 120
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert cls.call_args.kwargs["radius_km"] == 120


async def test_options_change_reuses_clients(
    hass: HomeAssistant, mock_dmi, mock_obs, mock_lightning
) -> None:
    """Changing the lightning radius must not re-create the forecast/observation clients
    (their caches would be lost and DMI hit with a burst of requests)."""
    with (
        patch("custom_components.dmi_weather.coordinator.DMIForecastAsync") as fc_cls,
        patch("custom_components.dmi_weather.coordinator.DMIObservationsAsync") as obs_cls,
        patch("custom_components.dmi_weather.coordinator.DMILightningAsync") as lt_cls,
    ):
        fc_cls.return_value = mock_dmi
        obs_cls.return_value = mock_obs
        lt_cls.side_effect = lambda *a, **kw: _lightning_client(kw["radius_km"])
        entry = await _setup(hass)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_DMI_URL: "", "observations": True, "lightning": True, "lightning_radius": 20},
        )
        await hass.async_block_till_done()  # reload
        assert entry.state is ConfigEntryState.LOADED
        assert fc_cls.call_count == 1
        assert obs_cls.call_count == 1
        assert lt_cls.call_count == 2  # new radius -> new lightning client
        assert entry.runtime_data.lightning.api.radius_km == 20


def _lightning_client(radius_km: float) -> AsyncMock:
    client = AsyncMock()
    client.radius_km = radius_km
    client.get_lightning = AsyncMock(return_value=make_lightning_data())
    return client


async def test_failed_update_keeps_last_forecast(hass: HomeAssistant, mock_dmi, forecast) -> None:
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    mock_dmi.cached = forecast
    mock_dmi.get_forecast = AsyncMock(side_effect=DMIConnectionError("timeout"))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.last_update_success
    assert coordinator.update_interval == timedelta(minutes=2)
    assert hass.states.get("weather.dmi_roskilde").state == "cloudy"  # still available

    mock_dmi.get_forecast = AsyncMock(return_value=forecast)
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(minutes=30)  # back to normal


async def test_failed_update_without_cache_is_unavailable(hass: HomeAssistant, mock_dmi) -> None:
    entry = await _setup(hass)
    mock_dmi.cached = None
    mock_dmi.get_forecast = AsyncMock(side_effect=DMIConnectionError("timeout"))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("weather.dmi_roskilde").state == "unavailable"


async def test_removing_entry_forgets_clients(hass: HomeAssistant, mock_dmi) -> None:
    entry = await _setup(hass)
    assert entry.entry_id in hass.data[DOMAIN]
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
