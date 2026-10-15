import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[4]


class VersionTests(unittest.TestCase):
    def test_integration_panel_and_frontend_versions_match(self):
        versions = {
            'const': re.search(r"VERSION = '([0-9.]+)'", (ROOT / 'custom_components/ha_pop/const.py').read_text()).group(1),
            'manifest': json.loads((ROOT / 'custom_components/ha_pop/manifest.json').read_text())['version'],
            'panel': re.search(r"VERSION = '([0-9.]+)'", (ROOT / 'panel/ha-panel-remote.py').read_text()).group(1),
            'frontend': re.search(r'HA_POP_VERSION = "([0-9.]+)"', (ROOT / 'custom_components/ha_pop/frontend/ha-pop-panel-card.js').read_text()).group(1),
        }
        self.assertEqual(len(set(versions.values())), 1, versions)


if __name__ == '__main__':
    unittest.main()
