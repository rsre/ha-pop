import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from ha_fakes import fakes, load_integration


class ButtonTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = patch.dict('sys.modules', fakes())
        self.context.start()
        self.addCleanup(self.context.stop)
        load_integration()
        self.button = importlib.import_module('ha_pop_test.button')
        self.entry = SimpleNamespace(unique_id='a' * 32, data={'name': 'Test Panel'}, runtime_data=SimpleNamespace(execute=AsyncMock()))

    async def created(self):
        entities = []
        await self.button.async_setup_entry(None, self.entry, entities.extend)
        return {entity._attr_translation_key: entity for entity in entities}

    async def test_reboot_button_is_a_restart_control_hidden_in_configuration(self):
        buttons = await self.created()
        self.assertEqual(sorted(buttons), ['doorbell', 'reboot', 'sleep', 'wake'])
        reboot = buttons['reboot']
        self.assertEqual(reboot._attr_unique_id, f'{self.entry.unique_id}_reboot')
        self.assertEqual(reboot._attr_icon, 'mdi:restart')
        self.assertEqual(reboot._attr_device_class, self.button.ButtonDeviceClass.RESTART)
        self.assertEqual(reboot._attr_entity_category, self.button.EntityCategory.CONFIG)
        for key in ('wake', 'sleep', 'doorbell'):
            self.assertFalse(hasattr(buttons[key], '_attr_device_class'))
            self.assertFalse(hasattr(buttons[key], '_attr_entity_category'))

    async def test_each_press_runs_only_its_matching_runtime_command(self):
        buttons = await self.created()
        for entity in buttons.values():
            await entity.async_press()
        commands = [call.args[0] for call in self.entry.runtime_data.execute.await_args_list]
        self.assertEqual(commands, ['wake', 'sleep', 'doorbell', 'reboot'])


if __name__ == '__main__':
    unittest.main()
