from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .api import BijouClient, BijouError, UnsupportedModel, validate_host
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
        }
    )


class BijouConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] = {}

    async def _probe(self, host: str) -> tuple[str, str]:
        client = BijouClient(async_get_clientsession(self.hass), host)
        state = await client.fetch()
        return state.serial, await client.fetch_model()

    async def _configure(
        self, step: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        defaults = dict(entry.data) if entry else {}
        errors = {}
        if user_input is not None:
            defaults.update(user_input)
            try:
                data = dict(user_input)
                data[CONF_HOST] = validate_host(data[CONF_HOST])
                serial, data[CONF_MODEL] = await self._probe(data[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            except UnsupportedModel:
                errors["base"] = "unsupported_model"
            except BijouError:
                errors["base"] = "cannot_connect"
            else:
                if entry is not None:
                    if serial != entry.unique_id:
                        return self.async_abort(reason="wrong_device")
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_MODEL], data=data)
        return self.async_show_form(
            step_id=step, data_schema=_schema(defaults), errors=errors
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._configure("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._configure("reconfigure", user_input)

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.ip
        try:
            serial, model = await self._probe(host)
        except BijouError:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._discovered = {
            CONF_HOST: host,
            CONF_MODEL: model,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }
        self.context["title_placeholders"] = {"name": model}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        model = self._discovered[CONF_MODEL]
        if user_input is not None:
            return self.async_create_entry(title=model, data=self._discovered)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "model": model,
                "host": self._discovered[CONF_HOST],
            },
        )
