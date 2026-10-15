# Touchscreen keyboard

The panel uses Squeekboard. Chromium needs `--enable-wayland-ime --wayland-text-input-version=3` to request text input through Wayland.

The Raspberry Pi keyboard package requests the `TOP` display layer, which labwc puts below fullscreen Chromium. Its D-Bus `Visible` property can be true while the keyboard is hidden behind the browser. This is reported in [Raspberry Pi's keyboard repository](https://github.com/raspberrypi-ui/squeekboard/issues/13) and is visible in the [panel source](https://github.com/raspberrypi-ui/squeekboard/blob/master/src/panel.c).

The repository's [patch](../../panel/squeekboard-overlay.patch) changes the requested layer to `OVERLAY`. A dedicated user service runs that compiled keyboard instead of the stock desktop autostart entry. The distribution's keyboard binary is preserved. This setup is intended for this dedicated panel: the overlay keyboard can also draw above other fullscreen surfaces.

| Purpose | Path on the Pi |
| --- | --- |
| Keyboard binary | `$HOME/.local/lib/ha-panel/squeekboard` |
| User service | `$HOME/.config/systemd/user/ha-panel-keyboard.service` |
| Stock startup override | `$HOME/.config/autostart/squeekboard.desktop` |
| Source and logs | `$HOME/ha-panel-keyboard-build` |

## Rebuild

The build uses the official Raspberry Pi source package `1.43.1-1+rpt1`, matching the installed package. Compiler and Rust dependencies use about 1 GB of additional SD space. Enable Debian source repositories before installing build dependencies.

On the Pi, as `ha`, with this repository available:

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
patch -p1 < $HOME/.local/share/ha-panel-source/panel/squeekboard-overlay.patch
patch -p1 < $HOME/.local/share/ha-panel-source/panel/squeekboard-test-fixture.patch
dpkg-buildpackage -b -us -uc -j2
bash $HOME/.local/share/ha-panel-source/panel/install-keyboard.sh "$PWD/_build/src/squeekboard"
```

Do not install the generated `.deb` files: only the compiled binary is copied into the panel's private installation. Keep the source and build logs for maintenance. Rebuild when relevant keyboard or library updates require it; distribution keyboard updates do not update this separate copy.

The source package's test fixture omits the `name` field added to `OutputState` by the Raspberry Pi patches, preventing its tests from compiling. The second patch adds `name: None` to that fixture. It changes no runtime behavior.

## Operation and recovery

```sh
systemctl --user status ha-panel-keyboard --no-pager
systemctl --user restart ha-panel-keyboard
busctl --user get-property sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 Visible
busctl --user call sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0 SetVisible b true
```

Tap a text field to request the keyboard; tap outside text fields to dismiss it. To restore the original keyboard, stop `ha-panel-keyboard`, restore the backed-up labwc startup file, and remove the `~/.config/autostart/squeekboard.desktop` override. Log out and back in or reboot. The installer records original files under `~/.local/state/ha-panel/backups/keyboard-*`.
