"""Constants for the DMI Weather integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dmi_weather"

DEFAULT_NAME: Final = "DMI"

# Option: link to the location on dmi.dk ("Visit" button). Empty = nearest place.
CONF_DMI_URL: Final = "dmi_url"

# Optional data sources (options). Both on by default; existing entries without
# the option behave as "on".
CONF_OBSERVATIONS: Final = "observations"
CONF_LIGHTNING: Final = "lightning"
CONF_LIGHTNING_RADIUS: Final = "lightning_radius"
DEFAULT_LIGHTNING_RADIUS: Final = 50

# Lightning: poll interval, and what counts as "thunder here" for the condition.
LIGHTNING_UPDATE_INTERVAL: Final = timedelta(minutes=5)
LIGHTNING_NEARBY_KM: Final = 20.0
LIGHTNING_RECENT: Final = timedelta(minutes=15)

# HARMONIE runs every 3 hours. Polling every 30 minutes picks up a new run
# within half an hour and keeps the load on DMI's free API negligible.
UPDATE_INTERVAL: Final = timedelta(minutes=30)

# Stations report every 10 minutes.
OBS_UPDATE_INTERVAL: Final = timedelta(minutes=10)

# While the chance of precipitation is missing (DMI busy), poll this often.
# pydmi then retries only the ensemble request; the forecast stays cached.
PROBABILITY_RETRY_INTERVAL: Final = timedelta(minutes=5)

# How often entities re-render the current conditions, which pydmi interpolates
# between hourly steps. Local only - no API calls.
REFRESH_INTERVAL: Final = timedelta(minutes=5)

MANUFACTURER: Final = "DMI (Danmarks Meteorologiske Institut)"
MODEL: Final = "HARMONIE DINI forecast"
