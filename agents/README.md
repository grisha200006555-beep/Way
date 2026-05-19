# Myndex-Lab-style AI agent team

A working skeleton of a multi-agent AI system you can run on a VPS — like in
the Макс Трейси / Myndex Lab video, but yours.

**Two agents out of the box:**

- **Alice** — personal assistant (email triage, calendar, replies).
- **Sam** — DevOps (monitors the VPS, reads GitHub issues, runs whitelisted shell commands).

**Three ways to talk to them:**

1. **Telegram bot** — primary, mobile-friendly. Send `alice: book me a haircut` or `sam: check disk space`.
2. **Web dashboard** — Mission Control at `http://your-vps:8000`, live status + queue.
3. **HTTP API** — same FastAPI app exposes `POST /tasks` for cron/webhooks/scripts.

## What's inside

```
agents/
├── src/
│   ├── main.py                  entry point (orchestrator + telegram + web)
│   ├── config.py                env-driven settings
│   ├── db.py                    SQLModel tables (tasks, agent state)
│   ├── orchestrator.py          task queue worker, dispatches to agents
│   ├── agents/
│   │   ├── base.py              Agent class with the Claude tool-use loop
│   │   ├── alice.py             personal assistant
│   │   └── sam.py               devops
│   ├── tools/
│   │   ├── registry.py          tool framework
│   │   ├── shell.py             sandboxed shell (whitelist + 30s timeout)
│   │   ├── github.py            list/read issues
│   │   ├── gmail.py             STUBS — see deploy/README.md to wire
│   │   └── gcal.py              STUBS — see deploy/README.md to wire
│   ├── interfaces/
│   │   ├── telegram_bot.py      aiogram bot
│   │   └── web.py               FastAPI dashboard
│   └── templates/dashboard.html
├── deploy/
│   ├── agents.service           systemd unit
│   └── README.md                step-by-step VPS deploy
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## Quick local run

```bash
cd agents
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill ANTHROPIC_API_KEY at minimum
python -m src.main
```

Open `http://localhost:8000/?token=change-me`, send Alice a task.

## Deploying on your VPS

See [`deploy/README.md`](deploy/README.md) — covers both Docker and systemd,
plus the Gmail/Calendar OAuth flow.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│  Telegram   │───▶│              │◄───│  Web dashboard  │
└─────────────┘    │  Task queue  │    └─────────────────┘
                   │  (SQLite)    │
┌─────────────┐    │              │
│  Cron /     │───▶│              │
│  webhooks   │    └──────┬───────┘
└─────────────┘           │
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      ┌──────────────┐        ┌──────────────┐
      │    Alice     │        │     Sam      │
      │  (Claude +   │        │  (Claude +   │
      │  gmail/gcal) │        │  shell/gh)   │
      └──────────────┘        └──────────────┘
```

The orchestrator polls the queue every 2s, picks pending tasks, dispatches
them to the right agent. Agents run a tool-use loop against Claude until they
hit `end_turn` or the iteration cap. Status updates stream into the DB so the
dashboard reflects them within 5s (template auto-refresh).

## Adding a third agent

1. Create `src/agents/leo.py` with a system prompt and a tool registry.
2. Add it to `src/agents/__init__.py` (`AGENTS = {a.name: a for a in (alice, sam, leo)}`).
3. Restart.

## Adding a new tool

1. Drop a file in `src/tools/`, decorate the async function with `@tool(...)`.
2. Import + register it in whichever agent should use it.
3. Restart.

The Claude tool-use loop in `agents/base.py` handles dispatch automatically.

## Safety notes

- `shell` tool enforces a command whitelist (`SAM_SHELL_WHITELIST` env var) and
  rejects all shell metacharacters. Keep it that way unless you've thought hard
  about what an injected prompt could do.
- `MAX_AGENT_ITERATIONS` caps tool-use loops at 15 by default. Tune down for
  cheaper tasks, up for more autonomous ones.
- Web dashboard is protected by a query-param token. Use HTTPS in front of it
  (see deploy/README.md).
- Telegram bot enforces `TELEGRAM_OWNER_ID` once set — only you can issue tasks.

## Cost expectations

Default model is Haiku 4.5 (~$1/M tokens). A typical Alice task is 5-30k
tokens with tools. Budget $5-15/month for casual personal use, more if you
let Sam run long monitoring loops.
