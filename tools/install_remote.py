"""Stage the Home Assistant package; read the Pi token from standard input.

Run inside the SSH add-on. Check configuration before reloading actions or restarting Core.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

import yaml


def mapping(text):
    node = yaml.compose(text)
    if node is None or node.tag == 'tag:yaml.org,2002:null':
        return {}
    if not isinstance(node, yaml.MappingNode):
        raise RuntimeError('Expected a YAML mapping')
    return {key.value: value for key, value in node.value}


def merge_scripts(existing, defaults, legacy_package):
    """Append missing panel scripts; preserve existing UI edits and YAML tags."""
    current = mapping(existing)
    legacy = mapping(legacy_package).get('script')
    previous = {k.value: v for k, v in legacy.value} if isinstance(legacy, yaml.MappingNode) else {}
    additions = []
    for key, value in mapping(defaults).items():
        if key not in current:
            additions.append((yaml.ScalarNode('tag:yaml.org,2002:str', key), previous.get(key, value)))
    if not additions:
        return existing
    # An empty scripts.yaml may contain the placeholder {} or null.
    prefix = existing.rstrip() + '\n' if current else ''
    return prefix + yaml.serialize(yaml.MappingNode('tag:yaml.org,2002:map', additions))


def merge_automations(existing, defaults, legacy_package):
    """Migrate by stable ID, preserving existing UI edits and unrelated YAML."""
    def sequence(node):
        if node is None or node.tag == 'tag:yaml.org,2002:null':
            return []
        if not isinstance(node, yaml.SequenceNode):
            raise RuntimeError('Expected an automation list')
        return node.value

    def identifier(node):
        if not isinstance(node, yaml.MappingNode):
            raise RuntimeError('Expected an automation mapping')
        return next((value.value for key, value in node.value if key.value == 'id'), None)

    current = sequence(yaml.compose(existing))
    ids = {identifier(node) for node in current}
    legacy = sequence(mapping(legacy_package).get('automation'))
    previous = {identifier(node): node for node in legacy}
    additions = []
    for node in sequence(yaml.compose(defaults)):
        key = identifier(node)
        if not key:
            raise RuntimeError('Panel automations require stable IDs for UI editing')
        if key not in ids:
            additions.append(previous.get(key, node))
            ids.add(key)
    if not additions:
        return existing
    prefix = existing.rstrip() + '\n' if current else ''
    return prefix + yaml.serialize(yaml.SequenceNode('tag:yaml.org,2002:seq', additions))


def install(config_dir=Path('/config')):
    token = sys.stdin.read().strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise ValueError('Expected a generated panel token on standard input')
    source = Path(__file__).resolve().parents[1] / 'homeassistant/remote.yaml'
    config = config_dir / 'configuration.yaml'
    secrets = config_dir / 'secrets.yaml'
    target = config_dir / 'ha-pop/remote.yaml'
    text = config.read_text()
    if not re.search(r'^script: !include scripts\.yaml\s*$', text, re.MULTILINE):
        raise RuntimeError('Expected script: !include scripts.yaml for UI-editable scripts')
    scripts = config_dir / 'scripts.yaml'
    scripts_text = merge_scripts(
        scripts.read_text() if scripts.exists() else '',
        source.with_name('scripts.yaml').read_text(),
        target.read_text() if target.exists() else '',
    )
    if not re.search(r'^automation: !include automations\.yaml\s*$', text, re.MULTILINE):
        raise RuntimeError('Expected automation: !include automations.yaml for UI editing')
    automations = config_dir / 'automations.yaml'
    automations_text = merge_automations(
        automations.read_text() if automations.exists() else '',
        source.with_name('automations.yaml').read_text(),
        target.read_text() if target.exists() else '',
    )
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
    for item in [config, secrets, target, scripts, automations]:
        if item.exists():
            shutil.copy2(item, backup / item.name)
        else:
            with (backup / 'previously-absent').open('a') as record:
                record.write(str(item.relative_to(config_dir)) + '\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    scripts.write_text(scripts_text)
    automations.write_text(automations_text)
    secrets.write_text(secret_text)
    secrets.chmod(0o600)
    config.write_text(text)
    print(f'Remote panel package staged. Backup: {backup}')
    print('Validate configuration before reloading actions or restarting Home Assistant.')


if __name__ == '__main__':
    install()
