"""Small HA API doubles for offline lifecycle tests (not a full HA runtime)."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).parents[2]


def module(name, **values):
    result = ModuleType(name)
    result.__dict__.update(values)
    return result


class HAError(Exception):
    pass


class ConfigNotFound(HAError):
    pass


class FlowAbort(Exception):
    pass


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        pass
    async def async_set_unique_id(self, value):
        self.unique_id = value
    def _abort_if_unique_id_configured(self):
        if self.unique_id in self.hass.configured:
            raise FlowAbort('already_configured')
    def async_show_form(self, **kwargs):
        return {'type': 'form', **kwargs}
    def async_create_entry(self, **kwargs):
        return {'type': 'create_entry', **kwargs}
    def async_abort(self, **kwargs):
        return {'type': 'abort', **kwargs}
    def _get_reconfigure_entry(self):
        return self.entry
    def async_update_reload_and_abort(self, entry, data_updates):
        entry.data = {**entry.data, **data_updates}
        return {'type': 'abort', 'reason': 'reconfigure_successful'}


class LovelaceStorage:
    def __init__(self, hass, config):
        self.hass, self.config = hass, config
    async def async_load(self, force):
        if self.config['id'] not in self.hass.storage:
            raise ConfigNotFound()
        return self.hass.storage[self.config['id']]
    async def async_save(self, data):
        self.hass.storage[self.config['id']] = data


def fakes():
    frontend = module('homeassistant.components.frontend')
    frontend.async_panel_exists = lambda hass, path: path in hass.panels
    def register(hass, component, **kwargs):
        path = kwargs['frontend_url_path']
        if path in hass.panels:
            raise ValueError('collision')
        hass.panels[path] = kwargs
    frontend.async_register_built_in_panel = register
    frontend.async_remove_panel = lambda hass, path: hass.panels.pop(path)
    frontend.add_extra_js_url = lambda hass, path: hass.modules.append(path)
    result = {
        'homeassistant': module('homeassistant', config_entries=SimpleNamespace(ConfigFlow=ConfigFlow)),
        'homeassistant.components': module('homeassistant.components', frontend=frontend),
        'homeassistant.components.frontend': frontend,
        'homeassistant.components.http': module('http', StaticPathConfig=lambda *a: a),
        'homeassistant.exceptions': module('exceptions', ConfigEntryAuthFailed=type('AuthFailed', (HAError,), {}), ConfigEntryNotReady=type('NotReady', (HAError,), {}), ConfigEntryError=HAError, HomeAssistantError=HAError),
        'homeassistant.helpers': module('helpers'),
        'homeassistant.helpers.aiohttp_client': module('aiohttp_client', async_get_clientsession=lambda hass: hass.session),
        'homeassistant.helpers.config_validation': module('cv', config_entry_only_config_schema=lambda d: d),
        'homeassistant.helpers.selector': module('selector', TextSelector=lambda c: str, TextSelectorConfig=dict, TextSelectorType=SimpleNamespace(PASSWORD='password'), EntitySelector=lambda c: str, EntitySelectorConfig=dict),
        'homeassistant.components.lovelace': module('lovelace'),
        'homeassistant.components.lovelace.const': module('const', LOVELACE_DATA='lovelace', ConfigNotFound=ConfigNotFound),
        'homeassistant.components.lovelace.dashboard': module('dashboard', LovelaceStorage=LovelaceStorage),
    }
    for name, value in result.items():
        value.__name__ = name
        parent, _, child = name.rpartition('.')
        if parent in result:
            setattr(result[parent], child, value)
    return result


def load_integration():
    spec = importlib.util.spec_from_file_location('ha_pop_test', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
    result = importlib.util.module_from_spec(spec)
    sys.modules['ha_pop_test'] = result
    spec.loader.exec_module(result)
    return result
