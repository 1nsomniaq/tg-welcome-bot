# Deploy — Hetzner Cloud VPS

Small Ubuntu VPS running the bot under `systemd`. State lives in `/opt/tg-bot/chats.json` on the server.

## 1. Create the server

1. Register at https://console.hetzner.cloud (Euro card works).
2. Add your SSH public key (`~/.ssh/id_ed25519.pub` — generate with `ssh-keygen -t ed25519` if you don't have one).
3. Create a new project → **Add Server**:
   - Location: any EU (Nuremberg / Falkenstein / Helsinki).
   - Image: **Ubuntu 24.04**.
   - Type: **CX22** (~€4.5/mo) — plenty for a welcome bot.
   - SSH key: pick the one you added.
4. Copy the public IPv4 — that's your `SERVER`.

## 2. Bootstrap the box (once)

From your laptop:

```sh
SERVER=root@YOUR.IP
scp -r deploy $SERVER:/root/
ssh $SERVER 'bash /root/deploy/bootstrap.sh'
```

This installs Python, creates the `tgbot` user, `/opt/tg-bot`, and enables the systemd unit.

## 3. Place the `.env`

```sh
scp .env $SERVER:/opt/tg-bot/.env
ssh $SERVER 'chown tgbot:tgbot /opt/tg-bot/.env && chmod 600 /opt/tg-bot/.env'
```

## 4. Push code & start

```sh
SERVER=root@YOUR.IP ./deploy/push.sh
```

The script rsyncs the tree (minus `.git`, `.venv`, `.env`, `chats.json`), rebuilds the venv, and restarts `tg-bot.service`.

## 5. Observe

```sh
ssh $SERVER 'journalctl -u tg-bot -f'          # live logs
ssh $SERVER 'systemctl status tg-bot'          # health
```

## Updating

Commit locally, then re-run `./deploy/push.sh` — no server-side steps needed.

## State & backups

`chats.json` (per-chat rules / captcha / TTL / log_chat overrides) lives at `/opt/tg-bot/chats.json`. Back it up with:

```sh
scp $SERVER:/opt/tg-bot/chats.json ./chats.json.backup
```
