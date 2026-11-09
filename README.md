# <img src="https://raw.githubusercontent.com/briis/ha-dmi-weather/main/custom_components/dmi_weather/brand/icon.png" alt="DMI" width="40" height="40" align="absmiddle"> DMI Weather for Home Assistant

A Home Assistant integration that adds a **weather entity** and **sensors** with forecast data
from DMI (Danmarks Meteorologiske Institut). The data comes from DMI's free
[Open Data API](https://www.dmi.dk/friedata), via the [`pydmi-weather`](https://pypi.org/project/pydmi-weather/) library.

- HARMONIE DINI model: ~2 km grid, hourly steps, ~60 hours ahead, new run every 3 hours
- No API key needed
- Hourly and daily forecasts in the weather entity
- Separate sensors for the current hour, so DMI can be compared with your own weather station
- UI setup with a map picker
- English and Danish translations

> Data: DMI, licensed [CC BY 4.0](https://www.dmi.dk/friedata/dokumentation/terms-of-use).
> All entities carry the required attribution.
>
> This is a community integration and is not made or endorsed by DMI. The DMI logo is
> used as the integration's icon to show where the data comes from.

## Installation

### Marketplace (Home Assistant 2026.11 and later)

DMI Weather is not in the Marketplace catalog yet, so add it as a custom repository:

1. Go to **Settings → Marketplace** and select **Add from link** (upper-right corner).
2. Enter `briis/ha-dmi-weather` and confirm. Adding a custom repository needs a GitHub connection;
   the dialog asks you to connect if you have not already.
3. Download **DMI Weather** and restart Home Assistant.
4. **Settings → Devices & services → Add integration → DMI Weather**.

On Home Assistant 2026.1–2026.10, add the same link as a custom repository (type *Integration*) in HACS.

### Manual

Copy `custom_components/dmi_weather` to `<config>/custom_components/` and restart.

## Configuration

Pick a name and a location on the map. The location defaults to your Home Assistant home location. It must be
inside DMI's HARMONIE DINI model area (Northwestern Europe). Add the integration more than once to get forecasts
for several places.

## Entities

| Entity | Notes |
|---|---|
| `weather.<name>` | Current conditions (interpolated between hourly steps, refreshed every 5 minutes), plus hourly and daily forecasts |
| Temperature, Humidity, Pressure | |
| Wind speed, Wind gust, Wind bearing | Bearing is where the wind comes *from* |
| Precipitation next hour | mm expected during the current hour |
| Cloud cover, Solar radiation | Solar radiation is the instantaneous flux in W/m² |
| Condition | Derived weather condition (DMI's API has no weather symbol) |
| Model run | Diagnostic: start time of the HARMONIE run in use |
| Dew point, Visibility, Lightning probability | Disabled by default |

All values are **model forecasts for the nearest 2 km grid point**, not measurements.

## Being kind to the free API

The integration polls every 30 minutes. The model only updates every 3 hours, and DMI's fair use limit is shared
by everyone. When DMI answers with HTTP 429, the library backs off and keeps serving the last forecast.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
