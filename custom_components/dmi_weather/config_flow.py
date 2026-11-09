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

from .const import CONF_DMI_URL, DEFAULT_NAME, DOMAIN
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


def _link_schema() -> vol.Schema:
    return vol.Schema({vol.Optional(CONF_DMI_URL): URL_SELECTOR})


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
                    latitude, longitude, session=async_get_clientsession(self.hass)
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
                return await self.async_step_link()

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

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: link to the location on dmi.dk (pre-filled with the nearest place)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = (user_input.get(CONF_DMI_URL) or "").strip()
            if url and not is_dmi_url(url):
                errors[CONF_DMI_URL] = "invalid_url"
            else:
                return self.async_create_entry(
                    title=self._title,
                    data=self._data,
                    options={CONF_DMI_URL: url},  # empty = use the suggestion
                )
        return self.async_show_form(
            step_id="link",
            data_schema=self.add_suggested_values_to_schema(
                _link_schema(), user_input or {CONF_DMI_URL: self._suggested_url}
            ),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )


class DMIOptionsFlow(OptionsFlowWithReload):
    """Change the dmi.dk link later."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = (user_input.get(CONF_DMI_URL) or "").strip()
            if url and not is_dmi_url(url):
                errors[CONF_DMI_URL] = "invalid_url"
            else:
                return self.async_create_entry(data={CONF_DMI_URL: url})

        current = self.config_entry.options.get(
            CONF_DMI_URL
        ) or await self.hass.async_add_executor_job(
            suggest_dmi_url,
            self.config_entry.data[CONF_LATITUDE],
            self.config_entry.data[CONF_LONGITUDE],
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _link_schema(), user_input or {CONF_DMI_URL: current}
            ),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )
