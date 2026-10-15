# Changelog

Project changes, deployment history, troubleshooting findings, and verification records live here. Current configuration and procedures are in [README.md](README.md) and [docs](docs).

## 2026-10-15

### Kiosk installation, touch input, and navigation

On 2026-10-15, connected successfully using `ssh paneluser@192.0.2.10 -i ~/.ssh/homeassistant`. The Pi is named `panel` and runs Raspberry Pi OS 64-bit, Debian 13.7 (trixie), image 2026-10-06. Its 58 GB root filesystem had about 49 GB available at inspection. LightDM already automatically logs into labwc as `paneluser`; Chromium and Squeekboard are installed.

`https://homeassistant.example/` returned HTTP 200 from the Pi. After deployment and reboot on 2026-10-15, the service started automatically and a display capture confirmed the fullscreen Home Assistant login page without a keyring prompt. Terminating the main Chromium process verified automatic recovery: the service returned to active with a new PID and `NRestarts=1`. SSH remained available after reboot.

The user explicitly approved deploying `--password-store=basic` and rebooting to test startup. This avoids a keyring unlock prompt during automatic login. [Chromium's storage documentation](https://chromium.googlesource.com/chromium/src/+/refs/tags/116.0.5845.47/docs/linux/password_storage.md) describes basic storage as unencrypted. Decline password saving; retain only the Home Assistant session in the private profile.

The user confirmed successful touchscreen sign-in on 2026-10-15 after the keyboard repair. Login persistence through a subsequent reboot, representative home controls, network outage recovery, and a prolonged idle display check remain unverified. Select the desired dashboard in the panel's Home Assistant profile as needed.

The on-screen keyboard was subsequently repaired by enabling Chromium's Wayland input support and deploying a Squeekboard overlay copy. Keyboard visibility and entry through its keys were verified; see [keyboard setup and validation](docs/keyboard.md).

A dedicated portrait dashboard was subsequently installed at `https://homeassistant.example/dashboard-panel/casa` and saved as the Pi's boot URL. It fits the screen without scrolling and opens detailed controls in popups. See [dashboard configuration and validation](docs/dashboard.md). The original Home dashboard is retained.

Screen sleep was subsequently enabled after five minutes without input. A wake guard consumes the first touch before revealing the dashboard, preventing accidental control actions. The user confirmed this behavior on the physical screen. This supersedes the initial always-on display setting. See [screen sleep configuration](docs/screen-sleep.md).

Home Assistant remote wake and doorbell display were subsequently installed. The `ring` event from `event.doorbell` runs `script.ha_panel_doorbell`, waking the screen and opening the camera popup. `script.ha_panel_wake` wakes it without changing the view. See [remote control installation and validation](docs/remote-control.md).

Touch scrolling was subsequently found to be blocked by the original `mouseEmulation="yes"` setting in labwc. On 2026-10-15 this was changed to `mouseEmulation="no"` for `10-005d Goodix Capacitive TouchScreen`, retaining `mapToOutput="DSI-1"`. labwc was reloaded using SIGHUP without restarting Chromium. The user confirmed swipe scrolling works after the change; both panel services remained active with their existing process IDs. The original configuration is backed up at `/home/paneluser/.local/state/ha-panel/backups/touch-20261015T130337/rc.xml`.

After enabling native touch, the user reported content staying displaced beyond the screen edges without bouncing back. Display and browser metrics confirmed a 720 × 1280 viewport, scale 1, no saved zoom overrides, and a hidden keyboard. Restarting Chromium cleared the issue, and the user confirmed normal behavior. The exact cause was not established; no extra scrolling or zoom flags were added. Temporary loopback-only browser diagnostics were removed after inspection. If it recurs, restart with `systemctl --user restart ha-panel`; this also confirmed that the saved Home Assistant sign-in survives a browser restart. A full reboot after sign-in remains untested.

On 2026-10-15, a reported full-browser reload when using a dashboard subview's Back arrow was investigated. Before diagnostics, Chromium's service showed zero automatic restarts and the same main process had been running for over 20 minutes. After restarting the browser for temporary local diagnostics, both a pointer click and the user's touchscreen Back test returned from `/dashboard-heating/heating` to `/dashboard-example/0` while retaining the same JavaScript document marker and `performance.timeOrigin`. The user confirmed normal behavior. The original symptom was not reproduced, so no navigation patches or speculative browser flags were added. Temporary diagnostics were removed and normal kiosk startup restored. If it recurs, distinguish a page navigation from an actual service restart using `systemctl --user show ha-panel -p MainPID -p NRestarts` before restarting the browser.

### Fullscreen keyboard

On 2026-10-15, deployed the overlay keyboard and verified it appears above Home Assistant in a display capture. A virtual pointer click on the keyboard entered `q` into the empty username field; clicking the keyboard's Backspace removed it. No login was submitted during that test. The user subsequently confirmed successful sign-in on the touchscreen. Both panel services are active. Startup is configured in labwc; the combined keyboard setup has not yet been tested through another reboot.

The build uses the official Raspberry Pi source package `1.43.1-1+rpt1`, matching the installed package. Compiler and Rust dependencies use about 1 GB of additional SD space. Enable Debian source repositories before installing build dependencies. During initial repair a temporary `/etc/apt/sources.list.d/ha-panel-build.sources` was used and subsequently removed; no original repository files were changed.

Validation: the runtime binary compiled successfully, both service units passed `systemd-analyze --user verify`, and keyboard visibility and text entry passed live checks. The initial package test run failed because a Raspberry Pi source fixture omitted the `name` field from `OutputState`; the test-only patch adds `name: None`. After correcting the fixture, the optional full package test rebuild was stopped during dependency compilation once the user confirmed successful sign-in. The full upstream test suite is not reported as passing. Build logs remain in the source directory.

### Portrait dashboard — panel 0.1.1

Added the no-scroll portrait dashboard and seven popups. Fixed inherited line heights and section row sizing in version 0.1.1.

On 2026-10-15, tested the installed dashboard in Chromium on the physical Pi:

- Page dimensions are exactly **720 × 1280**, with no horizontal or vertical document overflow.
- The card occupies **720 × 1224** below the toolbar.
- All 12 primary touch targets are at least 44 pixels and remain within the screen.
- Lighting and machine controls stay inside their section boundaries.
- All seven popups load their actual native cards without error cards, fit on screen without scrolling, release their cards on close, and restore focus.
- Rapidly replacing the camera popup with the coffee popup retains the new popup's content.
- Native Home Assistant more-info events release the panel modal before opening the native dialog.
- Six original unit tests covered correct entity/service selection, unavailable and offline behavior, duplicate-tap suppression, failure feedback, popup configuration, and entity validation. A seventh test was added with remote doorbell commands in version 0.1.2.

The live layout checks are in [`tests/verify-layout.js`](tests/verify-layout.js), evaluated in the panel's browser at the physical viewport. They open and close details without sending device commands. No device actions were executed by the validation suite. Temporary diagnostics were removed; both kiosk services are active, the saved boot URL targets the new dashboard, and a screenshot after normal browser startup confirmed it loads correctly with the existing login. A full reboot after selecting the new dashboard has not been performed.

### Guarded display sleep

Plain display power-off was insufficient: the first wake tap also reached the dashboard and could operate a control. The compositor-level overlay replaces that behavior and protects all dashboard content, including popups and the Home Assistant toolbar. It captures multiple touch contacts and held keys until they are released. A compositor wake notification without a routed touch also releases the guard after a short fallback interval.

On 2026-10-15, unit validation passed and a temporary 10-second idle test confirmed `DSI-1` changes from power mode `on` to `off`. The temporary test override was removed, the normal five-minute timeout restored, and an immediate-idle test left the display asleep. The user confirmed that a physical tap wakes the dashboard. The browser stayed running throughout. No browser restart or Pi reboot is needed to change this setting.

After the user reported wake-tap actions, the guard was added. Its two systemd units pass validation, and five unit tests cover held touches, complete release plus quiet time, trailing pointer events, mixed held inputs, and wake notifications without delivered touches. A live pointer test over the camera area confirmed the first click only wakes the screen, leaves the camera popup closed, and exits the guard successfully; the second click opens the popup normally. After the signal fix described below, the user confirmed that a physical tap reveals the dashboard without opening the camera popup.

The first physical guard test exposed a signal race: systemd sent the resume signal to both the guard and its running `wlopm` child, interrupting display power control and leaving the overlay visible. Resume now targets only the main guard process (`--kill-whom=main`). Input handlers also schedule guard dismissal before invoking display power control. Physical retesting passed on 2026-10-15: the user confirmed the first tap wakes the dashboard without triggering the underlying control. The normal five-minute idle timeout remains configured.

### Remote wake and doorbell display — panel 0.1.2

On 2026-10-15, Home Assistant configuration validation passed and Core restarted successfully. Both scripts, the helper, and the enabled ring automation appeared in the live API. Unauthenticated wake requests returned HTTP 401.

Running the installed automation's actions while the guarded screen was asleep powered on `DSI-1`, removed the guard, and opened a `videolink-doorbell` card with no error card. Its video reached ready state 4, played at 640 × 480, and reported its stream ready. Chromium retained the same document identity. A repeated doorbell command preserved the exact video card instance; a subsequent wake-only command also retained the popup and stream. No physical doorbell event was emitted during testing, so the existing TV automation was not triggered.

The portrait layout checks also passed on version 0.1.2: 720 × 1280 with no page overflow, all 12 main touch targets inside the screen, and all seven popups fitting without scroll or error cards.

Deployment backups:

- Pi remote service: `/home/paneluser/.local/state/ha-panel/backups/remote-20261015T144242-181858`.
- HA package/configuration/secrets: `/config/ha-pop-backups/remote-20261015T144244-217315`.
- Frontend and dashboard: `/config/ha-pop-backups/20261015T144243-773961`.

The full five-minute wake hold expired and automatically restarted the idle service with the remote process still healthy. Starting guarded sleep then powered `DSI-1` off; another doorbell command woke it and displayed the camera again under normal kiosk startup. Temporary browser diagnostics were removed and their port verified closed.

The hold delays the start of normal idle handling: the screen can remain on for another idle interval afterward. A physical ring and a Pi reboot after installing remote control have not been tested.

On 2026-10-15, the panel scripts were migrated from the package into `scripts.yaml` and `script.ha_panel_sleep` was added. Migration tests cover existing UI edits, legacy package scripts, preserved YAML tags, and empty script files.

Configuration validation and reloads of `rest_command` and `script` passed without restarting Core. The UI script configuration API returned HTTP 200 for all three scripts. Running wake followed by sleep left the idle service and wake guard active with `DSI-1` powered off. Migration backup: `/config/ha-pop-backups/remote-20261015T175814-721587`.

The doorbell automation was subsequently moved out of the package into `/config/automations.yaml`, retaining its stable ID. Migration backup: `/config/ha-pop-backups/remote-20261015T180240-530155`. The installer migrates by ID and preserves UI edits on subsequent deployments.

Configuration validation and automation reload passed without restarting Core. The UI automation editor API returned HTTP 200 for `ha_pop_show_doorbell_on_panel`; the ID appears exactly once in `automations.yaml`, the package no longer defines automations, and the reloaded automation remains enabled.

### mDNS name

Avahi advertises `panel.local` at `192.0.2.10`. On 2026-10-15, name resolution and SSH were verified from the development computer. The OS hostname remains `panel`; the independent mDNS name avoids changing cloud-init-managed host configuration. Home Assistant commands retain the fixed IP URL.

The setting is `host-name=panel` in `/etc/avahi/avahi-daemon.conf`. The prior file is backed up at `/home/paneluser/.local/state/ha-panel/backups/mdns-20261015T175905/avahi-daemon.conf`. After editing the name, run `sudo systemctl restart avahi-daemon`. Resolution requires a network that passes mDNS traffic; the IP remains available as a fallback.

### Additional deployment backups

- Kiosk installation backup: `/home/paneluser/.local/state/ha-panel/backups/20261015T124108-15844`.
- Keyboard installation backup: `/home/paneluser/.local/state/ha-panel/backups/keyboard-20261015T125923-24421`.
- Initial registration backup: `/config/ha-pop-backups/20261015T140457-825387`.
- Final deployment backup: `/config/ha-pop-backups/20261015T140811-892863`.
- Previous Pi URL: `/home/paneluser/.local/state/ha-panel/backups/dashboard-20261015T140524/url`.
- Initial sleep configuration backup: `/home/paneluser/.local/state/ha-panel/backups/idle-20261015T141437-139544`.
- Pre-guard configuration backup: `/home/paneluser/.local/state/ha-panel/backups/idle-20261015T142159-150630`.

### Additional installation and validation records

The original labwc user autostart file was absent and no display blanking process was configured at initial inspection. Display orientation and touch output mapping were preserved. The first candidate Home Assistant endpoint, `http://192.0.2.20:8123/`, refused connections; the confirmed HTTPS endpoint was used instead.

Review of the initial changeset fixed fresh sleep installation so it does not try to stop a nonexistent service. Fresh and repeat installations passed isolated checks on the Pi with mocked services.

After adding sleep control and UI-editable scripts and automation, all 24 tests passed: 17 Python tests and seven JavaScript tests. Wake → sleep → wake was verified against the running panel. A full reboot with the complete configuration, physical doorbell ring, device control acceptance check, network outage recovery, and the full upstream Squeekboard test suite remain outside the recorded validation.

### Documentation organization

Moved dated deployment notes, investigations, verification results, and specific backup records into this changelog. Revised the guides to describe the current configuration and maintenance procedures.
