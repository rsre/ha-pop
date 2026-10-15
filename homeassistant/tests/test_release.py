import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('build_release', Path(__file__).parents[1] / 'build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_release_contains_runtime_assets_and_excludes_private_snapshot_and_history(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            component, source = release.build(folder)
            with zipfile.ZipFile(component) as archive:
                paths = archive.namelist()
                self.assertTrue(all(p.startswith('custom_components/ha_pop/') for p in paths))
                self.assertIn('custom_components/ha_pop/frontend/ha-pop-panel.js', paths)
                self.assertIn('custom_components/ha_pop/blueprints/doorbell.yaml', paths)
                manifest = json.loads(archive.read('custom_components/ha_pop/manifest.json'))
                self.assertEqual(manifest['version'], '0.2.0')
            with zipfile.ZipFile(source) as archive:
                self.assertIn('panel/install.sh', archive.namelist())
                self.assertIn('hacs.json', archive.namelist())
                for name in archive.namelist():
                    self.assertNotIn('.local', Path(name).parts)
                    self.assertNotIn('.git', Path(name).parts)
                    self.assertNotIn('__pycache__', Path(name).parts)

    def test_release_guard_rejects_credentials_and_private_deployment_paths(self):
        for value in ['-----BEGIN ' + 'PRIVATE KEY-----', 'ghp_' + 'x' * 40, '/Users/' + 'private-person/project', '192.' + '168.99.123']:
            with self.assertRaises(ValueError):
                release.assert_public_data(value.encode())
        release.assert_public_data(b'http://panel.local:8765 /home/paneluser https://github.com/rsre/ha-pop')
