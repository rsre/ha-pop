#!/bin/bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
autostart="$HOME/.config/labwc/autostart"
grep -q 'start ha-panel-idle.service' "$autostart"
backup="$HOME/.local/state/ha-panel/backups/remote-$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup" "$HOME/.config/ha-panel" "$HOME/.config/systemd/user" "$HOME/.local/bin"
for item in .config/labwc/autostart .config/systemd/user/ha-panel-remote.service .local/bin/ha-panel-remote.py; do
    if [ -e "$HOME/$item" ]; then
        mkdir -p "$backup/$(dirname "$item")"
        cp -p "$HOME/$item" "$backup/$item"
    else
        printf '%s\n' "$item" >> "$backup/previously-absent"
    fi
done
# Preserve the shared credential on reinstall. Never print it.
if [ ! -e "$HOME/.config/ha-panel/remote-token" ]; then
    (umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > "$HOME/.config/ha-panel/remote-token")
fi
chmod 600 "$HOME/.config/ha-panel/remote-token"
install -m 755 "$source_dir/ha-panel-remote.py" "$HOME/.local/bin/ha-panel-remote.py"
install -m 644 "$source_dir/ha-panel-remote.service" "$HOME/.config/systemd/user/ha-panel-remote.service"
if ! grep -q 'start ha-panel-remote.service' "$autostart"; then
    sed -i '/^systemctl --user start ha-panel-idle.service/a\
systemctl --user start ha-panel-remote.service' "$autostart"
fi
systemctl --user daemon-reload
systemctl --user restart ha-panel-remote.service
printf 'Remote wake installed. Backup: %s\n' "$backup"
