# Changelog

All notable changes to this integration are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-11-09

### Added
- The device's **Visit** button now opens the location's page on dmi.dk (with DMI's longer forecast) instead of DMI's Open Data page. The nearest place is found automatically from a bundled list of places (GeoNames, CC BY 4.0). No requests are made for this. Existing installations get the link automatically.
- A new setup step and an options page (**Configure**) where the link can be changed to any address on dmi.dk.

## [0.2.0] - 2026-11-09

### Changed
- Requires `pydmi-weather==0.3.0`.

### Added
- **Chance of precipitation** (0–100 %, in steps of 10) in the hourly and daily forecasts, and as a new sensor for the current hour. It is the chance of at least 0.1 mm, calculated from DMI's ensemble forecast. The daily value is the highest hourly chance that day. This adds one request to DMI per update (every 30 minutes).
- README and info.md: section on the forecast length (about 2½ days, DMI's HARMONIE limit) and why dmi.dk's 7–10 day forecast is not available.

## [0.1.2] - 2026-11-09

### Fixed
- The current condition could say *Rainy* while the hourly forecast for the same hour showed *Cloudy*. The condition is now derived from the same rounded precipitation amount that is displayed (pydmi-weather 0.2.1).

### Changed
- An hour now needs at least 0.3 mm of precipitation to show as rain or snow (previously 0.1 mm). Hours with only a trace now show a cloud, matching dmi.dk.
- Requires `pydmi-weather==0.2.1`.
- The Marketplace now shows a short project description (`info.md`) instead of the full README.

### Added
- `info.md` and this changelog.

## [0.1.1] - 2026-11-09

### Added
- Current conditions are interpolated between the two hourly forecast steps around now, instead of using the value from the start of the hour. Wind direction takes the shortest way around the compass.
- Entities refresh every 5 minutes from the forecast already in memory. DMI is still only polled every 30 minutes.
- Icons for cloud cover, lightning probability, precipitation and model run. The condition sensor's icon follows the weather.

### Changed
- Sensible display precision on all sensors (for example, humidity and cloud cover as whole numbers).
- Wind speed and wind gust default to m/s, DMI's unit. Existing entities keep the unit they already have. Change it in the entity settings if needed.
- Requires `pydmi-weather==0.2.0`.

## [0.1.0] - 2026-11-09

### Added
- First release.
- Weather entity with current conditions and hourly and daily forecasts from DMI's HARMONIE DINI model.
- Sensors for temperature, humidity, pressure, wind speed, gust and bearing, precipitation next hour, cloud cover, solar radiation, condition and model run. Dew point, visibility and lightning probability are included but disabled by default.
- UI config flow with a map picker, defaulting to the Home Assistant home location.
- English and Danish translations.
- DMI brand assets and attribution (CC BY 4.0) on all entities.
- Release workflow that attaches `dmi_weather.zip` to each GitHub release, and CI for hassfest, Marketplace validation, tests and Ruff.

[Unreleased]: https://github.com/briis/ha-dmi-weather/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/briis/ha-dmi-weather/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/briis/ha-dmi-weather/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/briis/ha-dmi-weather/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/briis/ha-dmi-weather/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/briis/ha-dmi-weather/releases/tag/v0.1.0
