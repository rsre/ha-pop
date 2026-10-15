# HA Pop Panel

A pre-beta Raspberry Pi touchscreen project for Home Assistant: a portrait dashboard, large touch targets, camera popups, guarded tap-to-wake, and remote wake/sleep controls.

| Directory | Purpose |
| --- | --- |
| [`panel/`](panel/README.md) | Pi launcher, keyboard, sleep guard, remote endpoint, and installer |
| [`custom_components/ha_pop/`](custom_components/ha_pop/README.md) | Home Assistant integration, frontend, guides, and development tools |

The integration is at the repository root under `custom_components/` to follow the [HACS integration layout](https://www.hacs.xyz/docs/publish/integration/). Its guides are in `README.md` and `docs/`; tests and development dependencies are in `dev/`. Pi software remains separate.

1. Install the [Pi software](panel/README.md).
2. Add this repository to HACS as an Integration, download HA Pop Panel, and restart Home Assistant.
3. Add **HA Pop Panel** under Settings → Devices & services. Enter the panel address and shared token, choose the camera, and choose an unused dashboard URL.
4. Use the integration's Wake, Sleep, and Show doorbell buttons in automations.

No SSH access to Home Assistant, Supervisor token, YAML package editing, or Python dependency installation is needed for the integration. Setup uses the Pi's authenticated health endpoint without waking the display.

The default dashboard targets a 7-inch display at 720 × 1280 and uses example entity IDs. Choose real controls through the dashboard UI. Camera video uses Home Assistant's native card; an installed VideoLink card supplies talk controls automatically.

[CHANGELOG.md](CHANGELOG.md) records changes.

## Development checks

```sh
python3 -m pip install -r custom_components/ha_pop/dev/requirements-dev.txt
python3 -m unittest discover -s panel/tests
python3 -m unittest discover -s custom_components/ha_pop/dev/tests
node --test custom_components/ha_pop/dev/tests/panel.test.cjs
```
