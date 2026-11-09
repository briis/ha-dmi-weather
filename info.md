# <img src="https://raw.githubusercontent.com/briis/ha-dmi-weather/main/custom_components/dmi_weather/brand/icon.png" alt="DMI" width="40" height="40" align="absmiddle"> DMI Weather

Weather forecast for Home Assistant from **DMI** (Danmarks Meteorologiske Institut), using DMI's free Open Data API. No API key needed.

- **Weather entity:** current conditions plus hourly and daily forecasts
- **Observed values** from the nearest DMI weather stations, every 10 minutes, used for the current conditions
- **Sensors:** temperature, humidity, pressure, wind, precipitation, cloud cover, solar radiation and more. Plot them next to your own weather station.
- **Model:** HARMONIE DINI. About 2 km grid, hourly steps, about 60 hours (2½ days) ahead, updated every 3 hours.
- **Smooth current values:** current values are interpolated between the hourly forecasts and refreshed every 5 minutes, without extra requests to DMI.
- **Setup:** done in the UI, with a map picker. English and Danish.

Covers Denmark and the rest of Northwestern Europe inside DMI's HARMONIE model area.

**Note:** the forecast only reaches about 2½ days ahead (today + 2 days). That is the full length of DMI's free model data. The longer forecast on dmi.dk is not included in DMI's Open Data.

Data: DMI, licensed CC BY 4.0. This is a community integration and is not made or endorsed by DMI.

See the [README](https://github.com/briis/ha-dmi-weather) for details.
