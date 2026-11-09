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
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.dmi_weather.const import DOMAIN
from pydmi import DMIConnectionError, DMIInvalidLocationError


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
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home"
    assert result["data"] == {CONF_LATITUDE: 55.64, CONF_LONGITUDE: 12.08}


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
