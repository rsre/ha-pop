# Home Assistant panel

A dedicated touchscreen controller for Home Assistant. Powering on the panel opens the control dashboard in fullscreen Chromium, with no desktop interaction required.

| Component | Details |
| --- | --- |
| Computer | Raspberry Pi 5 |
| Display | Raspberry Pi Touch Display 2, 7-inch |
| Storage | 64 GB microSD |
| Panel address | `192.0.2.10` / `panel.local` |
| Home Assistant | `https://homeassistant.example/` |
| Touchscreen dashboard | [`Panel`](https://homeassistant.example/dashboard-panel/casa), portrait 720 × 1280 |
| Screen sleep | After 5 minutes idle; first tap wakes without operating controls |
| Doorbell | Home Assistant wakes the panel and opens the Portón video popup |
| Operating system | Raspberry Pi OS 64-bit, Debian 13.7 (trixie), image 2026-10-06 |
| Hostname / desktop user | `panel` / `paneluser` |
| Deployment | Portrait dashboard with seven popups, touch wake, and remote commands |

The Pi is a browser client. Home Assistant continues running on its existing server.

SSH: `ssh paneluser@panel.local -i ~/.ssh/homeassistant` (or use `192.0.2.10`).

The [touchscreen dashboard guide](docs/dashboard.md) covers its sections, popup controls, source, deployment, tests, and rollback.

The [remote control guide](docs/remote-control.md) covers Home Assistant wake commands and the doorbell video automation.

The [screen sleep guide](docs/screen-sleep.md) covers idle display power-off and touch wake.

See [setup and maintenance](docs/panel-setup.md) for installation, operating checks, and recovery procedures. No passwords, private keys, or browser profiles belong in this repository.

The [touchscreen keyboard notes](docs/keyboard.md) cover Chromium input support and the keyboard layer fix required for fullscreen use.

The [Home camera layout notes](docs/example-camera.md) describe the installed VideoLink camera sizing and frontend updates.

[CHANGELOG.md](CHANGELOG.md) records project changes, deployment history, and verification results.
