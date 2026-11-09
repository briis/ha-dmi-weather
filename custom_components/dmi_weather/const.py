"""Constants for the DMI Weather integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dmi_weather"

DEFAULT_NAME: Final = "DMI"

# HARMONIE runs every 3 hours. Polling every 30 minutes picks up a new run
# within half an hour and keeps the load on DMI's free API negligible.
UPDATE_INTERVAL: Final = timedelta(minutes=30)

MANUFACTURER: Final = "DMI (Danmarks Meteorologiske Institut)"
MODEL: Final = "HARMONIE DINI forecast"
