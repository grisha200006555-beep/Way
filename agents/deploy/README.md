# Deploying agents on a VPS

Two options: **Docker (easier)** or **systemd (more control)**. Pick one.

## 0. Prepare the VPS

SSH in as root (or a sudoer):

```bash
adduser --disabled-password --gecos "" agents
mkdir -p /opt/agents && chown agents:agents /opt/agents
```

## 1a. Docker deployment (recommended)

```bash
apt-get update && apt-get install -y docker.io docker-compose-plugin git
su - agents
cd /opt/agents
git clone <your repo url> .
cp .env.example .env
nano .env   # fill in ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, WEB_TOKEN
docker compose up -d --build
docker compose logs -f
```

That's it. Dashboard at `http://<VPS_IP>:8000/?token=<WEB_TOKEN>`.

## 1b. Systemd deployment (no Docker)

```bash
apt-get install -y python3 python3-venv git
su - agents
cd /opt/agents
git clone <your repo url> .
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt psutil
cp .env.example .env
nano .env

# As root, install the service:
cp deploy/agents.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now agents
journalctl -u agents -f
```

## 2. Get your Telegram bot

1. Open Telegram → @BotFather → `/newbot` → follow prompts.
2. Copy the token into `.env` (`TELEGRAM_BOT_TOKEN=`).
3. Restart (`docker compose restart` or `systemctl restart agents`).
4. Open your new bot in Telegram, send `/start`. It prints your numeric id.
5. Paste that id into `.env` (`TELEGRAM_OWNER_ID=`) and restart again.

After that, only you can talk to the bot.

## 3. (Optional) GitHub access

1. github.com → Settings → Developer settings → Fine-grained tokens.
2. Scope: repos you want Sam to read; permissions: Contents read, Issues read+write, PRs read.
3. Paste into `.env` (`GITHUB_TOKEN=`).

## 4. (Optional) Reverse proxy + HTTPS

Don't expose port 8000 directly long-term. Front it with nginx or Caddy:

```caddy
# /etc/caddy/Caddyfile
mission-control.yourdomain.com {
    reverse_proxy localhost:8000
}
```

Caddy auto-provisions Let's Encrypt. The `WEB_TOKEN` query param then becomes
your only public-facing secret — rotate it occasionally.

## 5. Wiring Gmail & Google Calendar

This step is **manual and one-time** because Google OAuth requires a browser
consent flow.

1. https://console.cloud.google.com/ → new project → enable Gmail API + Calendar API.
2. OAuth consent screen → External → fill in basics → add yourself as a test user.
3. Credentials → Create credentials → OAuth client ID → Desktop app → download
   `credentials.json`.
4. Copy `credentials.json` to `/opt/agents/data/`.
5. Run the one-time consent flow locally (it'll write `token.json` next to it):

```bash
pip install google-api-python-client google-auth-oauthlib
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'data/credentials.json',
    ['https://www.googleapis.com/auth/gmail.modify',
     'https://www.googleapis.com/auth/calendar'])
creds = flow.run_local_server(port=0)
open('data/token.json', 'w').write(creds.to_json())
"
```

6. Open `src/tools/gmail.py` and `src/tools/gcal.py`, replace the STUB bodies
   with real Gmail/Calendar API calls (build service from `token.json`).
7. Restart.

I left the function signatures + tool schemas in place so Alice already knows
*how* to call them — only the implementation needs to land.

## 6. Costs to watch

- Haiku is the default; ~$1 per million tokens. A typical Alice/Sam task uses
  5-30k tokens depending on tool iterations. Budget $5-15/month for casual use.
- If you switch the model to Sonnet/Opus in `.env`, monitor the bill daily for
  the first week.

## 7. Logs and troubleshooting

- Docker: `docker compose logs -f agents`
- Systemd: `journalctl -u agents -f`
- DB inspection: `sqlite3 data/agents.db 'select * from task order by id desc limit 10;'`
