# Home Assistant touch panel

Deployment notes for a Raspberry Pi 5 with a 7-inch Touch Display 2 (720 × 1280), using [TouchKio](https://github.com/leukipp/touchkio) to display a Home Assistant dashboard.

This repository contains deployment documentation. TouchKio supplies the kiosk application and device controls.

## Prepare the Pi

Use Raspberry Pi OS **64-bit with Desktop**, with labwc and desktop automatic login enabled for the panel account. Configure networking, SSH, display orientation, and touch alignment using Raspberry Pi OS settings.

Create:

- a Home Assistant dashboard in the HA UI
- a dedicated regular user for the panel
- a Mosquitto account for the panel

## Install Touchkio in the Raspberry Pi

Run these commands in a terminal **on the Pi**, as the desktop account, without prefixing the installer with sudo:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/leukipp/touchkio/main/install.sh)
```

The config used is:

```json
{
  "web_url": [
    "https://ha.rsanzr.com"
  ],
  "web_theme": "dark",
  "web_zoom": "1.25",
  "web_widget": "true",
  "web_pager": "true",
  "mqtt_url": "mqtt://ha.rsanzr.com:1883",
  "mqtt_user": "kiosk",
  "mqtt_password": "********************",
  "mqtt_discovery": "homeassistant",
  "app_disable": [],
  "app_reset": []
}
```

Reboot and verify automatic login, kiosk startup, persistent HA login, scrolling, keyboard input, and touch-to-wake.

### Maintenance

Reconfigure with the service stopped:

```bash
systemctl --user stop touchkio.service
touchkio --setup
systemctl --user start touchkio.service
```

Settings and login data live in `~/.config/touchkio/`; logs are under its `logs/` directory. Keep this directory private.

To update, download and review the installer again, then run:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/leukipp/touchkio/main/install.sh) update
```

Use `systemctl --user restart touchkio.service` after configuration changes.
For problems, consult the [upstream troubleshooting guide](https://github.com/leukipp/touchkio#issues) and [hardware FAQ](https://github.com/leukipp/touchkio/blob/main/HARDWARE.md#faq).

## Install kiosk-mode in Home Assistant

[kiosk-mode](https://github.com/NemesisRE/kiosk-mode#installation) hides Home Assistant's header and sidebar inside TouchKio.

1. In **HACS**, search for **Kiosk Mode** and download it.
2. Reload the dashboard in TouchKio. Set its `web_url` to your dashboard with `?kiosk`, for example:

   ```json
   "web_url": ["https://ha.rsanzr.com/dashboard-panel/home?kiosk"]
   ```

   Replace the dashboard path with yours. Use `&kiosk` if the URL already has query parameters, then restart TouchKio.

Alternatively, for dashboard-wide settings, create a dashboard from scratch, open **Edit dashboard → Raw configuration editor**, and add this alongside the existing `views:` key:

```yaml
kiosk_mode:
  kiosk: true
```

Refresh after saving. To temporarily restore navigation for editing, open the dashboard with `?disable_km` (or `&disable_km`). Verify the header and sidebar disappear on the panel and return with this override.
