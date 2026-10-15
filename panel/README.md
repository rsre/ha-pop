# Panel setup and maintenance

This directory contains everything installed on the Raspberry Pi: the Chromium launcher, user services, touch wake guard, remote wake/sleep endpoint, keyboard patches, installers, and tests. The dashboard and Home Assistant configuration live in [Home Assistant integration](../custom_components/ha_pop/README.md).

## Configuration

The panel is a Raspberry Pi 5 running Raspberry Pi OS 64-bit, Debian 13.7 (trixie). LightDM automatically logs into labwc as `ha`. The hostname is configured in Raspberry Pi OS; Avahi can advertise `panel.local` on the local network.

The display is mounted in portrait at 720 × 1280, 60 Hz, with touch mapped to `DSI-1`. Chromium opens `https://homeassistant.example/ha-pop-panel/home?ha_pop_kiosk=1` in fullscreen kiosk mode using a persistent Home Assistant session. The [dashboard guide](../custom_components/ha_pop/docs/dashboard.md) covers its sections and popup controls.

The panel uses an [overlay keyboard](docs/keyboard.md), [guarded touch wake](docs/screen-sleep.md), and [Home Assistant wake, sleep, and doorbell commands](../custom_components/ha_pop/README.md). The browser, keyboard, idle handler, and remote command endpoint start through labwc autostart.

## Installed paths

| Purpose | Path on the Pi |
| --- | --- |
| Launcher | `$HOME/.local/bin/ha-panel` |
| Browser service | `$HOME/.config/systemd/user/ha-panel.service` |
| URL (one line) | `$HOME/.config/ha-panel/url` |
| Persistent browser profile | `$HOME/.local/share/ha-panel/chromium` |
| Startup hook | `$HOME/.config/labwc/autostart` |
| Installer source copy | `$HOME/.local/share/ha-panel-source/panel` |
| Installer backups | `$HOME/.local/state/ha-panel/backups/` |

The startup hook retains `/etc/xdg/labwc/autostart`, imports the graphical session environment, and starts the panel services. The browser service restarts Chromium five seconds after it exits. Chromium exposes browser control only on `127.0.0.1:9222`; the authenticated doorbell endpoint uses it to return to the configured dashboard and open video. No arbitrary URL or browser command is accepted over the LAN. The launcher waits for a successful HTTP response before opening Chromium; the desktop can remain visible while Home Assistant or the network is unavailable.

## Install or update

Use Raspberry Pi OS 64-bit with a desktop and labwc. Inspect the desktop account, display mapping, network access, and existing startup files before installation. Enable graphical automatic login for the desktop user and install Chromium and curl if needed. Raspberry Pi's [kiosk guide](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/) describes the labwc startup mechanism.

Copy only this directory to the Pi:

```sh
tar -cf - panel |
  ssh -i ~/.ssh/homeassistant ha@panel.local 'mkdir -p ~/.local/share/ha-panel-source; tar -xf - -C ~/.local/share/ha-panel-source'
```

The installer requires Chromium, curl, labwc, systemd user services, swayidle, wlopm, Python GTK3 bindings, `gir1.2-gtklayershell-0.1`, `python3-gi-cairo`, and `python3-websocket`. Prepare the patched Squeekboard binary using the [keyboard build guide](docs/keyboard.md). Run the complete installer as the desktop user in the graphical session, or over SSH with its session environment imported into the user service manager:

```sh
cd ~/.local/share/ha-panel-source
bash panel/install.sh https://homeassistant.example/ha-pop-panel/home /path/to/patched/squeekboard
```

This installs the kiosk, overlay keyboard, guarded sleep, and authenticated command endpoint. It backs up changed files and preserves the shared token. On subsequent runs, omit the keyboard path to reuse the installed patched binary. Start `ha-panel` in the desktop session or reboot after installation. The individual `install-kiosk.sh`, `install-keyboard.sh`, `install-idle.sh`, and `install-remote.sh` scripts support component updates.

After installing the Pi services, install the [Home Assistant integration](../custom_components/ha_pop/README.md) through HACS and enter the token from `~/.config/ha-panel/remote-token` in its UI setup form. Select the integration dashboard URL in the launcher.

## Browser and login

The launcher uses Wayland input support and `--password-store=basic` to avoid a keyring unlock prompt during automatic login. [Chromium documents](https://chromium.googlesource.com/chromium/src/+/refs/tags/116.0.5845.47/docs/linux/password_storage.md) basic password storage as unencrypted. Decline password saving and retain only the Home Assistant session in the private profile.

Use a dedicated regular Home Assistant account and sign in once on the panel. Anyone using the touchscreen can operate controls available to that account. Dashboard visibility does not provide entity-level access control.

Run these commands over SSH as `ha`:

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

Native touch events allow Chromium to handle finger scrolling and sliders. The launcher disables Chromium's touchscreen and touchpad overscroll history navigation, preventing horizontal swipes from going back or forward. Reload labwc after changing its touch configuration. Use Raspberry Pi OS display settings for orientation and verify touch alignment afterward. The [Touch Display 2 documentation](https://www.raspberrypi.com/documentation/accessories/touch-display-2.html) covers wiring, rotation, and keyboard support.

## Local network name

Connect with:

```sh
ssh ha@panel.local -i ~/.ssh/homeassistant
```

Use the Pi's LAN address as a fallback if mDNS is unavailable.

Avahi uses `host-name=panel` in `/etc/avahi/avahi-daemon.conf`. After changing the mDNS name, run `sudo systemctl restart avahi-daemon`. The network must pass mDNS traffic for `.local` resolution. The mDNS name is independent of the OS hostname.

## Checks after installation or updates

- Boot into the intended dashboard and confirm the login persists.
- Check touch alignment, scrolling, sliders, and keyboard entry.
- Check a representative device control and its state feedback.
- Confirm the browser service recovers after Chromium exits.
- Check recovery from a network outage, including booting while Home Assistant is unavailable.
- Confirm idle sleep consumes the first wake tap without operating a control.
- Press the integration Wake, Sleep, and Show doorbell buttons.
- Confirm SSH remains available.

Run `python3 -m unittest discover -s panel/tests -p 'test_*.py'` from the checkout for the Pi control tests.

Recorded verification results and outstanding checks are in the [changelog](../CHANGELOG.md).

## Recovery and removal

If the panel shows an error page, check its URL, network connection, DNS, clock, and browser service output. If it shows a login page, sign in again without deleting the browser profile. For a blank display, check idle state and press the integration Wake button before investigating the graphical session or display connection.

Restart Chromium if page content is displaced. To distinguish a page navigation from a browser service restart, inspect `systemctl --user show ha-panel -p MainPID -p NRestarts` before restarting it. To escape fullscreen locally, attach a keyboard and stop the browser service before closing its window.

To remove the panel setup, remove its labwc autostart block, stop all panel services, and restore startup files from the relevant installer backup. The backup's `previously-absent` file identifies newly created paths. Remove unneeded service files and run `systemctl --user daemon-reload`. Keep the browser profile until its saved session is no longer needed. Remove the Home Assistant integration and its associated automations through the HA UI when they are no longer needed.

Use `sudo poweroff` before disconnecting power. Keep the filesystem writable for the browser profile and configuration. Specific deployment backups and troubleshooting history are listed in [CHANGELOG.md](../CHANGELOG.md).
