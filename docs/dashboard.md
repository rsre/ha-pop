# Portrait touchscreen dashboard

The installed dashboard is [Panel](https://homeassistant.example/dashboard-panel/casa). The Pi's kiosk URL points directly to it.

The layout targets the mounted 7-inch screen at **720 × 1280**, including Home Assistant's 56-pixel toolbar. The main card uses the remaining 1224 pixels. Its sections have fixed row allocations and explicit typography so inherited theme line heights cannot push controls into the next section.

## Main screen

| Section | Interaction |
| --- | --- |
| Portón | Snapshot preview; tap to open the full VideoLink stream and talk controls |
| Cocina | Direct controls for both lights; coffee status opens its controls and schedule |
| Nave y exterior | Direct controls for nave lights, spotlight, and exterior light |
| Sala de máquinas | Heating, hot-water setpoint, washer, and dryer summaries open details |
| Robot | Vacuum state and available battery level; tap for start/pause and return-home controls |

The snapshot refreshes every 30 seconds. Continuous video and audio are created only inside the camera popup and released on close. Camera video uses `contain` to preserve the full image. The dashboard uses the existing VideoLink frontend; it does not require Browser Mod, Mushroom, or another popup integration.

Popups close with their large close button, Escape, or a tap outside. Focus returns to the triggering control. Native Home Assistant detail dialogs can take over after the panel's own dialog closes. Missing or unavailable light entities, offline connections, and pending commands disable their controls. Errors appear in the footer. Opening a popup does not operate the device; service calls require interaction with its controls.

Home Assistant can also [wake the screen and open the camera popup](remote-control.md) through the doorbell command helper.

The hot-water popup displays the existing `sensor.hot_water_setpoint`; this sensor is read-only. The dashboard does not invent a writable temperature control that the existing setup lacks.

## Source and installation

- [`frontend/ha-pop-panel.js`](../frontend/ha-pop-panel.js): custom Home Assistant card, version **0.1.2**.
- [`dashboards/example-panel.yaml`](../dashboards/example-panel.yaml): dashboard source and entity mappings.
- [`tools/install_dashboard.py`](../tools/install_dashboard.py): authenticated management API installer.

Installed server files and registrations:

| Item | Location |
| --- | --- |
| SSH access | `homeassistant-local` |
| Frontend file | `/config/www/ha-pop/ha-pop-panel.js` |
| JavaScript module resource | `/local/ha-pop/ha-pop-panel.js?v=0.1.2` |
| Storage dashboard | `dashboard-panel`, titled “Panel”, visible to regular users |
| Dashboard URL | `/dashboard-panel/casa` |

The installer copies the frontend atomically, registers its resource through the WebSocket API, creates the dashboard if absent, saves its configuration, and reads it back to verify equality. It backs up existing registrations, configuration, and frontend before changes. It does not edit `.storage` files or `configuration.yaml` directly and requires no Core restart. The installer uses the SSH add-on's Supervisor authentication; no credentials are stored in this repository.

## Update

Edit the JavaScript and YAML here. Bump `HA_POP_VERSION` when changing JavaScript, then run:

```sh
node --check frontend/ha-pop-panel.js
node --test tests/panel.test.cjs
git diff --check
```

The installer requires PyYAML and `websocket-client`. The SSH add-on provides PyYAML; make the pure-Python WebSocket client available in `/tmp/ha-pop-deploy` via `PYTHONPATH`. This dependency is used only for installation, not by the running dashboard:

```sh
ssh -i ~/.ssh/homeassistant paneluser@192.0.2.10 'tar -cf - -C /usr/lib/python3/dist-packages websocket' |
  ssh homeassistant-local 'mkdir -p /tmp/ha-pop-deploy; tar -xf - -C /tmp/ha-pop-deploy'
```

With the temporary client available, deploy from this repository:

```sh
tar -cf - frontend dashboards tools/install_dashboard.py |
  ssh homeassistant-local 'mkdir -p /tmp/ha-pop-deploy/payload; tar -xf - -C /tmp/ha-pop-deploy/payload; PYTHONPATH=/tmp/ha-pop-deploy python3 /tmp/ha-pop-deploy/payload/tools/install_dashboard.py'
```

Rerunning the installer applies the YAML source to this managed dashboard, backing up the previous saved configuration. Edits made only through Home Assistant's dashboard editor will therefore be replaced on the next deployment.

Force-reload the panel after an update so it loads the new module. On the Pi:

```sh
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
wlrctl toplevel focus app_id:chromium
wlrctl keyboard type r modifiers CTRL,SHIFT
```

## Checks

Run `node --test tests/panel.test.cjs` for control behavior and doorbell command handling. Evaluate [`tests/verify-layout.js`](../tests/verify-layout.js) in the panel browser at 720 × 1280 to check page overflow, section boundaries, touch target sizes, popup layout, cleanup, and focus return. These layout checks open details without sending device commands.

## Recovery

To select another dashboard, put its URL in `~/.config/ha-panel/url` and restart `ha-panel`. The original Home dashboard is available at `https://homeassistant.example/dashboard-example/0`.

The installer stores backups under `/config/ha-pop-backups/`. To remove the panel dashboard, delete “Panel” and its `/local/ha-pop/ha-pop-panel.js` resource in Home Assistant's dashboard settings. Specific deployment backup records are in the [changelog](../CHANGELOG.md).
