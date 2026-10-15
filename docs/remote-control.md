# Wake and doorbell commands from Home Assistant

Three UI-editable scripts are available for automations and dashboard buttons:

```yaml
# Wake the panel without changing its current view.
action: script.ha_panel_wake
```

```yaml
# Wake the panel and open the Portón video/talk popup.
action: script.ha_panel_doorbell
```

```yaml
# Sleep now and cancel any active wake hold; tap-to-wake remains enabled.
action: script.ha_panel_sleep
```

The scripts live in Home Assistant's `/config/scripts.yaml`, so they can be edited through the UI. Defaults are in [`homeassistant/scripts.yaml`](../homeassistant/scripts.yaml). Reinstallation preserves existing scripts and UI edits.

The installer also adds “Show doorbell on wall panel” to `/config/automations.yaml`, with the stable ID `ha_pop_show_doorbell_on_panel`, so it can be edited through the UI. It triggers on the `ring` event from `event.doorbell` and is independent of the existing Android TV automation. Defaults are in [`homeassistant/automations.yaml`](../homeassistant/automations.yaml); reinstalling preserves existing UI edits. The package, [`homeassistant/remote.yaml`](../homeassistant/remote.yaml), contains only REST commands and the popup helper.

## Behavior

The Pi accepts authenticated `POST /wake` and `POST /sleep` commands on `192.0.2.10:8765`. Waking pauses the idle service, removes the touch guard, and powers on `DSI-1` without sending a click or restarting Chromium. It holds the screen awake for at least five minutes; another command restarts that hold. At the end it resumes normal idle handling, so the screen can remain on for an additional idle interval. Touch wake remains guarded when idle sleep resumes.

Sleeping cancels the wake hold, resumes idle handling, and waits for the input guard to turn the display off. No browser restart or simulated touch is used.

After waking successfully, the doorbell script presses `input_button.ha_panel_doorbell`. The panel watches this helper through its existing Home Assistant connection and opens its VideoLink popup. The browser remains logged in. Talk still requires the user's explicit interaction. Repeated rings leave an already-open camera stream intact. The popup stays open until dismissed; normal screen sleep resumes after the wake hold. A wake-only command preserves the current popup.

The dashboard needs to be loaded and connected to receive popup commands. Initial helper state and commands older than 30 seconds are ignored to avoid replaying old rings after browser startup or a network outage. The `doorbell_command` entity mapping identifies the helper in the dashboard YAML.

## Installation and update

Install guarded sleep first. Copy `kiosk` to the Pi, then run as `paneluser`:

```sh
bash kiosk/install-remote.sh
```

This creates a random shared token at `~/.config/ha-panel/remote-token` with mode 600, installs the Python service, and adds its labwc startup hook. Reinstalling preserves the token. No extra Python packages or root privileges are required.

Deploy the frontend and dashboard using the [dashboard guide](dashboard.md). Transfer `tools/install_remote.py` and the `homeassistant` directory to the SSH add-on, retaining their repository paths, for example:

```sh
tar -cf - tools/install_remote.py homeassistant |
  ssh homeassistant-local 'mkdir -p /tmp/ha-pop-deploy/payload; tar -xf - -C /tmp/ha-pop-deploy/payload'
ssh -i ~/.ssh/homeassistant paneluser@192.0.2.10 'cat ~/.config/ha-panel/remote-token' |
  ssh homeassistant-local 'python3 /tmp/ha-pop-deploy/payload/tools/install_remote.py'
ssh homeassistant-local 'ha core check'
```

The installer backs up configuration and secrets under `/config/ha-pop-backups/remote-*`, adds the package include beneath `homeassistant.packages.ha_pop`, and places authorization in `/config/secrets.yaml`. It also merges missing panel scripts into `/config/scripts.yaml` and the doorbell automation into `/config/automations.yaml`, preserving existing UI edits and unrelated settings. The installer backs up both UI files and can migrate definitions from an existing package. The installer requires PyYAML, already present in the SSH add-on. An existing packages layout that does not match its managed include requires a manual merge. Check configuration before the initial Core restart:

```sh
ssh homeassistant-local 'ha core restart'
```

Home Assistant's [REST command documentation](https://www.home-assistant.io/integrations/rest_command/) covers this action and its response. The [input button documentation](https://www.home-assistant.io/integrations/input_button/) describes the timestamp used to deliver the popup command.

The bearer token is sent over HTTP on the local network. Keep port 8765 private to the trusted LAN; do not forward it through the router. The endpoint binds the Pi's configured address and exposes only waking and sleeping, with no arbitrary command execution or browser debugging. Update its address and the package URL together if the Pi's IP changes. No token is stored in the repository or dashboard JavaScript.

## Recovery

Run on the Pi:

```sh
systemctl --user status ha-panel-remote --no-pager
systemctl --user restart ha-panel-remote
```

Stopping the remote service resumes normal idle handling, including when its process fails. To remove it permanently, remove its labwc startup line and stop the service. Disable or delete the ring automation in the UI and remove the panel scripts if no longer needed. Remove `homeassistant.packages.ha_pop` to stop loading the HA package, then check configuration and restart Core. Restore backed-up files if needed; their secrets must remain private.

## Checks

Unit tests cover authenticated requests, rejection of other endpoints and incorrect credentials, timed idle restoration, repeated wake holds, failure recovery, and fresh versus stale/repeated popup commands:

```sh
node --test tests/panel.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

For updates to an existing installation, validate configuration, then reload the affected REST commands, scripts, and automations from Home Assistant. An initial installation of the package requires the Core restart shown above.

Specific deployment backups and verification results are recorded in the [changelog](../CHANGELOG.md).
