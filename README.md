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

### Link to dmi.dk

The device's **Visit** button opens your location on dmi.dk, which also has DMI's longer
forecast. During setup, the link is filled in with the nearest place (for example
`https://www.dmi.dk/lokation/show/DK/2620997/Gundsømagle`). To use another place, find it on
dmi.dk and paste its address. You can change it later under the integration's **Configure**
button. Leave it empty to use the nearest place.

The nearest place is found offline, from a bundled list of Danish, Faroese and Greenlandic places
with at least 500 inhabitants, from [GeoNames](https://www.geonames.org)
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). Outside those countries, the button
opens dmi.dk's front page.

## Entities

| Entity | Notes |
|---|---|
| `weather.<name>` | Current conditions **measured** at the nearest DMI stations (see below), with the forecast as a fallback for anything not measured; plus hourly and daily forecasts |
| Temperature, Humidity, Pressure | |
| Wind speed, Wind gust, Wind bearing | Bearing is where the wind comes *from* |
| Precipitation next hour | mm expected during the current hour |
| Chance of precipitation | Chance (%) of at least 0.1 mm during the current hour, from DMI's ensemble forecast. Also in the hourly and daily forecasts. |
| Cloud cover, Solar radiation | Solar radiation is the instantaneous flux in W/m² |
| Condition | Derived weather condition (DMI's API has no weather symbol) |
| Model run | Diagnostic: start time of the HARMONIE run in use |
| Dew point, Visibility, Lightning probability | Disabled by default |

The sensors above are **model forecasts for the nearest 2 km grid point** (current hour), not
measurements.

### Observed values

For each measurement, the nearest active DMI weather station (Synop, within 50 km) that measures
it is used. Near Roskilde, for example, temperature, wind, pressure, precipitation and cloud cover
come from Roskilde Lufthavn, and solar radiation from Sjælsmark. Stations report every 10 minutes.

| Sensor | Notes |
|---|---|
| Observed temperature, humidity, pressure | Pressure at sea level |
| Observed wind speed, wind gust, wind bearing | Speed: 10-minute mean. Gust: highest in the last 10 minutes |
| Observed precipitation 10 min, 1 hour | |
| Observed cloud cover, solar radiation | |
| Observed dew point, visibility, sunshine 10 min | Disabled by default |

Each observed sensor has the attributes `station`, `station_id`, `distance_km` and `observed` (time of
the measurement). A value older than one hour shows as unavailable. If there is no station within
50 km, the observed sensors are not created and the weather entity uses the forecast.

The weather entity's **condition** is derived from what is measured right now (precipitation in the
last 10 minutes, cloud cover, visibility, wind), with the forecast filling any gaps.

## Limitations: forecast length

The forecast covers **about 60 hours (2½ days)**. That is the full length of DMI's HARMONIE DINI model,
and nothing in the integration can extend it.

- The **daily forecast** shows today plus the next two days. Later days with fewer than 12 hourly steps
  are left out, so a partial day does not show a misleading high or low. The last day often ends in the
  afternoon or evening.
- The **hourly forecast** ends when the model run ends, typically 50–60 hours ahead depending on how old
  the current run is.
- The **7–10 day forecast on dmi.dk** comes from ECMWF's global model, which is **not** part of DMI's free
  Open Data. It is therefore not available here.

If you need a longer forecast, combine this integration with another weather integration for days 3 and
onwards. Keep DMI for the next 2½ days, where its 2 km model is at its best.

## Being kind to the free API

The integration polls the forecast every 30 minutes and the observations every 10 minutes (one request per station, normally two stations, plus the station list once a day). The model only updates every 3 hours, and DMI's fair use limit is shared
by everyone. When DMI answers with HTTP 429, the library backs off and keeps serving the last forecast.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
