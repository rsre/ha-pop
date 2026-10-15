"""Register a native, editable Lovelace dashboard without editing YAML files."""
from homeassistant.components import frontend
from homeassistant.components.lovelace.const import ConfigNotFound, LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.exceptions import ConfigEntryError

from .const import DEFAULT_ENTITIES


def default_dashboard(entry):
    entities = {**DEFAULT_ENTITIES, 'camera': entry.data['camera'], 'doorbell_command': entry.runtime_data.event_entity.entity_id}
    return {'title': entry.data['name'], 'views': [{
        'title': 'Home', 'path': 'home', 'type': 'panel', 'cards': [{
            'type': 'custom:ha-pop-panel', 'title': entry.data['name'],
            'entities': entities, 'camera_card': {'video_fit': 'contain', 'talk_mode': 'native'},
        }],
    }]}


async def async_setup_dashboard(hass, entry):
    path = entry.data['dashboard_path']
    dashboards = hass.data[LOVELACE_DATA].dashboards
    if path in dashboards or frontend.async_panel_exists(hass, path):
        raise ConfigEntryError('The dashboard URL is already in use; choose another URL during setup')
    if entry.runtime_data.event_entity is None:
        raise ConfigEntryError('Panel command entity was not created')
    config = {'id': f'ha_pop_{entry.entry_id}', 'url_path': path, 'title': entry.data['name'],
              'icon': 'mdi:tablet-dashboard', 'show_in_sidebar': True, 'require_admin': False, 'mode': 'storage'}
    dashboard = LovelaceStorage(hass, config)
    dashboard.ha_pop_entry_id = entry.entry_id
    try:
        await dashboard.async_load(False)
    except ConfigNotFound:
        await dashboard.async_save(default_dashboard(entry))
    # Existing saved layouts are retained, including all edits through the UI.
    dashboards[path] = dashboard
    try:
        frontend.async_register_built_in_panel(
            hass, 'lovelace', sidebar_title=entry.data['name'], sidebar_icon='mdi:tablet-dashboard',
            frontend_url_path=path, config={'mode': 'storage'}, require_admin=False,
        )
    except Exception:
        dashboards.pop(path, None)
        raise


def async_unload_dashboard(hass, entry):
    path = entry.data['dashboard_path']
    dashboards = hass.data[LOVELACE_DATA].dashboards
    if getattr(dashboards.get(path), 'ha_pop_entry_id', None) == entry.entry_id:
        dashboards.pop(path)
        frontend.async_remove_panel(hass, path)
