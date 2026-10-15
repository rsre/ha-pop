# Panel setup and maintenance

## Configuration

The panel is a Raspberry Pi 5 running Raspberry Pi OS 64-bit, Debian 13.7 (trixie). LightDM automatically logs into labwc as `paneluser`. The OS hostname is `panel`; Avahi advertises `panel.local` at `192.0.2.10`.

The display is mounted in portrait at 720 × 1280, 60 Hz, with touch mapped to `DSI-1`. Chromium opens `https://homeassistant.example/dashboard-panel/casa` in fullscreen kiosk mode using a persistent Home Assistant session. The [dashboard guide](dashboard.md) covers its sections and popup controls.

The panel uses an [overlay keyboard](keyboard.md), [guarded touch wake](screen-sleep.md), and [Home Assistant wake, sleep, and doorbell commands](remote-control.md). The browser, keyboard, idle handler, and remote command endpoint start through labwc autostart.

## Installed paths

| Purpose | Path on the Pi |
| --- | --- |
| Launcher | `/home/paneluser/.local/bin/ha-panel` |
| Browser service | `/home/paneluser/.config/systemd/user/ha-panel.service` |
| URL (one line) | `/home/paneluser/.config/ha-panel/url` |
| Persistent browser profile | `/home/paneluser/.local/share/ha-panel/chromium` |
| Startup hook | `/home/paneluser/.config/labwc/autostart` |
| Installer source copy | `/home/paneluser/.local/share/ha-panel-source/kiosk` |
| Installer backups | `/home/paneluser/.local/state/ha-panel/backups/` |

The startup hook retains `/etc/xdg/labwc/autostart`, imports the graphical session environment, and starts the panel services. The browser service restarts Chromium five seconds after it exits. The launcher waits for a successful HTTP response before opening Chromium; the desktop can remain visible while Home Assistant or the network is unavailable.

## Install or update

Use Raspberry Pi OS 64-bit with a desktop and labwc. Inspect the desktop account, display mapping, network access, and existing startup files before installation. Enable graphical automatic login for the desktop user and install Chromium and curl if needed. Raspberry Pi's [kiosk guide](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/) describes the labwc startup mechanism.

Copy this repository to the Pi and install the [dashboard](dashboard.md). Run as the desktop user:

```sh
bash kiosk/install.sh https://homeassistant.example/dashboard-panel/casa
```

The installer backs up existing files. Reinstalling does not restart an active browser automatically. Install the keyboard, guarded sleep, and remote commands using their linked guides. Keep the persistent browser profile outside version control.

## Browser and login

The launcher uses Wayland input support and `--password-store=basic` to avoid a keyring unlock prompt during automatic login. [Chromium documents](https://chromium.googlesource.com/chromium/src/+/refs/tags/116.0.5845.47/docs/linux/password_storage.md) basic password storage as unencrypted. Decline password saving and retain only the Home Assistant session in the private profile.

Use a dedicated regular Home Assistant account and sign in once on the panel. Anyone using the touchscreen can operate controls available to that account. Dashboard visibility does not provide entity-level access control.

Run these commands over SSH as `paneluser`:

```sh
systemctl --user status ha-panel --no-pager --lines=5
systemctl --user stop ha-panel
systemctl --user start ha-panel
systemctl --user restart ha-panel
```

To select a different dashboard, edit `~/.config/ha-panel/url` and restart the browser service. Use `systemctl --user status` for service output; user journal files may be unavailable on this image.

## Display and touch

Keep native touchscreen events enabled in `~/.config/labwc/rc.xml`:

```xml
<touch deviceName="10-005d Goodix Capacitive TouchScreen" mapToOutput="DSI-1" mouseEmulation="no"/>
```

Native touch events allow Chromium to handle finger scrolling and sliders. Reload labwc after changing its touch configuration. Use Raspberry Pi OS display settings for orientation and verify touch alignment afterward. The [Touch Display 2 documentation](https://www.raspberrypi.com/documentation/accessories/touch-display-2.html) covers wiring, rotation, and keyboard support.

## Local network name

Connect with:

```sh
ssh paneluser@panel.local -i ~/.ssh/homeassistant
```

The IP address `192.0.2.10` is available as a fallback. Home Assistant's panel commands use that fixed IP address.

Avahi uses `host-name=panel` in `/etc/avahi/avahi-daemon.conf`. After changing the mDNS name, run `sudo systemctl restart avahi-daemon`. The network must pass mDNS traffic for `.local` resolution. The independent mDNS name leaves the cloud-init-managed OS hostname as `panel`.

## Checks after installation or updates

- Boot into the intended dashboard and confirm the login persists.
- Check touch alignment, scrolling, sliders, and keyboard entry.
- Check a representative device control and its state feedback.
- Confirm the browser service recovers after Chromium exits.
- Check recovery from a network outage, including booting while Home Assistant is unavailable.
- Confirm idle sleep consumes the first wake tap without operating a control.
- Run the Home Assistant wake, sleep, and doorbell scripts.
- Confirm SSH remains available.

Recorded verification results and outstanding checks are in the [changelog](../CHANGELOG.md).

## Recovery and removal

If the panel shows an error page, check its URL, network connection, DNS, clock, and browser service output. If it shows a login page, sign in again without deleting the browser profile. For a blank display, check idle state and try `script.ha_panel_wake` before investigating the graphical session or display connection.

Restart Chromium if page content is displaced. To distinguish a page navigation from a browser service restart, inspect `systemctl --user show ha-panel -p MainPID -p NRestarts` before restarting it. To escape fullscreen locally, attach a keyboard and stop the browser service before closing its window.

To remove the panel setup, remove its labwc autostart block, stop all panel services, and restore startup files from the relevant installer backup. The backup's `previously-absent` file identifies newly created paths. Remove unneeded service files and run `systemctl --user daemon-reload`. Keep the browser profile until its saved session is no longer needed. Follow the remote control guide to remove Home Assistant scripts, automation, and package configuration.

Use `sudo poweroff` before disconnecting power. Keep the filesystem writable for the browser profile and configuration. Specific deployment backups and troubleshooting history are listed in [CHANGELOG.md](../CHANGELOG.md).
