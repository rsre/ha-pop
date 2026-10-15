# Screen sleep and touch wake

The panel turns off its DSI display after **five minutes without input**. The first tap wakes the display without reaching dashboard controls. After lifting that finger, subsequent taps operate the dashboard normally. The Pi, Home Assistant browser, and network connection continue running; there is no operating-system suspend or login prompt.

The user service `ha-panel-idle` runs `swayidle`. At idle it starts `ha-panel-wake-guard`, which maps a black Wayland overlay with exclusive input capture **before** turning `DSI-1` off. The guard reports ready only after that surface has reached the compositor. On activity it wakes the display but retains the overlay until the entire touch/button/key gesture has ended, with a short quiet interval to consume trailing events. Only then is the dashboard exposed.

The overlay protects dashboard content, popups, and the Home Assistant toolbar. It captures multiple touch contacts and held keys until they are released. A compositor wake notification without a routed touch releases the guard after a short fallback interval. Resume signals target only the main guard process so display power helpers are not interrupted.

labwc starts the idle service after importing the graphical session environment. Stopping the service stops any active guard and turns the display back on. Guard startup failures leave the display on.

| Item | Path on the Pi |
| --- | --- |
| Service | `/home/paneluser/.config/systemd/user/ha-panel-idle.service` |
| Wake guard service | `/home/paneluser/.config/systemd/user/ha-panel-wake-guard.service` |
| Wake guard | `/home/paneluser/.local/bin/ha-panel-wake-guard.py` |
| Timeout | `/home/paneluser/.config/ha-panel/idle.conf` |
| Startup | `/home/paneluser/.config/labwc/autostart` |

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

## Checks

The guard logic tests cover held touches, release and quiet time, trailing pointer events, mixed held inputs, and wake notifications without delivered touches:

```sh
python3 -m unittest discover -s tests -p 'test_wake_guard.py'
```

For a physical check, put the panel to sleep, then tap over a control. The first tap should reveal the dashboard without operating that control.
