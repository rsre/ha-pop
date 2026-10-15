# Home camera card layout

The installed VideoLink frontend is version `0.12.59`. Video cards use `rows: "auto"` from `getGridOptions()` so their Sections grid slots fit the rendered video and controls. Audio-only cards retain compact sizing. The Home camera needs no dashboard YAML sizing override.

The source is in the sibling VideoLink repository at `frontend/videolink-doorbell.js`. The HACS bundle and its cache version must stay synchronized when updating the card.

The dedicated [portrait dashboard](dashboard.md) shows a snapshot on its main screen and creates the VideoLink card inside the Portón popup. It uses `video_fit: contain` to preserve the full camera image.

After deploying a frontend update, force-reload the kiosk as `paneluser` on the Pi:

```sh
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
wlrctl toplevel focus app_id:chromium
wlrctl keyboard type r modifiers CTRL,SHIFT
```
