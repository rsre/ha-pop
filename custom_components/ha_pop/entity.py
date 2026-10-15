"""Shared device identity for panel entities."""
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, VERSION


def device_info(entry):
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.data['name'],
        manufacturer='HA Pop',
        model='Touchscreen panel',
        sw_version=VERSION,
    )
