"""Config flow for DMI Weather."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from pydmi import DMIConnectionError, DMIError, DMIInvalidLocationError
from pydmi.client_async import DMIForecastAsync

from .const import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DMIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DMI Weather."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude},
                )

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
