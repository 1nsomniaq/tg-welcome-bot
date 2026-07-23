#!/usr/bin/env bash
# Push local code to the server and restart the bot.
# Usage: SERVER=user@ip ./deploy/push.sh
#   e.g. SERVER=root@203.0.113.7 ./deploy/push.sh
set -euo pipefail

: "${SERVER:?set SERVER=user@host (e.g. root@1.2.3.4)}"

REMOTE_DIR=/opt/tg-bot
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ">>> rsync $LOCAL_DIR -> $SERVER:$REMOTE_DIR"
rsync -az --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.env' \
    --exclude 'chats.json' \
    --exclude '.idea' \
    --exclude '.vscode' \
    "$LOCAL_DIR"/ "$SERVER:$REMOTE_DIR/"

echo ">>> fix ownership + (re)create venv + install deps + restart"
ssh "$SERVER" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/tg-bot
chown -R tgbot:tgbot /opt/tg-bot
if [ ! -x .venv/bin/python ]; then
    sudo -u tgbot python3 -m venv .venv
fi
sudo -u tgbot .venv/bin/pip install --quiet --upgrade pip
sudo -u tgbot .venv/bin/pip install --quiet -r requirements.txt
systemctl restart tg-bot
sleep 1
systemctl --no-pager --lines=20 status tg-bot || true
REMOTE

echo ">>> done. Tail logs with:  ssh $SERVER 'journalctl -u tg-bot -f'"
