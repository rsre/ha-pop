#!/bin/bash
# Run with sudo as the panel desktop account: sudo bash panel/install-reboot.sh
# Installs the fixed root units that watch for reboot requests. The panel account
# is never granted sudo access; the reboot command exists only in these files.
# Safe to re-run: unchanged units are left in place and only replaced files are backed up.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run with sudo so the fixed units are installed as root: sudo bash panel/install-reboot.sh' >&2
    exit 1
fi
if [ -z "${SUDO_USER:-}" ]; then
    echo 'Run with sudo as the panel desktop account so its home directory is used.' >&2
    exit 1
fi
panel_home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
if [ -z "$panel_home" ] || [ ! -d "$panel_home/.config/ha-panel" ]; then
    echo 'Could not find the panel configuration directory. Run panel/install-remote.sh as the panel account first.' >&2
    exit 1
fi
trigger="$panel_home/.config/ha-panel/reboot-request"
rendered=$(mktemp)
trap 'rm -f "$rendered"' EXIT
python3 - "$source_dir/ha-panel-reboot.path" "$trigger" > "$rendered" <<'PY'
import sys
sys.stdout.write(open(sys.argv[1]).read().replace('@PANEL_TRIGGER@', sys.argv[2]))
PY
backup=/var/backups/ha-panel/reboot-$(date +%Y%m%dT%H%M%S)-$$
ensure_backup() { [ -d "$backup" ] || mkdir -p "$backup"; }
changed=0
cmp -s /etc/systemd/system/ha-panel-reboot.path "$rendered" || changed=1
cmp -s /etc/systemd/system/ha-panel-reboot.service "$source_dir/ha-panel-reboot.service" || changed=1
if [ "$changed" -eq 0 ] && systemctl is-enabled ha-panel-reboot.path >/dev/null 2>&1 && systemctl is-active ha-panel-reboot.path >/dev/null 2>&1; then
    printf 'Reboot service already installed and watching %s. Nothing to do.\n' "$trigger"
    exit 0
fi
install_unit() {
    if [ -e "/etc/systemd/system/$1" ]; then
        cmp -s "/etc/systemd/system/$1" "$2" || { ensure_backup; cp -p "/etc/systemd/system/$1" "$backup/$1"; }
    else
        ensure_backup
        printf '%s\n' "/etc/systemd/system/$1" >> "$backup/previously-absent"
    fi
    install -m 644 -o root -g root "$2" "/etc/systemd/system/$1"
}
install_unit ha-panel-reboot.path "$rendered"
install_unit ha-panel-reboot.service "$source_dir/ha-panel-reboot.service"
systemctl daemon-reload
systemctl enable ha-panel-reboot.path
systemctl restart ha-panel-reboot.path
systemctl is-enabled ha-panel-reboot.path >/dev/null
systemctl is-active ha-panel-reboot.path >/dev/null
if [ -d "$backup" ]; then
    printf 'Reboot service installed and watching %s. Backup: %s\n' "$trigger" "$backup"
else
    printf 'Reboot service installed and watching %s.\n' "$trigger"
fi
