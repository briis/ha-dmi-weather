"""Fixtures for DMI Weather tests."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from pydmi import (
    DMIConnectionError,
    Lightning,
    Observations,
    ObservedValue,
    Strike,
    parse_coverage,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components/ in tests."""
    yield


def make_coverage(run: datetime) -> dict:
    steps = 61
    times = [(run + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000Z") for i in range(steps)]
    acc = [0.0]
    for i in range(1, steps):
        acc.append(acc[-1] + (1.5 if 6 <= i <= 8 else 0.0))
    values = {
        "temperature-2m": [280.15] * steps,
        "dew-point-temperature-2m": [277.15] * steps,
        "relative-humidity-2m": [88.0] * steps,
        "pressure-sealevel": [102320.0] * steps,
        "wind-speed-10m": [2.3] * steps,
        "wind-dir-10m": [162.0] * steps,
        "gust-wind-speed-10m": [4.7] * steps,
        "total-precipitation": acc,
        "precipitation-type": [1.0] * steps,
        "fraction-of-cloud-cover": [1.0] * steps,
        "visibility": [50000.0] * steps,
        "probability-of-lightning": [0.4] * steps,
        "downward-short-wave-radiation-flux-instant": [30.0] * steps,
    }
    return {
        "type": "Coverage",
        "domain": {
            "axes": {"t": {"values": times}, "x": {"values": [12.08]}, "y": {"values": [55.65]}}
        },
        "ranges": {k: {"values": v, "shape": [steps, 1, 1]} for k, v in values.items()},
    }


@pytest.fixture
def forecast():
    run = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    return parse_coverage(make_coverage(run))


@pytest.fixture
def mock_dmi(forecast) -> Generator[AsyncMock]:
    """Patch the pydmi async client everywhere the integration uses it."""
    with (
        patch("custom_components.dmi_weather.coordinator.DMIForecastAsync") as coord_cls,
        patch("custom_components.dmi_weather.config_flow.DMIForecastAsync") as flow_cls,
    ):
        for cls in (coord_cls, flow_cls):
            cls.return_value.get_forecast = AsyncMock(return_value=forecast)
            cls.return_value.probability_pending = False
            cls.return_value.cached = None
        yield coord_cls.return_value


@pytest.fixture
def forecast_with_probability(forecast):
    forecast.all_hours = [
        replace(h, precipitation_probability_pct=30.0) for h in forecast.all_hours
    ]
    return forecast


def make_observations_data(**overrides) -> Observations:
    """Observations as from Roskilde Lufthavn / Sjælsmark."""
    now = datetime.now(UTC)
    values = {
        "temperature_c": 6.6,
        "humidity_pct": 80.7,
        "pressure_hpa": 1020.9,
        "wind_speed_ms": 2.57,
        "wind_bearing_deg": 125.0,
        "wind_gust_ms": 3.6,
        "precipitation_10min_mm": 0.0,
        "cloud_cover_pct": 100.0,
        "visibility_m": 20700.0,
        "global_radiation_wm2": 54.0,
    }
    values.update(overrides)
    obs = Observations(fetched_at=now)
    for name, value in values.items():
        if value is None:
            continue
        station = (
            ("06188", "Sjælsmark", 22.3)
            if name == "global_radiation_wm2"
            else ("06170", "Roskilde Lufthavn", 17.1)
        )
        obs.values[name] = ObservedValue(value, now, station[0], station[1], station[2])
    return obs


@pytest.fixture
def mock_obs() -> Generator[AsyncMock]:
    """Patch the pydmi observation client used by the integration."""
    with patch("custom_components.dmi_weather.coordinator.DMIObservationsAsync") as cls:
        cls.return_value.get_observations = AsyncMock(return_value=make_observations_data())
        yield cls.return_value


@pytest.fixture(autouse=True)
def _no_real_observations(request):
    """Tests that don't ask for mock_obs get an observation client that fails."""
    if "mock_obs" in request.fixturenames:
        yield
        return
    with patch("custom_components.dmi_weather.coordinator.DMIObservationsAsync") as cls:
        cls.return_value.get_observations = AsyncMock(side_effect=DMIConnectionError("offline"))
        yield


def make_lightning_data(strikes: list[tuple[float, int]] | None = None) -> Lightning:
    """strikes: (distance_km, minutes_ago). Default: none."""
    now = datetime.now(UTC)
    lt = Lightning(fetched_at=now, radius_km=50.0)
    for distance, minutes in strikes or []:
        lt.strikes.append(
            Strike(now - timedelta(minutes=minutes), 55.8, 12.2, distance, 45, -10.0, 1, 0)
        )
    lt.strikes.sort(key=lambda s: s.observed, reverse=True)
    return lt


@pytest.fixture
def mock_lightning() -> Generator[AsyncMock]:
    with patch("custom_components.dmi_weather.coordinator.DMILightningAsync") as cls:
        cls.return_value.get_lightning = AsyncMock(return_value=make_lightning_data())
        cls.return_value.radius_km = 50.0
        yield cls.return_value


@pytest.fixture(autouse=True)
def _no_real_lightning(request):
    """Tests that don't ask for mock_lightning get a lightning client that fails."""
    if "mock_lightning" in request.fixturenames:
        yield
        return
    with patch("custom_components.dmi_weather.coordinator.DMILightningAsync") as cls:
        cls.return_value.get_lightning = AsyncMock(side_effect=DMIConnectionError("offline"))
        cls.return_value.radius_km = 50.0
        yield
