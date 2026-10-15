"""Wake, sleep, and show-doorbell buttons for normal UI automations."""
from homeassistant.components.button import ButtonEntity

from .entity import device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PanelButton(entry, command, icon) for command, icon in [
        ('wake', 'mdi:monitor'), ('sleep', 'mdi:power-sleep'), ('doorbell', 'mdi:doorbell-video'),
    ]])


class PanelButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, command, icon):
        self._runtime = entry.runtime_data
        self._command = command
        self._attr_unique_id = f'{entry.unique_id}_{command}'
        self._attr_translation_key = command
        self._attr_icon = icon
        self._attr_device_info = device_info(entry)

    async def async_press(self):
        await self._runtime.execute(self._command)
