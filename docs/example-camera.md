# Home camera card layout

On 2026-10-15, the custom `videolink-doorbell` card for `camera.doorbell` rendered at 443.5 px tall on the panel, while its five-row Sections grid slot reserved only 312 px. The following “Sala de Máquinas” section therefore overlapped the camera and its controls.

The custom card reports `getGridOptions()` as `{ rows: 5, columns: 12, min_rows: 3, min_columns: 6 }`. Its height varies with video dimensions and width, so a fixed five-row allocation is insufficient. The matching source is in the sibling VideoLink repository at `frontend/videolink-doorbell.js`.

Add this to the existing camera card configuration, preserving its other settings:

```yaml
grid_options:
  columns: 12
  rows: auto
```

Home Assistant merges explicit [card grid options](https://raw.githubusercontent.com/home-assistant/frontend/dev/src/panels/lovelace/cards/hui-card.ts) over the custom card's defaults. Its [grid sizing code](https://raw.githubusercontent.com/home-assistant/frontend/dev/src/panels/lovelace/common/compute-card-grid-size.ts) supports automatic rows.

A temporary browser preview removed the fixed-height allocation: the slot then matched the camera's 443.5 px height, and the following section started 24 px after the camera ended. Temporary browser diagnostics and the preview have since been removed; the panel uses its normal startup configuration.

The VideoLink frontend source in `/Users/example/Documents/GitHub/VideoLink` has now been fixed at version `0.12.59`: video cards return `rows: "auto"` from `getGridOptions()`; audio-only cards retain their compact sizing. The HACS bundle and its cache version are synchronized. All 29 card tests pass, including the new video sizing regression, and bundle consistency and whitespace checks pass. The standalone build is at `/tmp/videolink-card-0.12.59/videolink-doorbell-card-0.12.59.zip` on the development computer.

The user deployed the update on 2026-10-15. Verification from the Pi confirmed Home Assistant serves version `0.12.59` with automatic video row height. After forcing a cache-bypassing reload, a panel screenshot confirmed the entire camera and its talk controls fit above the “Sala de Máquinas” heading without overlap. No dashboard YAML override was needed.

For future frontend updates, force-reload the kiosk after deploying. Run as `paneluser` on the Pi:

```sh
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
wlrctl toplevel focus app_id:chromium
wlrctl keyboard type r modifiers CTRL,SHIFT
```

The panel account remains a non-admin. During this repair the existing local server alias at `192.0.2.20:22` refused the connection, and the Tailscale alias at `192.0.2.30:22` timed out; deployment was performed by the user.
