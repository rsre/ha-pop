#!/bin/bash
# Install the separately built overlay keyboard for the desktop account.
set -euo pipefail
binary=${1:?Usage: bash kiosk/install-keyboard.sh /path/to/patched/squeekboard}
test -x "$binary"
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
autostart="$HOME/.config/labwc/autostart"
grep -q '^# BEGIN ha-panel$' "$autostart"
backup="$HOME/.local/state/ha-panel/backups/keyboard-$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup" "$HOME/.local/lib/ha-panel" "$HOME/.config/autostart" \
    "$HOME/.config/systemd/user"
for item in .config/labwc/autostart .config/autostart/squeekboard.desktop .config/systemd/user/ha-panel-keyboard.service .local/lib/ha-panel/squeekboard; do
    if [ -e "$HOME/$item" ]; then
        mkdir -p "$backup/$(dirname "$item")"
        cp -p "$HOME/$item" "$backup/$item"
    else
        printf '%s\n' "$item" >> "$backup/previously-absent"
    fi
done
systemctl --user stop ha-panel-keyboard.service 2>/dev/null || true
install -m 755 "$binary" "$HOME/.local/lib/ha-panel/squeekboard"
install -m 644 "$source_dir/ha-panel-keyboard.service" "$HOME/.config/systemd/user/ha-panel-keyboard.service"
# The dedicated service replaces the distribution's desktop autostart entry.
cat > "$HOME/.config/autostart/squeekboard.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Squeekboard
Hidden=true
DESKTOP
if ! grep -q 'start ha-panel-keyboard.service' "$autostart"; then
    sed -i '/^systemctl --user restart ha-panel.service/i\
if [ -x "$HOME/.local/lib/ha-panel/squeekboard" ]; then\
    systemctl --user start ha-panel-keyboard.service\
fi' "$autostart"
fi
systemctl --user daemon-reload
pkill -x squeekboard || true
gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true
systemctl --user start ha-panel-keyboard.service
printf 'Keyboard installed. Backup: %s\n' "$backup"
