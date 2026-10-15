"""Timestamped popup requests delivered through ordinary HA entity state."""
from homeassistant.components.event import EventEntity

from .entity import device_info


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([DoorbellCommand(entry)])


class DoorbellCommand(EventEntity):
    _attr_has_entity_name = True
    _attr_translation_key = 'doorbell_command'
    _attr_event_types = ['show']
    _attr_icon = 'mdi:doorbell-video'

    def __init__(self, entry):
        self._entry = entry
        self._attr_unique_id = f'{entry.unique_id}_doorbell_command'
        self._attr_device_info = device_info(entry)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._entry.runtime_data.event_entity = self

    async def async_will_remove_from_hass(self):
        self._entry.runtime_data.event_entity = None
        await super().async_will_remove_from_hass()

    def show_doorbell(self):
        self._trigger_event('show')
        self.async_write_ha_state()
