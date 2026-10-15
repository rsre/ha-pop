#!/bin/bash
# Run as the desktop user on Raspberry Pi OS with labwc.
set -euo pipefail
url=${1:?Usage: bash panel/install-kiosk.sh https://your-home-assistant/}
case "$url" in
    http://*|https://*) ;;
    *) echo 'URL must use HTTP or HTTPS' >&2; exit 1 ;;
esac
url=$(python3 - "$url" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
url = urlsplit(sys.argv[1])
query = dict(parse_qsl(url.query))
query['ha_pop_kiosk'] = '1'
print(urlunsplit(url._replace(query=urlencode(query))))
PY
)
for program in chromium curl labwc systemctl; do
    command -v "$program" >/dev/null
done
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
backup="$HOME/.local/state/ha-panel/backups/$(date +%Y%m%dT%H%M%S)-$$"
mkdir -p "$backup" "$HOME/.local/bin" "$HOME/.config/systemd/user" \
    "$HOME/.config/labwc" "$HOME/.config/ha-panel" "$HOME/.local/share/ha-panel/chromium"
chmod 700 "$HOME/.config/ha-panel" "$HOME/.local/share/ha-panel" \
    "$HOME/.local/share/ha-panel/chromium"
for item in .config/labwc/autostart .config/ha-panel/url .config/systemd/user/ha-panel.service .local/bin/ha-panel; do
    if [ -e "$HOME/$item" ]; then
        mkdir -p "$backup/$(dirname "$item")"
        cp -p "$HOME/$item" "$backup/$item"
    else
        printf '%s\n' "$item" >> "$backup/previously-absent"
    fi
done
install -m 755 "$source_dir/ha-panel" "$HOME/.local/bin/ha-panel"
install -m 644 "$source_dir/ha-panel.service" "$HOME/.config/systemd/user/ha-panel.service"
printf '%s\n' "$url" > "$HOME/.config/ha-panel/url"
chmod 600 "$HOME/.config/ha-panel/url"
autostart="$HOME/.config/labwc/autostart"
if [ ! -e "$autostart" ]; then
    printf '#!/bin/sh\n# Retain Raspberry Pi desktop services and on-screen keyboard.\n. /etc/xdg/labwc/autostart\n' > "$autostart"
fi
if ! grep -q '^# BEGIN ha-panel$' "$autostart"; then
    cat >> "$autostart" <<'AUTOSTART'

# BEGIN ha-panel
systemctl --user import-environment WAYLAND_DISPLAY DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE
systemctl --user restart ha-panel.service
# END ha-panel
AUTOSTART
fi
systemctl --user daemon-reload
printf 'Installed. Backup: %s\nStart in the desktop session, or reboot, to launch the kiosk.\n' "$backup"
