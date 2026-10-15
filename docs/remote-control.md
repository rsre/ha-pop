# Wake and doorbell commands from Home Assistant

Two scripts are available for automations and dashboard buttons:

```yaml
# Wake the panel without changing its current view.
action: script.ha_panel_wake
```

```yaml
# Wake the panel and open the Portón video/talk popup.
action: script.ha_panel_doorbell
```

The package also installs “Show doorbell on wall panel”, triggered by the `ring` event from `event.doorbell`. It is independent of the existing Android TV automation. The package source is [`homeassistant/remote.yaml`](../homeassistant/remote.yaml).

## Behavior

The Pi accepts an authenticated `POST /wake` on `192.0.2.10:8765`. It pauses the idle service, removes the touch guard, and powers on `DSI-1` without sending a click or restarting Chromium. It holds the screen awake for at least five minutes; another command restarts that hold. At the end it resumes normal idle handling. Touch wake remains guarded when idle sleep resumes.

After waking successfully, the doorbell script presses `input_button.ha_panel_doorbell`. The panel watches this helper through its existing Home Assistant connection and opens its VideoLink popup. The browser remains logged in. Talk still requires the user's explicit interaction. Repeated rings leave an already-open camera stream intact. The popup stays open until dismissed; normal screen sleep resumes after the wake hold. A wake-only command preserves the current popup.

The dashboard needs to be loaded and connected to receive popup commands. Initial helper state and commands older than 30 seconds are ignored to avoid replaying old rings after browser startup or a network outage. The `doorbell_command` entity mapping identifies the helper in the dashboard YAML.

## Installation and update

Install guarded sleep first. Copy `kiosk` to the Pi, then run as `paneluser`:

```sh
bash kiosk/install-remote.sh
```

This creates a random shared token at `~/.config/ha-panel/remote-token` with mode 600, installs the Python service, and adds its labwc startup hook. Reinstalling preserves the token. No extra Python packages or root privileges are required.

Deploy the frontend and dashboard using the [dashboard guide](dashboard.md). Transfer `tools/install_remote.py` and `homeassistant/remote.yaml` to the SSH add-on, retaining their repository paths, for example:

```sh
tar -cf - tools/install_remote.py homeassistant |
  ssh homeassistant-local 'mkdir -p /tmp/ha-pop-deploy/payload; tar -xf - -C /tmp/ha-pop-deploy/payload'
ssh -i ~/.ssh/homeassistant paneluser@192.0.2.10 'cat ~/.config/ha-panel/remote-token' |
  ssh homeassistant-local 'python3 /tmp/ha-pop-deploy/payload/tools/install_remote.py'
ssh homeassistant-local 'ha core check'
```

The installer backs up configuration and secrets under `/config/ha-pop-backups/remote-*`, adds the package include beneath `homeassistant.packages.ha_pop`, and places authorization in `/config/secrets.yaml`. It preserves unrelated settings. An existing packages layout that does not match its managed include requires a manual merge. Check configuration before the initial Core restart:

```sh
ssh homeassistant-local 'ha core restart'
```

Home Assistant's [REST command documentation](https://www.home-assistant.io/integrations/rest_command/) covers this action and its response. The [input button documentation](https://www.home-assistant.io/integrations/input_button/) describes the timestamp used to deliver the popup command.

The bearer token is sent over HTTP on the local network. Keep port 8765 private to the trusted LAN; do not forward it through the router. The endpoint binds the Pi's configured address and exposes only waking, with no arbitrary command execution or browser debugging. Update its address and the package URL together if the Pi's IP changes. No token is stored in the repository or dashboard JavaScript.

## Recovery

Run on the Pi:

```sh
systemctl --user status ha-panel-remote --no-pager
systemctl --user restart ha-panel-remote
```

Stopping the remote service resumes normal idle handling, including when its process fails. To remove it permanently, remove its labwc startup line and stop the service. Disable the ring automation and remove `homeassistant.packages.ha_pop` to stop loading the HA package, then check configuration and restart Core. Restore backed-up files if needed; their secrets must remain private.

## Verification

Unit tests cover authenticated requests, rejection of other endpoints and incorrect credentials, timed idle restoration, repeated wake holds, failure recovery, and fresh versus stale/repeated popup commands:

```sh
node --test tests/panel.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

On 2026-10-15, Home Assistant configuration validation passed and Core restarted successfully. Both scripts, the helper, and the enabled ring automation appeared in the live API. Unauthenticated wake requests returned HTTP 401.

Running the installed automation's actions while the guarded screen was asleep powered on `DSI-1`, removed the guard, and opened a `videolink-doorbell` card with no error card. Its video reached ready state 4, played at 640 × 480, and reported its stream ready. Chromium retained the same document identity. A repeated doorbell command preserved the exact video card instance; a subsequent wake-only command also retained the popup and stream. No physical doorbell event was emitted during testing, so the existing TV automation was not triggered.

The portrait layout checks also passed on version 0.1.2: 720 × 1280 with no page overflow, all 12 main touch targets inside the screen, and all seven popups fitting without scroll or error cards.

Deployment backups:

- Pi remote service: `/home/paneluser/.local/state/ha-panel/backups/remote-20261015T144242-181858`.
- HA package/configuration/secrets: `/config/ha-pop-backups/remote-20261015T144244-217315`.
- Frontend and dashboard: `/config/ha-pop-backups/20261015T144243-773961`.

The full five-minute wake hold expired and automatically restarted the idle service with the remote process still healthy. Starting guarded sleep then powered `DSI-1` off; another doorbell command woke it and displayed the camera again under normal kiosk startup. Temporary browser diagnostics were removed and their port verified closed.

The hold delays the start of normal idle handling: the screen can remain on for another idle interval afterward. A physical ring and a Pi reboot after installing remote control have not been tested.
