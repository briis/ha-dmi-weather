"""Config flow for DMI Weather."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from pydmi import DMIConnectionError, DMIError, DMIInvalidLocationError
from pydmi.client_async import DMIForecastAsync

from .const import (
    CONF_DMI_URL,
    CONF_LIGHTNING,
    CONF_LIGHTNING_RADIUS,
    CONF_OBSERVATIONS,
    DEFAULT_LIGHTNING_RADIUS,
    DEFAULT_NAME,
    DOMAIN,
)
from .dmi_link import DMI_DK_PREFIX, is_dmi_url, suggest_dmi_url

_LOGGER = logging.getLogger(__name__)

URL_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
)


# Hassfest forbids URLs in translation strings, so they are filled in as placeholders.
PLACEHOLDERS = {
    "dmi_prefix": DMI_DK_PREFIX,
    "example_url": "https://www.dmi.dk/lokation/show/DK/2620997/Gundsømagle",
}


def _settings_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_DMI_URL): URL_SELECTOR,
            vol.Required(CONF_OBSERVATIONS, default=True): selector.BooleanSelector(),
            vol.Required(CONF_LIGHTNING, default=True): selector.BooleanSelector(),
            vol.Required(
                CONF_LIGHTNING_RADIUS, default=DEFAULT_LIGHTNING_RADIUS
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=300,
                    step=5,
                    unit_of_measurement="km",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


def _settings_from_input(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Validate the settings form; returns (options, errors)."""
    url = (user_input.get(CONF_DMI_URL) or "").strip()
    if url and not is_dmi_url(url):
        return {}, {CONF_DMI_URL: "invalid_url"}
    return {
        CONF_DMI_URL: url,  # empty = use the suggestion
        CONF_OBSERVATIONS: bool(user_input.get(CONF_OBSERVATIONS, True)),
        CONF_LIGHTNING: bool(user_input.get(CONF_LIGHTNING, True)),
        CONF_LIGHTNING_RADIUS: int(user_input.get(CONF_LIGHTNING_RADIUS, DEFAULT_LIGHTNING_RADIUS)),
    }, {}


class DMIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DMI Weather."""

    VERSION = 1

    def __init__(self) -> None:
        self._title = ""
        self._data: dict[str, Any] = {}
        self._suggested_url = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DMIOptionsFlow:
        return DMIOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: name and location."""
        errors: dict[str, str] = {}

        if user_input is not None:
            latitude = round(user_input[CONF_LOCATION][CONF_LATITUDE], 2)
            longitude = round(user_input[CONF_LOCATION][CONF_LONGITUDE], 2)

            await self.async_set_unique_id(f"{latitude}_{longitude}")
            self._abort_if_unique_id_configured()

            try:
                api = DMIForecastAsync(
                    latitude,
                    longitude,
                    session=async_get_clientsession(self.hass),
                    include_precipitation_probability=False,  # only validating the location
                )
                await api.get_forecast()
            except DMIInvalidLocationError:
                errors["base"] = "invalid_location"
            except DMIConnectionError:
                errors["base"] = "cannot_connect"
            except DMIError:
                _LOGGER.exception("Unexpected response from DMI")
                errors["base"] = "unknown"
            else:
                self._title = user_input[CONF_NAME]
                self._data = {CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude}
                self._suggested_url = await self.hass.async_add_executor_job(
                    suggest_dmi_url, latitude, longitude
                )
                return await self.async_step_settings()

        defaults = user_input or {
            CONF_NAME: DEFAULT_NAME,
            CONF_LOCATION: {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
            },
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_LOCATION): selector.LocationSelector(
                    selector.LocationSelectorConfig(radius=False)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, defaults),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: dmi.dk link (pre-filled with the nearest place) and optional data."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _settings_from_input(user_input)
            if not errors:
                return self.async_create_entry(title=self._title, data=self._data, options=options)
        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(
                _settings_schema(), user_input or {CONF_DMI_URL: self._suggested_url}
            ),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )


class DMIOptionsFlow(OptionsFlowWithReload):
    """Change the dmi.dk link and turn observations / lightning on or off."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _settings_from_input(user_input)
            if not errors:
                return self.async_create_entry(data=options)

        opts = self.config_entry.options
        url = opts.get(CONF_DMI_URL) or await self.hass.async_add_executor_job(
            suggest_dmi_url,
            self.config_entry.data[CONF_LATITUDE],
            self.config_entry.data[CONF_LONGITUDE],
        )
        current = {
            CONF_DMI_URL: url,
            CONF_OBSERVATIONS: opts.get(CONF_OBSERVATIONS, True),
            CONF_LIGHTNING: opts.get(CONF_LIGHTNING, True),
            CONF_LIGHTNING_RADIUS: opts.get(CONF_LIGHTNING_RADIUS, DEFAULT_LIGHTNING_RADIUS),
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _settings_schema(), user_input or current
            ),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )
