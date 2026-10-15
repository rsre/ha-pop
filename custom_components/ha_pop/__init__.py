"""Home Assistant integration for a dedicated touchscreen panel."""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv

from .client import CannotConnect, InvalidAuth, PanelClient
from .const import DOMAIN, MODULE_URL, PLATFORMS, STATIC_URL

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class PanelRuntime:
    client: PanelClient
    event_entity: object = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def execute(self, command):
        if command not in ('wake', 'sleep', 'doorbell'):
            raise ValueError('Unsupported command')
        async with self.lock:
            try:
                await self.client.command('wake' if command == 'doorbell' else command)
            except (CannotConnect, InvalidAuth) as error:
                raise HomeAssistantError('The panel could not complete the command. Check its connection and shared token.') from error
            if command == 'doorbell':
                if self.event_entity is None:
                    raise HomeAssistantError('The panel command entity is not ready')
                self.event_entity.show_doorbell()


async def async_setup(hass, config):
    await hass.http.async_register_static_paths([
        StaticPathConfig(STATIC_URL, str(Path(__file__).parent / 'frontend'), True)
    ])
    frontend.add_extra_js_url(hass, MODULE_URL)
    return True


async def async_setup_entry(hass, entry):
    client = PanelClient(async_get_clientsession(hass), entry.data['host'], entry.data['port'], entry.data['token'])
    try:
        info = await client.health()
    except InvalidAuth as error:
        raise ConfigEntryAuthFailed('Panel authentication failed; reconfigure the shared token') from error
    except CannotConnect as error:
        raise ConfigEntryNotReady('Panel is not reachable') from error
    if info['id'] != entry.unique_id:
        raise ConfigEntryError('A different panel is using this address')
    entry.runtime_data = PanelRuntime(client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    from .dashboard import async_setup_dashboard
    try:
        await async_setup_dashboard(hass, entry)
    except Exception:
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        raise
    return True


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    from .dashboard import async_unload_dashboard
    async_unload_dashboard(hass, entry)
    return True
