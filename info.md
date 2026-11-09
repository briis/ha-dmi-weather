# DMI Weather

Weather forecast for Home Assistant from **DMI** (Danmarks Meteorologiske Institut), using DMI's free Open Data API. No API key needed.

- **Weather entity:** current conditions plus hourly and daily forecasts
- **Sensors:** temperature, humidity, pressure, wind, precipitation, cloud cover, solar radiation and more. Plot them next to your own weather station.
- **Model:** HARMONIE DINI. About 2 km grid, hourly steps, about 60 hours (2½ days) ahead, updated every 3 hours.
- **Smooth current values:** current values are interpolated between the hourly forecasts and refreshed every 5 minutes, without extra requests to DMI.
- **Setup:** done in the UI, with a map picker. English and Danish.

Covers Denmark and the rest of Northwestern Europe inside DMI's HARMONIE model area.

Data: DMI, licensed CC BY 4.0. This is a community integration and is not made or endorsed by DMI.

See the [README](https://github.com/briis/ha-dmi-weather) for details.
