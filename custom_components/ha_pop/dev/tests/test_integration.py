import asyncio
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from ha_fakes import FlowAbort, HAError, fakes, load_integration


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = patch.dict('sys.modules', fakes())
        self.context.start()
        self.addCleanup(self.context.stop)
        self.integration = load_integration()
        self.dashboard = importlib.import_module('ha_pop_test.dashboard')
        self.client = importlib.import_module('ha_pop_test.client')
        self.hass = SimpleNamespace(data={'lovelace': SimpleNamespace(dashboards={})}, panels={}, storage={}, modules=[], configured=set(), session=None)
        self.entry = SimpleNamespace(entry_id='entry1', unique_id='a' * 32, data={'name': 'Test Panel', 'host': 'panel.local', 'port': 8765, 'token': 't' * 48, 'camera': 'camera.test', 'dashboard_path': 'ha-pop-panel'})
        self.entry.runtime_data = self.integration.PanelRuntime(AsyncMock())
        self.entry.runtime_data.event_entity = SimpleNamespace(entity_id='event.test_doorbell', show_doorbell=Mock())

    async def test_dashboard_is_editable_and_edits_survive_reload(self):
        await self.dashboard.async_setup_dashboard(self.hass, self.entry)
        card = self.hass.storage['ha_pop_entry1']['views'][0]['cards'][0]
        self.assertEqual(card['entities']['doorbell_command'], 'event.test_doorbell')
        self.assertEqual(card['entities']['camera'], 'camera.test')
        edited = {'title': 'Edited in UI', 'views': []}
        await self.hass.data['lovelace'].dashboards['ha-pop-panel'].async_save(edited)
        self.dashboard.async_unload_dashboard(self.hass, self.entry)
        self.assertFalse(self.hass.panels)
        await self.dashboard.async_setup_dashboard(self.hass, self.entry)
        self.assertEqual(self.hass.storage['ha_pop_entry1'], edited)

    async def test_foreign_dashboard_is_never_overwritten_or_removed(self):
        foreign = object()
        self.hass.data['lovelace'].dashboards['ha-pop-panel'] = foreign
        with self.assertRaises(HAError):
            await self.dashboard.async_setup_dashboard(self.hass, self.entry)
        self.dashboard.async_unload_dashboard(self.hass, self.entry)
        self.assertIs(self.hass.data['lovelace'].dashboards['ha-pop-panel'], foreign)
        self.assertEqual(self.hass.storage, {})

    async def test_doorbell_is_emitted_only_after_successful_wake(self):
        runtime = self.entry.runtime_data
        await runtime.execute('doorbell')
        runtime.client.command.assert_awaited_once_with('doorbell')
        runtime.event_entity.show_doorbell.assert_called_once()
        runtime.client.command.side_effect = self.client.CannotConnect()
        with self.assertRaises(HAError):
            await runtime.execute('doorbell')
        runtime.event_entity.show_doorbell.assert_called_once()

    async def test_command_errors_distinguish_token_from_browser_failure(self):
        runtime = self.entry.runtime_data
        runtime.client.command.side_effect = self.client.InvalidAuth()
        with self.assertRaisesRegex(HAError, 'rejected its token'):
            await runtime.execute('doorbell')
        runtime.client.command.side_effect = self.client.CannotConnect('Restart the panel browser.')
        with self.assertRaisesRegex(HAError, 'Restart the panel browser'):
            await runtime.execute('doorbell')
        runtime.event_entity.show_doorbell.assert_not_called()

    async def test_parallel_commands_are_serialized(self):
        sequence = []
        async def command(name):
            sequence.append(name + ':start')
            await asyncio.sleep(0)
            sequence.append(name + ':end')
        runtime = self.entry.runtime_data
        runtime.client.command.side_effect = command
        await asyncio.gather(runtime.execute('wake'), runtime.execute('sleep'))
        self.assertEqual(sequence, ['wake:start', 'wake:end', 'sleep:start', 'sleep:end'])

    async def test_setup_retries_connection_failure_and_rolls_back_failed_dashboard(self):
        self.hass.config_entries = SimpleNamespace(async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True))
        client = AsyncMock()
        client.health.side_effect = self.client.CannotConnect()
        with patch.object(self.integration, 'PanelClient', return_value=client):
            with self.assertRaises(HAError):
                await self.integration.async_setup_entry(self.hass, self.entry)
        self.hass.config_entries.async_forward_entry_setups.assert_not_awaited()
        client.health.side_effect = None
        client.health.return_value = {'id': self.entry.unique_id}
        with patch.object(self.integration, 'PanelClient', return_value=client):
            with self.assertRaises(HAError):  # Entity platform double deliberately creates no command entity.
                await self.integration.async_setup_entry(self.hass, self.entry)
        self.hass.config_entries.async_unload_platforms.assert_awaited_once()

    async def test_flow_validates_before_creating_entry_and_handles_auth_errors(self):
        flow_module = importlib.import_module('ha_pop_test.config_flow')
        flow = flow_module.PanelConfigFlow()
        flow.hass = self.hass
        client = AsyncMock()
        client.health.return_value = {'id': self.entry.unique_id}
        with patch.object(flow_module, 'PanelClient', return_value=client):
            result = await flow.async_step_user(dict(self.entry.data))
            self.assertEqual(result['type'], 'create_entry')
            self.assertEqual(result['data']['camera'], 'camera.test')
            self.hass.configured.add(self.entry.unique_id)
            with self.assertRaises(FlowAbort):
                await flow.async_step_user(dict(self.entry.data))
            self.hass.configured.clear()
            client.health.side_effect = self.client.InvalidAuth()
            result = await flow.async_step_user(dict(self.entry.data))
            self.assertEqual(result['errors']['base'], 'invalid_auth')
            self.assertNotIn(self.entry.data['token'], str(result['data_schema']))

    async def test_flow_rejects_foreign_dashboard_and_wrong_device_reconfiguration(self):
        flow_module = importlib.import_module('ha_pop_test.config_flow')
        flow = flow_module.PanelConfigFlow()
        flow.hass, flow.entry = self.hass, self.entry
        client = AsyncMock()
        client.health.return_value = {'id': self.entry.unique_id}
        with patch.object(flow_module, 'PanelClient', return_value=client):
            self.hass.data['lovelace'].dashboards['ha-pop-panel'] = object()
            result = await flow.async_step_user(dict(self.entry.data))
            self.assertEqual(result['errors']['base'], 'dashboard_exists')
            client.health.return_value = {'id': 'b' * 32}
            result = await flow.async_step_reconfigure(dict(self.entry.data))
            self.assertEqual(result['reason'], 'wrong_device')
