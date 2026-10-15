# Changelog

Project changes and verification history. Deployment addresses, account names, entity mappings, and private backup locations are intentionally excluded from the public record. Current setup is described in the [panel guide](panel/README.md) and [integration guide](custom_components/ha_pop/README.md).

## Unreleased — integration 0.2.0

- Consolidated Home Assistant guides and development tools under `custom_components/ha_pop/`, alongside the integration; removed the separate `homeassistant/` directory.

### Home Assistant integration

- Added a HACS-compatible `custom_components/ha_pop` integration with UI setup and reconfiguration, password-style token entry, stable panel identity, and authenticated connectivity validation.
- Added native Wake, Sleep, and Show doorbell button entities and an event entity to deliver popup commands only after successful waking.
- Bundled the frontend and an editable native dashboard. Saved dashboard edits survive integration reloads. Existing dashboards at the requested URL are protected from replacement.
- Added an importable doorbell automation blueprint. The resulting automation remains editable in the UI.
- Removed the SSH/Supervisor installer workflow in favor of HACS and UI configuration. Existing deployments remain untouched until explicitly migrated.
- Added native-camera fallback when no video/talk card is installed.
- Added authenticated Pi health checks and a persistent generated panel ID. Health checks do not wake the screen; existing wake/sleep commands remain compatible.
- Added offline client and integration lifecycle checks, and HACS/hassfest CI validation.

### Repository and publication

- Separated Pi software under `panel/` from Home Assistant support under `homeassistant/`. HACS requires the installable integration itself at repository-root `custom_components/ha_pop/`.
- Added a complete Pi installer while retaining component installers. Source reorganization does not change installed service names or token files.
- Added publication auditing and replaced deployment-specific examples with public placeholders. Private local snapshots are ignored.
- Sanitized historical deployment details and commit author metadata while preserving the sequence of historical commits. Remote publication is a separate user action.

## 2026-10-15

### Kiosk, keyboard, and touch input

- Configured a Raspberry Pi 5 and 7-inch Touch Display 2 as a portrait Chromium kiosk with automatic desktop login, a persistent browser profile, HTTP readiness checks, and service restart recovery. Initial reboot and process-exit recovery checks passed; SSH stayed available.
- Enabled Wayland input support. A separate Squeekboard build uses the overlay layer above fullscreen Chromium while preserving the distribution binary. Keyboard visibility, key entry, deletion, and physical login were confirmed.
- Built from the matching Raspberry Pi Squeekboard source. A test-only patch supplies the missing `OutputState.name` fixture field. The runtime binary compiled; the optional full upstream test build was stopped after login confirmation and was not reported as passing. Build dependencies use about 1 GB of additional space.
- Enabled native Goodix touch events rather than mouse emulation. Finger scrolling was confirmed after a compositor reload without restarting the browser.
- Investigated content displacement beyond screen borders. Restarting Chromium restored normal layout and retained login; viewport metrics were correct and the exact cause was not established.
- Investigated a reported reload on a dashboard subview Back action. Pointer and physical tests returned normally within the same document and service process. The original symptom was not reproduced; temporary diagnostics were removed without speculative navigation patches.

### Portrait dashboard — frontend 0.1.1

- Added a no-scroll dashboard with camera, lighting, equipment summaries, and vacuum controls. Seven detail popups use native HA cards, return focus, and release media on close.
- Fixed inherited line heights and section row sizing. Live checks passed at 720 × 1280, including a 56-pixel toolbar and a 720 × 1224 main card. All 12 main targets were at least 44 pixels and remained within their sections.
- Verified all seven popups fit without overflow or error cards. Rapid popup replacement and takeover by native HA details worked. Six original JavaScript tests covered commands, unavailable/offline behavior, duplicate suppression, error feedback, configuration, and entity validation.

### Guarded sleep

- Added five-minute display idle sleep without suspending the Pi or browser. Initial idle tests confirmed display power changes and physical touch wake.
- Added a compositor overlay to consume the entire first gesture after wake. Pointer tests showed the first click only wakes; subsequent clicks operate controls.
- Fixed a signal race that sent a wake notification to both the guard and its display power helper, leaving the black overlay visible. Signals target only the main guard process, and input handlers schedule dismissal before powering the display. Physical retesting passed.
- Five guard tests covered held gestures, release quiet time, trailing pointer events, mixed devices, and wake notifications without routed touch.
- Fixed fresh installation so a missing idle service does not cause failure. Fresh and repeat installer checks passed using isolated files and mocked Pi services.

### Remote commands — frontend 0.1.2

- Added an authenticated LAN wake endpoint, a five-minute wake hold, and a Home Assistant doorbell command. Repeated requests extend the hold; normal idle handling resumes afterward. An additional idle interval can keep the display on longer.
- Tested the automation actions from a guarded asleep screen. The display woke and live video played at 640 × 480 with ready state 4, without reloading the browser. Repeated rings and wake-only commands preserved the current video card.
- Verified the complete five-minute hold restored idle handling. Normal guarded sleep and another remote wake worked afterward. Temporary browser diagnostics were removed and their port closed.
- Added remote sleep and verified wake → sleep → wake. Sleep cancels the current wake hold while retaining guarded touch wake.
- Moved the initial package-defined scripts and automation into HA's UI-editable files, preserving script keys, automation ID, and UI edits. Configuration checks and reloads passed without restarting Core. UI editing APIs returned HTTP 200, and the automation remained enabled without duplicate IDs.
- Added the mDNS name `panel.local`; resolution and SSH were verified independently of the OS hostname.
- After these additions, all 24 tests passed: 17 Python and seven JavaScript tests. The directory split later passed 29 tests from isolated copies of each deployment directory.

### Documentation and validation scope

- Moved deployment history, investigations, and verification records into this changelog; guides describe current behavior and procedures.
- Recorded per-installation backups remain private under the Pi's backup directory and HA's backup directory. Browser profiles and credentials were not committed.
- A full reboot with the complete configuration, a physical doorbell ring, device-action acceptance checks, network-outage recovery, and the complete upstream keyboard test suite were outside the recorded live validation. The new 0.2.0 integration is tested offline with API doubles, not reported as live-validated on HA.
