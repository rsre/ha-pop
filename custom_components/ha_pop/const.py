"""Constants for the panel integration."""
DOMAIN = 'ha_pop'
VERSION = '0.2.1'
STATIC_URL = '/ha_pop_static'
MODULE_URL = f'{STATIC_URL}/ha-pop-panel.js?v={VERSION}'
DEFAULT_PORT = 8765
PLATFORMS = ['event', 'button']

DEFAULT_ENTITIES = {
    'kitchen_1': 'switch.kitchen_light_1',
    'kitchen_2': 'switch.kitchen_light_2',
    'coffee': 'switch.coffee_maker',
    'coffee_schedule': 'input_boolean.coffee_schedule',
    'coffee_time': 'input_datetime.coffee_time',
    'nave': 'switch.garage_lights',
    'spotlight': 'switch.spotlight',
    'exterior': 'switch.exterior_lights',
    'camera': 'camera.doorbell',
    'washer': 'sensor.washer_status',
    'dryer': 'sensor.dryer_status',
    'climate': 'climate.heating',
    'hot_water': 'sensor.hot_water_setpoint',
    'vacuum': 'vacuum.robot',
}
