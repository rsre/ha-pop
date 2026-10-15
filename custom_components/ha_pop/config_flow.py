"""Set up a panel entirely through the Home Assistant UI."""
import re

try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import CannotConnect, InvalidAuth, PanelClient, validate_host
from .const import DEFAULT_PORT, DOMAIN


def form_schema(defaults, dashboard=True):
    fields = {
        vol.Required('name', default=defaults.get('name', 'Wall Panel')): str,
        vol.Required('host', default=defaults.get('host', 'panel.local')): str,
        vol.Required('port', default=defaults.get('port', DEFAULT_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required('token'): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
    }
    if dashboard:
        fields[vol.Required('camera', **({'default': defaults['camera']} if 'camera' in defaults else {}))] = selector.EntitySelector(selector.EntitySelectorConfig(domain='camera'))
        fields[vol.Required('dashboard_path', default=defaults.get('dashboard_path', 'ha-pop-panel'))] = str
    return vol.Schema(fields)


class PanelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data):
        data['host'] = validate_host(data['host'])
        data['name'] = data['name'].strip()
        if not data['name'] or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)+', data['dashboard_path']):
            raise ValueError('Invalid name or dashboard path')
        client = PanelClient(async_get_clientsession(self.hass), data['host'], data['port'], data['token'])
        return await client.health()

    async def async_step_user(self, user_input=None):
        return await self._step('user', user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._step('reconfigure', user_input)

    async def _step(self, step, user_input):
        entry = self._get_reconfigure_entry() if step == 'reconfigure' else None
        defaults = dict(entry.data) if entry else {}
        errors = {}
        if user_input is not None:
            data = {**(dict(entry.data) if entry else {}), **user_input}
            try:
                info = await self._validate(data)
                if entry:
                    if info['id'] != entry.unique_id:
                        return self.async_abort(reason='wrong_device')
                    # The managed dashboard remains at its original URL.
                    if data['dashboard_path'] != entry.data['dashboard_path']:
                        errors['base'] = 'dashboard_path_changed'
                    else:
                        return self.async_update_reload_and_abort(entry, data_updates=data)
                else:
                    await self.async_set_unique_id(info['id'])
                    self._abort_if_unique_id_configured()
                    from homeassistant.components.lovelace.const import LOVELACE_DATA
                    if data['dashboard_path'] in self.hass.data[LOVELACE_DATA].dashboards:
                        errors['base'] = 'dashboard_exists'
                    else:
                        return self.async_create_entry(title=data['name'], data=data)
            except InvalidAuth:
                errors['base'] = 'invalid_auth'
            except CannotConnect:
                errors['base'] = 'cannot_connect'
            except ValueError:
                errors['base'] = 'invalid_config'
            defaults = {**defaults, **{k: v for k, v in data.items() if k != 'token'}}
        return self.async_show_form(step_id=step, data_schema=form_schema(defaults, dashboard=entry is None), errors=errors)
