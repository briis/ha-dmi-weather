"""Fixtures for DMI Weather tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from pydmi import parse_coverage


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
        yield coord_cls.return_value
