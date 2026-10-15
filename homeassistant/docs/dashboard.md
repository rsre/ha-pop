# Portrait dashboard

The integration creates an editable native Lovelace dashboard at `/<dashboard-path>/home`. Its layout targets a 720 × 1280 portrait display, including Home Assistant's toolbar. The frontend is bundled in [`custom_components/ha_pop/frontend`](../../custom_components/ha_pop/frontend).

| Section | Interaction |
| --- | --- |
| Camera | Snapshot; tap to open live video |
| Lighting | Large direct controls for example kitchen, garage, and exterior entities |
| Equipment | Heating, hot-water, washer, and dryer summaries with detail popups |
| Vacuum | Status and popup commands |

The camera selected during integration setup and the integration's popup-command entity are wired automatically. The other entity IDs are illustrative defaults. Edit the custom card configuration in the dashboard UI to map them to your devices. Missing entities disable direct controls. The hot-water example is a read-only sensor.

The camera popup uses the native HA live-camera card when no video/talk card is installed. If VideoLink is available, the popup uses it automatically. Camera cards are removed on close to release their media. Snapshots refresh every 30 seconds.

Popups close using the close button, Escape, or a tap outside; focus returns to the trigger. Native HA detail dialogs can take over from a popup. Repeated commands cannot restart an already-open camera popup. Direct controls suppress duplicate pending calls and show command failures.

The integration supplies the frontend automatically. No dashboard resources or files under `/config/www` need to be maintained. Upgrade it through HACS and reload the panel browser afterward. The saved layout is retained across integration reloads and updates.

The layout checks in [`tests/verify-layout.js`](../tests/verify-layout.js) run in a browser at 720 × 1280 and check overflow, touch target sizes, section boundaries, popup fit, focus, and cleanup. They open details without operating devices. Browser unit tests run with `node --test homeassistant/tests/panel.test.cjs` from the repository root.
