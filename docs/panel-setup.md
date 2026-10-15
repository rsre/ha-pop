# Panel setup and maintenance

## Current status

On 2026-10-15, connected successfully using `ssh paneluser@192.0.2.10 -i ~/.ssh/homeassistant`. The Pi is named `panel` and runs Raspberry Pi OS 64-bit, Debian 13.7 (trixie), image 2026-10-06. Its 58 GB root filesystem has about 49 GB available. LightDM already automatically logs into labwc as `paneluser`; Chromium and Squeekboard are installed.

`https://homeassistant.example/` returned HTTP 200 from the Pi. After deployment and reboot on 2026-10-15, the service started automatically and a display capture confirmed the fullscreen Home Assistant login page without a keyring prompt. Terminating the main Chromium process verified automatic recovery: the service returned to active with a new PID and `NRestarts=1`. SSH remained available after reboot.

The user explicitly approved deploying `--password-store=basic` and rebooting to test startup. This avoids a keyring unlock prompt during automatic login. [Chromium's storage documentation](https://chromium.googlesource.com/chromium/src/+/refs/tags/116.0.5845.47/docs/linux/password_storage.md) describes basic storage as unencrypted. Decline password saving; retain only the Home Assistant session in the private profile.

The user confirmed successful touchscreen sign-in on 2026-10-15 after the keyboard repair. Login persistence through a subsequent reboot, representative home controls, network outage recovery, and a prolonged idle display check remain unverified. Select the desired dashboard in the panel's Home Assistant profile as needed.

The on-screen keyboard was subsequently repaired by enabling Chromium's Wayland input support and deploying a Squeekboard overlay copy. Keyboard visibility and entry through its keys were verified; see [keyboard setup and validation](keyboard.md).

A dedicated portrait dashboard was subsequently installed at `https://homeassistant.example/dashboard-panel/casa` and saved as the Pi's boot URL. It fits the screen without scrolling and opens detailed controls in popups. See [dashboard configuration and validation](dashboard.md). The original Home dashboard is retained.

Screen sleep was subsequently enabled after five minutes without input. A wake guard consumes the first touch before revealing the dashboard, preventing accidental control actions. The user confirmed this behavior on the physical screen. This supersedes the initial always-on display setting. See [screen sleep configuration](screen-sleep.md).

Touch scrolling was subsequently found to be blocked by the original `mouseEmulation="yes"` setting in labwc. On 2026-10-15 this was changed to `mouseEmulation="no"` for `10-005d Goodix Capacitive TouchScreen`, retaining `mapToOutput="DSI-1"`. labwc was reloaded using SIGHUP without restarting Chromium. The user confirmed swipe scrolling works after the change; both panel services remained active with their existing process IDs. The original configuration is backed up at `/home/paneluser/.local/state/ha-panel/backups/touch-20261015T130337/rc.xml`.

After enabling native touch, the user reported content staying displaced beyond the screen edges without bouncing back. Display and browser metrics confirmed a 720 × 1280 viewport, scale 1, no saved zoom overrides, and a hidden keyboard. Restarting Chromium cleared the issue, and the user confirmed normal behavior. The exact cause was not established; no extra scrolling or zoom flags were added. Temporary loopback-only browser diagnostics were removed after inspection. If it recurs, restart with `systemctl --user restart ha-panel`; this also confirmed that the saved Home Assistant sign-in survives a browser restart. A full reboot after sign-in remains untested.

## Installed configuration

| Purpose | Path on the Pi |
| --- | --- |
| Launcher | `/home/paneluser/.local/bin/ha-panel` |
| User service | `/home/paneluser/.config/systemd/user/ha-panel.service` |
| URL (one line) | `/home/paneluser/.config/ha-panel/url` |
| Persistent browser profile | `/home/paneluser/.local/share/ha-panel/chromium` |
| Startup hook | `/home/paneluser/.config/labwc/autostart` |
| Original-state backup | `/home/paneluser/.local/state/ha-panel/backups/20261015T124108-15844` |
| Installer source copy | `/home/paneluser/.local/share/ha-panel-source/kiosk` |

The startup hook retains `/etc/xdg/labwc/autostart`, imports Wayland session variables, and starts the user service. The service restarts Chromium five seconds after it exits. Before launching Chromium, the launcher waits for a successful HTTP response; the desktop can remain visible while Home Assistant or the network is unavailable. No screen blanking process was running or configured in the desktop autostart at inspection. The display is currently portrait, 720 × 1280 at 60 Hz, with touch mapped to `DSI-1`; those settings were preserved.

Commands below run over SSH as `paneluser`:

```sh
systemctl --user status ha-panel --no-pager --lines=5
systemctl --user stop ha-panel
systemctl --user start ha-panel
systemctl --user restart ha-panel
```

To update the target, edit `~/.config/ha-panel/url` and restart the service. Service output is available through `systemctl --user status`; this image currently reports no journal files through `journalctl --user`.

To undo this installation, stop the service and remove the `BEGIN ha-panel` / `END ha-panel` block from labwc autostart. Since autostart was previously absent, removing the newly created file restores system startup defaults. The backup's `previously-absent` file records each newly created path. Remove the launcher and service if no longer needed, then run `systemctl --user daemon-reload`. Keep the browser profile until its saved session is no longer needed.

The reproducible source is in [`../kiosk`](../kiosk). After installing the dashboard, run `bash kiosk/install.sh https://homeassistant.example/dashboard-panel/casa` as the desktop user on the Pi. The installer backs up existing files before changing them. A reinstall does not restart a running browser automatically.

## Intended behavior

1. Power on and automatically enter the graphical session.
2. Start Chromium in fullscreen kiosk mode at the chosen dashboard URL.
3. Retain the Home Assistant login across browser restarts and reboots.
4. Restart Chromium after it exits unexpectedly.
5. Keep SSH available for maintenance.

## Inspect before installing

Connect using the provisioned account, then inspect:

```sh
id
hostname
cat /etc/os-release
tr -d '\000' </proc/device-tree/model
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
df -h /
loginctl list-sessions
systemctl status display-manager --no-pager
pgrep -a labwc
command -v chromium
sudo -n true
```

Check the existing session startup files and back them up before changes. Preserve any existing applications or display settings. Identify the desktop account independently of the SSH account.

## Installation approach

Use Raspberry Pi OS 64-bit with a desktop and labwc. Reuse the installed OS if compatible; flashing the SD card requires a separate decision because it erases its contents. Raspberry Pi's [official kiosk guide](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/) uses `~/.config/labwc/autostart` to launch Chromium.

After inspection:

1. Install Chromium if missing and enable graphical automatic login for the intended desktop account.
2. Store the exact dashboard URL in the panel configuration, with no credentials or tokens in the URL.
3. Install a browser launcher and arrange for labwc autostart to invoke it. Supervise browser exits with a short retry delay and prevent duplicate instances.
4. Give Chromium a dedicated, persistent profile owned by the desktop account. Do not use incognito mode: the saved login must survive reboot.
5. Disable screen blanking for the initial always-on panel. Revisit a night schedule after basic operation is verified.
6. Start the kiosk, verify it remotely, then reboot and verify automatic startup.

Verify the URL from the Pi before using it in startup configuration. The initial candidate `http://192.0.2.20:8123/` refused connections. The confirmed endpoint is `https://homeassistant.example/`, with the installed panel at `/dashboard-panel/casa`.

## Display and touch

The 7-inch display has a native resolution of 720 × 1280. Select orientation to match the physical mounting; landscape presents 1280 × 720. Use Raspberry Pi OS display settings and verify touch alignment after rotation. The [official Touch Display 2 documentation](https://www.raspberrypi.com/documentation/accessories/touch-display-2.html) covers wiring, rotation, and the on-screen keyboard.

For finger scrolling, keep native touchscreen events enabled in `~/.config/labwc/rc.xml`:

```xml
<touch deviceName="10-005d Goodix Capacitive TouchScreen" mapToOutput="DSI-1" mouseEmulation="no"/>
```

[labwc documents](https://raw.githubusercontent.com/labwc/labwc/master/docs/labwc-config.5.scd) that mouse emulation translates touch motion into mouse motion. That prevents Chromium from receiving the native gestures it needs for swipe scrolling. Reload labwc after changes; a browser restart is unnecessary for this setting.

Test touch at all four corners, scrolling, sliders, and text entry. Touchscreen sign-in requires Chromium Wayland input support and a keyboard drawn above the fullscreen window. See [keyboard setup and repair](keyboard.md) for the Squeekboard layer fix and recovery commands.

## Home Assistant login

Create a dedicated regular user for the panel and sign in once on the panel. Choose its dashboard in the profile settings or use the dashboard's explicit URL. Home Assistant documents [separate wall-tablet profiles](https://www.home-assistant.io/dashboards/dashboards/) and [regular versus administrator accounts](https://www.home-assistant.io/faq/household-use/).

The browser profile contains the session and must remain private. Keep it outside version control. Anyone using the panel can perform the actions available to that user. Dashboard visibility alone does not provide entity-level access control.

## Acceptance checks

- A reboot opens the intended dashboard without a keyboard, shell, or manual browser launch.
- The login survives reboot.
- Touch controls and scrolling work in the mounted orientation.
- A representative light or other safe control works and reflects its actual state.
- The browser restarts after its process exits.
- A temporary network outage recovers when connectivity returns; check both an outage after login and booting while Home Assistant is unavailable.
- After five minutes idle, the display sleeps; the first touch wakes it without operating a control.
- SSH remains available after reboot.

The installed OS, desktop account, URL, file paths, backup location, and completed verification results are recorded above. Visual checks used remote `grim` captures; the user confirmed physical keyboard entry, scrolling, and guarded touch wake.

## Maintenance and recovery

Use SSH for maintenance. To escape fullscreen locally, attach a keyboard and use Alt+F4; stop the browser service first if it immediately relaunches.

If the panel shows an error page, check the dashboard URL from the Pi, network connectivity, DNS, clock, and browser logs. If it shows a login screen, sign in again without deleting the browser profile. If the display is blank, check the graphical session and display connection before changing Chromium flags.

On 2026-10-15, a reported full-browser reload when using a dashboard subview's Back arrow was investigated. Before diagnostics, Chromium's service showed zero automatic restarts and the same main process had been running for over 20 minutes. After restarting the browser for temporary local diagnostics, both a pointer click and the user's touchscreen Back test returned from `/dashboard-heating/heating` to `/dashboard-example/0` while retaining the same JavaScript document marker and `performance.timeOrigin`. The user confirmed normal behavior. The original symptom was not reproduced, so no navigation patches or speculative browser flags were added. Temporary diagnostics were removed and normal kiosk startup restored. If it recurs, distinguish a page navigation from an actual service restart using `systemctl --user show ha-panel -p MainPID -p NRestarts` before restarting the browser.

Back up changed startup files so kiosk startup can be removed and the previous desktop behavior restored. Shut down with `sudo poweroff` before disconnecting power. Keep the root filesystem writable during initial deployment so the browser login and configuration persist; evaluate SD write reduction only after reboot testing.
