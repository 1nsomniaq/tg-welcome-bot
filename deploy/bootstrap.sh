#!/usr/bin/env bash
# One-time server bootstrap. Run as root (or via sudo) on a fresh Ubuntu 24.04 box.
# Idempotent — safe to re-run.
set -euo pipefail

APP_DIR=/opt/tg-bot
APP_USER=tgbot

echo ">>> apt update + base packages"
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git ca-certificates

echo ">>> user + directory"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi
install -d -o "$APP_USER" -g "$APP_USER" -m 0750 "$APP_DIR"

echo ">>> systemd unit"
install -m 0644 "$(dirname "$0")/tg-bot.service" /etc/systemd/system/tg-bot.service
systemctl daemon-reload
systemctl enable tg-bot.service

echo ">>> done. Next steps:"
echo "  1) rsync the code into $APP_DIR (see deploy/push.sh)"
echo "  2) place $APP_DIR/.env with BOT_TOKEN=..."
echo "  3) systemctl start tg-bot && journalctl -u tg-bot -f"
