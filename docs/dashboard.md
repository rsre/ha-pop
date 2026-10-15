# Portrait touchscreen dashboard

The installed dashboard is [Panel](https://homeassistant.example/dashboard-panel/casa). The Pi's kiosk URL now points directly to it. The original Home dashboard remains available.

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
| Initial registration backup | `/config/ha-pop-backups/20261015T140457-825387` |
| Final deployment backup | `/config/ha-pop-backups/20261015T140811-892863` |
| Previous Pi URL | `/home/paneluser/.local/state/ha-panel/backups/dashboard-20261015T140524/url` |

The installer copies the frontend atomically, registers its resource through the WebSocket API, creates the dashboard if absent, saves its configuration, and reads it back to verify equality. It backs up existing registrations, configuration, and frontend before changes. It does not edit `.storage` files or `configuration.yaml` directly and requires no Core restart. Installation used the SSH add-on's existing Supervisor authentication; no credentials are stored in this repository.

## Update

Edit the JavaScript and YAML here. Bump `HA_POP_VERSION` when changing JavaScript, then run:

```sh
node --check frontend/ha-pop-panel.js
node --test tests/panel.test.cjs
git diff --check
```

For the initial deployment, a pure-Python `websocket-client` package was copied into `/tmp/ha-pop-deploy` on the server, and the SSH add-on already provided PyYAML. Recreate that temporary dependency if the add-on has restarted; the installer accepts it via `PYTHONPATH`. The dependency is used only for installation, not by the running dashboard:

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

## Validation

On 2026-10-15, tested the installed dashboard in Chromium on the physical Pi:

- Page dimensions are exactly **720 × 1280**, with no horizontal or vertical document overflow.
- The card occupies **720 × 1224** below the toolbar.
- All 12 primary touch targets are at least 44 pixels and remain within the screen.
- Lighting and machine controls stay inside their section boundaries.
- All seven popups load their actual native cards without error cards, fit on screen without scrolling, release their cards on close, and restore focus.
- Rapidly replacing the camera popup with the coffee popup retains the new popup's content.
- Native Home Assistant more-info events release the panel modal before opening the native dialog.
- Seven unit tests cover correct entity/service selection, unavailable and offline behavior, duplicate-tap suppression, failure feedback, popup configuration, entity validation, and fresh doorbell command handling.

The live layout checks are in [`tests/verify-layout.js`](../tests/verify-layout.js), evaluated in the panel's browser at the physical viewport. They open and close details without sending device commands. No device actions were executed by the validation suite. Temporary diagnostics were removed; both kiosk services are active, the saved boot URL targets the new dashboard, and a screenshot after normal browser startup confirmed it loads correctly with the existing login. A full reboot after selecting the new dashboard has not been performed.

## Roll back

Restore the Pi's previous URL and restart its browser:

```sh
cp ~/.local/state/ha-panel/backups/dashboard-20261015T140524/url ~/.config/ha-panel/url
systemctl --user restart ha-panel
```

This immediately returns the panel to the original Home dashboard. To remove the new dashboard entirely, delete “Panel” and its `/local/ha-pop/ha-pop-panel.js` resource in Home Assistant's dashboard settings. The backups above retain its prior registrations and source for recovery.
