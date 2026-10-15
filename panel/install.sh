#!/bin/bash
# Run as the graphical desktop user. The compiled keyboard is a prerequisite.
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
url=${1:?Usage: bash panel/install.sh https://your-home-assistant/dashboard [patched-squeekboard]}
keyboard=${2:-$HOME/.local/lib/ha-panel/squeekboard}
case "$url" in http://*|https://*) ;; *) echo 'URL must use HTTP or HTTPS' >&2; exit 1 ;; esac
if [ ! -x "$keyboard" ]; then
    echo 'Provide a compiled overlay Squeekboard binary; see panel/docs/keyboard.md.' >&2
    exit 1
fi
for program in chromium curl labwc systemctl swayidle wlopm python3 gsettings; do
    command -v "$program" >/dev/null
done
python3 -c 'import gi; gi.require_version("GtkLayerShell", "0.1"); gi.require_foreign("cairo")'
python3 -c 'import websocket'
# The keyboard installer replaces its destination; preserve a reused binary first.
keyboard_copy=$(mktemp)
trap 'rm -f "$keyboard_copy"' EXIT
install -m 755 "$keyboard" "$keyboard_copy"
bash "$source_dir/install-kiosk.sh" "$url"
bash "$source_dir/install-keyboard.sh" "$keyboard_copy"
bash "$source_dir/install-idle.sh" 300
bash "$source_dir/install-remote.sh"
printf 'Panel installed. Start ha-panel in the desktop session or reboot.\n'
