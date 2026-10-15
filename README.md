# HA Pop Panel

A Raspberry Pi 7-inch touchscreen display at 720 × 1280 project for Home Assistant: a portrait dashboard, large touch targets, camera popups, guarded tap-to-wake, and remote wake/sleep controls.

| Directory | Purpose |
| --- | --- |
| [`panel/`](panel/README.md) | Pi launcher, keyboard, sleep guard, remote endpoint, and installer |
| [`custom_components/ha_pop/`](custom_components/ha_pop/README.md) | Home Assistant integration, frontend, guides, and development tools |

1. Install the [Pi software](panel/README.md).
2. Add this repository to HACS as an Integration, download HA Pop Panel, and restart Home Assistant.
3. Add **HA Pop Panel** under Settings → Devices & services. Enter the panel address and shared token, choose the camera, and choose an unused dashboard URL.
4. Use the integration's Wake, Sleep, and Show doorbell buttons in automations.

[CHANGELOG.md](CHANGELOG.md) records changes.

## Development checks

```sh
python3 -m pip install -r custom_components/ha_pop/dev/requirements-dev.txt
python3 -m unittest discover -s panel/tests
python3 -m unittest discover -s custom_components/ha_pop/dev/tests
node --test custom_components/ha_pop/dev/tests/panel.test.cjs
```
