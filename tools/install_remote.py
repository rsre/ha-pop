"""Stage the Home Assistant package; read the Pi token from standard input.

Run inside the SSH add-on. Check configuration and restart Core separately.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys


def install(config_dir=Path('/config')):
    token = sys.stdin.read().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise ValueError('Expected a generated panel token on standard input')
    source = Path(__file__).resolve().parents[1] / 'homeassistant/remote.yaml'
    config = config_dir / 'configuration.yaml'
    secrets = config_dir / 'secrets.yaml'
    target = config_dir / 'ha-pop/remote.yaml'
    text = config.read_text()
    include = '    ha_pop: !include ha-pop/remote.yaml'
    if include not in text:
        if len(re.findall(r'^homeassistant:\s*$', text, re.MULTILINE)) != 1:
            raise RuntimeError('Expected one existing homeassistant configuration block')
        # Refuse ambiguous layouts rather than adding a duplicate packages key.
        block = re.search(r'^homeassistant:\s*\n((?:[ \t].*\n|\n)*)', text, re.MULTILINE)
        if not block or re.search(r'^  packages:', block[1], re.MULTILINE):
            raise RuntimeError('Merge ha_pop into the existing packages configuration manually')
        text = re.sub(r'^homeassistant:\s*$', 'homeassistant:\n  packages:\n' + include, text, count=1, flags=re.MULTILINE)
    secret_text = secrets.read_text() if secrets.exists() else ''
    secret_line = f'ha_panel_authorization: "Bearer {token}"'
    if re.search(r'^ha_panel_authorization:', secret_text, re.MULTILINE):
        secret_text = re.sub(r'^ha_panel_authorization:.*$', secret_line, secret_text, flags=re.MULTILINE)
    else:
        secret_text = secret_text.rstrip() + '\n' + secret_line + '\n'
    backup = config_dir / 'ha-pop-backups' / datetime.now().strftime('remote-%Y%m%dT%H%M%S-%f')
    backup.mkdir(parents=True, mode=0o700)
    for item in [config, secrets, target]:
        if item.exists():
            shutil.copy2(item, backup / item.name)
        else:
            with (backup / 'previously-absent').open('a') as record:
                record.write(str(item.relative_to(config_dir)) + '\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    secrets.write_text(secret_text)
    secrets.chmod(0o600)
    config.write_text(text)
    print(f'Remote panel package staged. Backup: {backup}')
    print('Validate configuration before restarting Home Assistant.')


if __name__ == '__main__':
    install()
