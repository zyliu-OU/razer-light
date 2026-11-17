#!/bin/bash
# Installs the Razer Blade 16 speaker fix system-wide. Run with sudo.
# Uninstall: sudo ./install.sh --uninstall
set -e
[ "$EUID" -eq 0 ] || { echo "run with sudo"; exit 1; }
SRC="$(dirname "$(readlink -f "$0")")"
LIB=/usr/local/lib/razer-speaker-fix
UNIT=/etc/systemd/system/razer-speaker-fix.service
HOOK=/usr/lib/systemd/system-sleep/razer-speaker-fix
PROTECT=/etc/wireplumber/wireplumber.conf.d/51-razer-speaker-protect.conf

if [ "$1" = "--uninstall" ]; then
    systemctl disable --now razer-speaker-fix.service 2>/dev/null || true
    rm -rf "$LIB" "$UNIT" "$HOOK" "$PROTECT"
    systemctl daemon-reload
    echo "uninstalled; run 'systemctl --user restart wireplumber' (no sudo) or log out to drop the speaker filter"
    exit 0
fi

install -d -m 755 "$LIB"
install -m 755 "$SRC/razer_speaker_fix.py" "$LIB/"
install -m 644 "$SRC/razer_blade16_alc298_verbs.txt" "$LIB/"
install -m 644 "$SRC/razer-speaker-fix.service" "$UNIT"
install -m 755 "$SRC/sleep-hook" "$HOOK"
install -D -m 644 "$SRC/51-razer-speaker-protect.conf" "$PROTECT"
systemctl daemon-reload
systemctl enable razer-speaker-fix.service
systemctl restart razer-speaker-fix.service
systemctl --no-pager status razer-speaker-fix.service | head -12
echo "speaker protection filter installed; run 'systemctl --user restart wireplumber' (no sudo) or log out and in to activate it"
