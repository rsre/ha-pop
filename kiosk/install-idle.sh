#!/bin/bash
set -euo pipefail
seconds=${1:-300}
if ! [[ "$seconds" =~ ^[0-9]+$ ]] || (( 10#$seconds < 10 )); then
    echo 'Usage: bash kiosk/install-idle.sh [idle-seconds, at least 10]' >&2
    exit 1
fi
for program in swayidle wlopm python3; do command -v "$program" >/dev/null; done
python3 -c 'import gi; gi.require_version("GtkLayerShell", "0.1"); gi.require_foreign("cairo")'
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
autostart="$HOME/.config/labwc/autostart"
grep -q '^# BEGIN ha-panel$' "$autostart"
backup="$HOME/.local/state/ha-panel/backups/idle-$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup" "$HOME/.config/ha-panel" "$HOME/.config/systemd/user" "$HOME/.local/bin"
for item in .config/labwc/autostart .config/ha-panel/idle.conf .config/systemd/user/ha-panel-idle.service .config/systemd/user/ha-panel-wake-guard.service .local/bin/ha-panel-wake-guard.py; do
    if [ -e "$HOME/$item" ]; then
        mkdir -p "$backup/$(dirname "$item")"
        cp -p "$HOME/$item" "$backup/$item"
    else
        printf '%s\n' "$item" >> "$backup/previously-absent"
    fi
done
if systemctl --user cat ha-panel-idle.service >/dev/null 2>&1; then
    systemctl --user stop ha-panel-idle.service
fi
install -m 755 "$source_dir/ha-panel-wake-guard.py" "$HOME/.local/bin/ha-panel-wake-guard.py"
install -m 644 "$source_dir/ha-panel-wake-guard.service" "$HOME/.config/systemd/user/ha-panel-wake-guard.service"
install -m 644 "$source_dir/ha-panel-idle.service" "$HOME/.config/systemd/user/ha-panel-idle.service"
printf 'HA_PANEL_IDLE_SECONDS=%s\n' "$seconds" > "$HOME/.config/ha-panel/idle.conf"
if ! grep -q 'start ha-panel-idle.service' "$autostart"; then
    sed -i '/^systemctl --user restart ha-panel.service/a\
systemctl --user start ha-panel-idle.service' "$autostart"
fi
systemctl --user daemon-reload
systemctl --user restart ha-panel-idle.service
printf 'Screen idle timeout: %s seconds\nBackup: %s\n' "$seconds" "$backup"
