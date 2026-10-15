import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('install_remote', Path(__file__).parents[1] / 'tools/install_remote.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallRemoteTests(unittest.TestCase):
    def test_install_and_reinstall_preserve_unrelated_configuration_and_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / 'configuration.yaml'
            secrets = root / 'secrets.yaml'
            config.write_text('# retain comment\nhomeassistant:\n  allowlist_external_dirs:\n    - /config\nscript: !include scripts.yaml\nautomation: !include automations.yaml\n')
            secrets.write_text('existing_password: unchanged\n')
            for token in ['a' * 48, 'b' * 48]:
                with patch('sys.stdin', io.StringIO(token)), patch('sys.stdout', io.StringIO()):
                    installer.install(root)
            updated = config.read_text()
            self.assertEqual(updated.count('ha_pop: !include ha-pop/remote.yaml'), 1)
            self.assertIn('# retain comment\n', updated)
            self.assertIn('  allowlist_external_dirs:\n    - /config\n', updated)
            self.assertIn('script: !include scripts.yaml', updated)
            self.assertEqual(secrets.read_text().count('ha_panel_authorization:'), 1)
            self.assertIn('existing_password: unchanged', secrets.read_text())
            self.assertIn('Bearer ' + 'b' * 48, secrets.read_text())
            self.assertEqual(secrets.stat().st_mode & 0o777, 0o600)
            backups = list((root / 'ha-pop-backups').iterdir())
            self.assertEqual(len(backups), 2)
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o700 for p in backups))
            self.assertTrue((root / 'ha-pop/remote.yaml').exists())

    def test_existing_packages_require_manual_merge_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / 'configuration.yaml'
            original = 'homeassistant:\n  packages: !include_dir_named packages\nscript: !include scripts.yaml\nautomation: !include automations.yaml\n'
            config.write_text(original)
            with patch('sys.stdin', io.StringIO('a' * 48)):
                with self.assertRaisesRegex(RuntimeError, 'Merge ha_pop'):
                    installer.install(root)
            self.assertEqual(config.read_text(), original)
            self.assertFalse((root / 'secrets.yaml').exists())

    def test_invalid_credential_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('sys.stdin', io.StringIO('bad\ncredential')):
                with self.assertRaises(ValueError):
                    installer.install(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_migration_preserves_legacy_scripts_and_existing_ui_edits(self):
        existing = '# UI edited\nha_panel_wake:\n  alias: My wake\n  sequence: []\nother:\n  sequence: []\n'
        defaults = 'ha_panel_wake:\n  alias: Default wake\nha_panel_doorbell:\n  alias: Default doorbell\nha_panel_sleep:\n  alias: Sleep\n'
        legacy = 'rest_command:\n  wake:\n    headers: !secret authorization\nscript:\n  ha_panel_wake:\n    alias: Legacy wake\n  ha_panel_doorbell:\n    alias: Custom doorbell\n    secret: !secret preserved\n'
        result = installer.merge_scripts(existing, defaults, legacy)
        self.assertTrue(result.startswith(existing))
        self.assertIn('Custom doorbell', result)
        self.assertIn('!secret', result)
        self.assertNotIn('Default wake', result)
        self.assertIn('ha_panel_sleep:', result)
        self.assertEqual(installer.merge_scripts(result, defaults, ''), result)

    def test_empty_scripts_placeholder_is_replaced_with_mapping(self):
        result = installer.merge_scripts('{}\n', 'ha_panel_sleep:\n  sequence: []\n', '')
        self.assertEqual(list(installer.mapping(result)), ['ha_panel_sleep'])

    def test_automation_migration_preserves_legacy_definition_and_ui_edits(self):
        defaults = '- id: panel\n  alias: Default\n  actions: []\n'
        legacy = 'automation:\n  - id: panel\n    alias: Custom legacy\n    actions: []\n'
        existing = '# keep comment\n- id: other\n  alias: Unrelated\n  actions: []\n'
        result = installer.merge_automations(existing, defaults, legacy)
        self.assertTrue(result.startswith(existing))
        self.assertIn('Custom legacy', result)
        self.assertEqual(len(installer.yaml.safe_load(result)), 2)
        edited = result.replace('Custom legacy', 'Edited in UI')
        self.assertEqual(installer.merge_automations(edited, defaults, legacy), edited)

    def test_empty_automation_file_and_missing_id(self):
        defaults = '- id: panel\n  actions: []\n'
        result = installer.merge_automations('[]\n', defaults, '')
        self.assertEqual(installer.yaml.safe_load(result)[0]['id'], 'panel')
        with self.assertRaisesRegex(RuntimeError, 'stable IDs'):
            installer.merge_automations('', '- alias: Missing ID\n', '')


if __name__ == '__main__':
    unittest.main()
