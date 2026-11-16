#!/bin/sh
# Install the script + systemd service so the color is applied on every boot.
set -e
cd "$(dirname "$0")"
install -m 755 razer_static.py /usr/local/bin/razer_static.py
install -m 644 razer-keyboard-color.service /etc/systemd/system/razer-keyboard-color.service
# Also re-apply just before suspend/hibernate (so the lid logo is on going into
# sleep) and again after waking
cat > /usr/lib/systemd/system-sleep/razer-keyboard-color <<'EOF'
#!/bin/sh
/usr/bin/python3 /usr/local/bin/razer_static.py 0 255 0 100 || true
EOF
chmod 755 /usr/lib/systemd/system-sleep/razer-keyboard-color
systemctl daemon-reload
systemctl enable --now razer-keyboard-color.service
systemctl status --no-pager razer-keyboard-color.service
