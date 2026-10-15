import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class InstallTests(unittest.TestCase):
    def test_missing_keyboard_fails_before_installing_services(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(['bash', str(Path(__file__).parents[1] / 'install.sh'), 'https://example.test/', str(Path(folder) / 'missing')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('compiled overlay Squeekboard', result.stderr)

    def test_standalone_installer_reuses_keyboard_without_copying_it_onto_itself(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            home = root / 'home'
            source = root / 'panel'
            source.mkdir()
            shutil.copyfile(Path(__file__).parents[1] / 'install.sh', source / 'install.sh')
            keyboard = home / '.local/lib/ha-panel/squeekboard'
            keyboard.parent.mkdir(parents=True)
            keyboard.write_text('patched keyboard fixture')
            keyboard.chmod(0o755)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            for name in ['chromium', 'curl', 'labwc', 'systemctl', 'swayidle', 'wlopm', 'python3', 'gsettings']:
                stub = bin_dir / name
                stub.write_text('#!/bin/sh\nexit 0\n')
                stub.chmod(0o755)
            log = root / 'installed'
            for name in ['kiosk', 'keyboard', 'idle', 'remote']:
                body = '#!/bin/bash\nset -eu\n'
                if name == 'keyboard':
                    body += 'test "$1" != "$HOME/.local/lib/ha-panel/squeekboard"\ncmp "$1" "$HOME/.local/lib/ha-panel/squeekboard"\nprintf "%s" "$1" > "$KEYBOARD_COPY"\n'
                body += f'printf "{name}\\n" >> "$INSTALL_LOG"\n'
                (source / f'install-{name}.sh').write_text(body)
            copied = root / 'copied'
            env = {**os.environ, 'HOME': str(home), 'PATH': f'{bin_dir}:/usr/bin:/bin', 'INSTALL_LOG': str(log), 'KEYBOARD_COPY': str(copied)}
            subprocess.run(['bash', str(source / 'install.sh'), 'https://example.test/'], env=env, check=True, capture_output=True)
            self.assertEqual(log.read_text().splitlines(), ['kiosk', 'keyboard', 'idle', 'remote'])
            self.assertFalse(Path(copied.read_text()).exists())
            self.assertEqual(keyboard.read_text(), 'patched keyboard fixture')
