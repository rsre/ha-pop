"""Install the panel through Home Assistant's authenticated WebSocket API.

Run inside the SSH add-on with SUPERVISOR_TOKEN available. Requires PyYAML and
websocket-client; the client can be supplied via a temporary PYTHONPATH.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil

import websocket
import yaml


class HomeAssistantAPI:
    def __init__(self):
        token = os.environ["SUPERVISOR_TOKEN"]
        self.socket = websocket.create_connection(
            "ws://supervisor/core/websocket",
            header={"Authorization": f"Bearer {token}"},
            suppress_origin=True,
            timeout=20,
        )
        if json.loads(self.socket.recv()).get("type") != "auth_required":
            raise RuntimeError("Unexpected management API handshake")
        self.socket.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(self.socket.recv()).get("type") != "auth_ok":
            raise RuntimeError("Home Assistant API authentication failed")
        self.sequence = 0

    def call(self, command, **fields):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "type": command, **fields}))
        while True:
            reply = json.loads(self.socket.recv())
            if reply.get("id") != self.sequence:
                continue
            if not reply.get("success"):
                raise RuntimeError(f"{command}: {reply.get('error', {}).get('code', 'failed')}")
            return reply.get("result")


def install(config_dir: Path, url_path: str):
    root = Path(__file__).resolve().parents[1]
    source = root / "frontend/ha-pop-panel.js"
    dashboard = yaml.safe_load((root / "dashboards/example-panel.yaml").read_text())
    version = re.search(r'const HA_POP_VERSION = "([0-9.]+)";', source.read_text())[1]
    asset_url = f"/local/ha-pop/ha-pop-panel.js?v={version}"
    api = HomeAssistantAPI()
    try:
        dashboards = api.call("lovelace/dashboards/list")
        resources = api.call("lovelace/resources")
        existing = next((d for d in dashboards if d["url_path"] == url_path), None)
        if existing and existing["mode"] != "storage":
            raise RuntimeError("The requested URL belongs to a YAML dashboard")
        backup = config_dir / "ha-pop-backups" / datetime.now().strftime("%Y%m%dT%H%M%S-%f")
        backup.mkdir(parents=True, mode=0o700)
        (backup / "registrations.json").write_text(json.dumps({"dashboards": dashboards, "resources": resources}, indent=2))
        if existing:
            try:
                original = api.call("lovelace/config", url_path=url_path)
            except RuntimeError as error:
                if "config_not_found" not in str(error):
                    raise
                original = None
            (backup / "dashboard.json").write_text(json.dumps(original, indent=2))

        target = config_dir / "www/ha-pop/ha-pop-panel.js"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup / "ha-pop-panel.js")
        temporary = target.with_suffix(".js.new")
        shutil.copyfile(source, temporary)
        temporary.chmod(0o644)
        temporary.replace(target)

        resource = next((r for r in resources if r["url"].split("?", 1)[0] == "/local/ha-pop/ha-pop-panel.js"), None)
        if resource:
            api.call("lovelace/resources/update", resource_id=resource["id"], url=asset_url, res_type="module")
        else:
            api.call("lovelace/resources/create", url=asset_url, res_type="module")
        if not existing:
            api.call(
                "lovelace/dashboards/create", url_path=url_path, title="Panel",
                icon="mdi:tablet-dashboard", show_in_sidebar=True,
                require_admin=False, mode="storage",
            )
        api.call("lovelace/config/save", url_path=url_path, config=dashboard)
        if api.call("lovelace/config", url_path=url_path) != dashboard:
            raise RuntimeError("Saved dashboard does not match its source")
        print(f"Installed panel {version}: /{url_path}/casa")
        print(f"Resource: {asset_url}")
        print(f"Backup: {backup}")
    finally:
        api.socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=Path("/config"))
    parser.add_argument("--url-path", default="dashboard-panel")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", args.url_path):
        parser.error("Dashboard URL must contain lowercase words separated by hyphens")
    install(args.config_dir, args.url_path)
