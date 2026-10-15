# Touchscreen keyboard

The panel uses Squeekboard. Chromium needs `--enable-wayland-ime --wayland-text-input-version=3` to request text input through Wayland. The original browser launcher lacked these flags.

There is a second issue: the Raspberry Pi keyboard package requests the `TOP` display layer, which labwc puts below fullscreen Chromium. Its D-Bus `Visible` property can be true while the keyboard is hidden behind the browser. This is reported in [Raspberry Pi's keyboard repository](https://github.com/raspberrypi-ui/squeekboard/issues/13) and is visible in the [panel source](https://github.com/raspberrypi-ui/squeekboard/blob/master/src/panel.c).

The repository's [patch](../kiosk/squeekboard-overlay.patch) changes the requested layer to `OVERLAY`. A dedicated user service runs that compiled keyboard instead of the stock desktop autostart entry. The distribution's keyboard binary is preserved. This setup is intended for this dedicated panel: the overlay keyboard can also draw above other fullscreen surfaces.

On 2026-10-15, deployed the overlay keyboard and verified it appears above Home Assistant in a display capture. A virtual pointer click on the keyboard entered `q` into the empty username field; clicking the keyboard's Backspace removed it. No login was submitted during that test. The user subsequently confirmed successful sign-in on the touchscreen. Both panel services are active. Startup is configured in labwc; the combined keyboard setup has not yet been tested through another reboot.

| Purpose | Path on the Pi |
| --- | --- |
| Keyboard binary | `/home/paneluser/.local/lib/ha-panel/squeekboard` |
| User service | `/home/paneluser/.config/systemd/user/ha-panel-keyboard.service` |
| Stock startup override | `/home/paneluser/.config/autostart/squeekboard.desktop` |
| Original-state backup | `/home/paneluser/.local/state/ha-panel/backups/keyboard-20261015T125923-24421` |
| Source and logs | `/home/paneluser/ha-panel-keyboard-build` |

## Rebuild

The build uses the official Raspberry Pi source package `1.43.1-1+rpt1`, matching the installed package. Compiler and Rust dependencies use about 1 GB of additional SD space. Enable Debian source repositories before installing build dependencies. During initial repair a temporary `/etc/apt/sources.list.d/ha-panel-build.sources` was used and subsequently removed; no original repository files were changed.

On the Pi, as `paneluser`, with this repository available:

```sh
sudo apt-get update
sudo apt-get --no-install-recommends -y build-dep squeekboard
mkdir -p ~/ha-panel-keyboard-build
cd ~/ha-panel-keyboard-build
curl -fSsO https://archive.raspberrypi.com/debian/pool/main/s/squeekboard/squeekboard_1.43.1-1+rpt1.dsc
curl -fSsO https://archive.raspberrypi.com/debian/pool/main/s/squeekboard/squeekboard_1.43.1.orig.tar.bz2
curl -fSsO https://archive.raspberrypi.com/debian/pool/main/s/squeekboard/squeekboard_1.43.1-1+rpt1.debian.tar.xz
sha256sum squeekboard_1.43.1.orig.tar.bz2 squeekboard_1.43.1-1+rpt1.debian.tar.xz
```

Expected SHA-256 hashes, respectively:

```text
f3ec511ffed23eda48ca44bfc4a0b4c8c9fc44c61f648f6ac0cae7856d84dadc
05de823ec9945a9f12c1a02960bc643d3420ff0cccc2e8890465c634269fdbaa
```

Then unpack, patch, compile, and run the package's tests:

```sh
dpkg-source -x squeekboard_1.43.1-1+rpt1.dsc patched-squeekboard
cd patched-squeekboard
patch -p1 < /home/paneluser/.local/share/ha-panel-source/kiosk/squeekboard-overlay.patch
patch -p1 < /home/paneluser/.local/share/ha-panel-source/kiosk/squeekboard-test-fixture.patch
dpkg-buildpackage -b -us -uc -j2
bash /home/paneluser/.local/share/ha-panel-source/kiosk/install-keyboard.sh "$PWD/_build/src/squeekboard"
```

Do not install the generated `.deb` files: only the compiled binary is copied into the panel's private installation. Keep the source and build logs for maintenance. Rebuild when relevant keyboard or library updates require it; distribution keyboard updates do not update this separate copy.

The source package's test fixture omits the `name` field added to `OutputState` by the Raspberry Pi patches, preventing its tests from compiling. The second patch adds `name: None` to that fixture. It changes no runtime behavior.

Validation: the runtime binary compiled successfully, both service units passed `systemd-analyze --user verify`, and keyboard visibility and text entry passed live checks. The initial package test run failed to compile the upstream fixture described above. After correcting the fixture, the optional full package test rebuild was stopped during dependency compilation once the user confirmed successful sign-in. The full upstream test suite is not reported as passing. Build logs remain in the source directory.

## Operation and recovery

```sh
systemctl --user status ha-panel-keyboard --no-pager
systemctl --user restart ha-panel-keyboard
busctl --user get-property sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 Visible
busctl --user call sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 SetVisible b true
```

Tap a text field to request the keyboard; tap outside text fields to dismiss it. To restore the original keyboard, stop `ha-panel-keyboard`, restore the backed-up labwc startup file, and remove the newly created `~/.config/autostart/squeekboard.desktop` override. Log out and back in or reboot. The installer records original files under `~/.local/state/ha-panel/backups/keyboard-*`.
