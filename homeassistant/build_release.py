"""Build an integration ZIP and a source export without private files/history."""
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/ha_pop'


def assert_public_data(data):
    patterns = [
        rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----',
        rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
        rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
        rb'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
        rb'/Users/(?!example(?:/|\b))[A-Za-z0-9_.-]+',
        rb'/home/(?!(?:paneluser|example)(?:/|\b))[A-Za-z0-9_.-]+',
    ]
    if any(re.search(pattern, data) for pattern in patterns):
        raise ValueError('Possible credential or personal deployment data in release source')


def build(output=None):
    output = Path(output) if output else ROOT / 'dist'
    output.mkdir(parents=True, exist_ok=True)
    version = json.loads((COMPONENT / 'manifest.json').read_text())['version']
    component_zip = output / f'ha-pop-{version}.zip'
    source_zip = output / f'ha-pop-public-source-{version}.zip'
    excludes = {'__pycache__', '.git', '.local', '.venv', 'dist', '.env', '.DS_Store', 'secrets.yaml', 'remote-token', 'remote-id'}
    def add(archive, path):
        if path.is_file() and not path.is_symlink() and not any(part in excludes for part in path.relative_to(ROOT).parts) and path.suffix not in ('.pyc', '.key', '.pem', '.p12'):
            if path.suffix == '.png' and 'brand' not in path.parts:
                return
            if path.suffix != '.png':
                assert_public_data(path.read_bytes())
            archive.write(path, path.relative_to(ROOT))
    with zipfile.ZipFile(component_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(COMPONENT.rglob('*')):
            add(archive, path)
    with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        # Explicit source roots prevent ignored credentials or local snapshots from being exported.
        for name in ['panel', 'custom_components', 'homeassistant', '.github']:
            for path in sorted((ROOT / name).rglob('*')):
                add(archive, path)
        for name in ['README.md', 'CHANGELOG.md', 'PUBLICATION.md', 'hacs.json', '.gitignore', '.gitattributes']:
            add(archive, ROOT / name)
    print(component_zip)
    print(source_zip)
    return component_zip, source_zip


if __name__ == '__main__':
    build()
