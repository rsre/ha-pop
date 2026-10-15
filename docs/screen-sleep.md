# Screen sleep and touch wake

The panel turns off its DSI display after **five minutes without input**. The first tap wakes the display without reaching dashboard controls. After lifting that finger, subsequent taps operate the dashboard normally. The Pi, Home Assistant browser, and network connection continue running; there is no operating-system suspend or login prompt.

The user service `ha-panel-idle` runs `swayidle`. At idle it starts `ha-panel-wake-guard`, which maps a black Wayland overlay with exclusive input capture **before** turning `DSI-1` off. The guard reports ready only after that surface has reached the compositor. On activity it wakes the display but retains the overlay until the entire touch/button/key gesture has ended, with a short quiet interval to consume trailing events. Only then is the dashboard exposed.

Plain display power-off was insufficient: the first wake tap also reached the dashboard and could operate a control. The compositor-level overlay replaces that behavior and protects all dashboard content, including popups and the Home Assistant toolbar. It captures multiple touch contacts and held keys until they are released. A compositor wake notification without a routed touch also releases the guard after a short fallback interval.

labwc starts the idle service after importing the graphical session environment. Stopping the service stops any active guard and turns the display back on. Guard startup failures leave the display on.

| Item | Path on the Pi |
| --- | --- |
| Service | `/home/paneluser/.config/systemd/user/ha-panel-idle.service` |
| Wake guard service | `/home/paneluser/.config/systemd/user/ha-panel-wake-guard.service` |
| Wake guard | `/home/paneluser/.local/bin/ha-panel-wake-guard.py` |
| Timeout | `/home/paneluser/.config/ha-panel/idle.conf` |
| Startup | `/home/paneluser/.config/labwc/autostart` |
| Original-state backup | `/home/paneluser/.local/state/ha-panel/backups/idle-20261015T141437-139544` |
| Pre-guard configuration backup | `/home/paneluser/.local/state/ha-panel/backups/idle-20261015T142159-150630` |

The source services, Python guard, and installer are in [`kiosk`](../kiosk). The guard uses the distribution's GTK3 Python bindings, `gir1.2-gtklayershell-0.1`, and `python3-gi-cairo`. Reinstall those dependencies if needed, then run `bash kiosk/install-idle.sh 300` as the desktop user. The installer backs up existing files and accepts an idle duration in seconds, with a minimum of 10 seconds.

Home Assistant can [wake the screen on command and show the doorbell video](remote-control.md). A remote wake temporarily pauses this idle service for a five-minute hold, then restores it.

## Adjust or control

Run over SSH as `paneluser`:

```sh
# Change the duration, then reload the service.
printf 'HA_PANEL_IDLE_SECONDS=300\n' > ~/.config/ha-panel/idle.conf
systemctl --user restart ha-panel-idle

# Sleep now, while retaining automatic wake on input.
systemctl --user kill --kill-whom=main --signal=SIGUSR1 ha-panel-idle

# Wake the display and keep it on until the service is started again.
systemctl --user stop ha-panel-idle
systemctl --user start ha-panel-idle
```

To permanently return to always-on operation, remove the line `systemctl --user start ha-panel-idle.service` from labwc autostart and stop the service. To restore sleep behavior, rerun the installer.

The [swayidle documentation](https://github.com/swaywm/swayidle/blob/master/swayidle.1.scd) describes idle timeout/resume events and the immediate-idle signal.

## Verification

On 2026-10-15, unit validation passed and a temporary 10-second idle test confirmed `DSI-1` changes from power mode `on` to `off`. The temporary test override was removed, the normal five-minute timeout restored, and an immediate-idle test left the display asleep. The user confirmed that a physical tap wakes the dashboard. The browser stayed running throughout. No browser restart or Pi reboot is needed to change this setting.

After the user reported wake-tap actions, the guard was added. Its two systemd units pass validation, and five unit tests cover held touches, complete release plus quiet time, trailing pointer events, mixed held inputs, and wake notifications without delivered touches. A live pointer test over the camera area confirmed the first click only wakes the screen, leaves the camera popup closed, and exits the guard successfully; the second click opens the popup normally. After the signal fix described below, the user confirmed that a physical tap reveals the dashboard without opening the camera popup.

Run the guard's logic tests from the repository:

```sh
python3 -m unittest discover -s tests -p 'test_wake_guard.py'
```

The first physical guard test exposed a signal race: systemd sent the resume signal to both the guard and its running `wlopm` child, interrupting display power control and leaving the overlay visible. Resume now targets only the main guard process (`--kill-whom=main`). Input handlers also schedule guard dismissal before invoking display power control. Physical retesting passed on 2026-10-15: the user confirmed the first tap wakes the dashboard without triggering the underlying control. The normal five-minute idle timeout remains configured.
