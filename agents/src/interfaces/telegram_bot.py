import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from ..agents import AGENTS
from ..config import settings
from ..db import Task, TaskStatus, session
from ..orchestrator import enqueue

log = logging.getLogger(__name__)


def _build_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start(m: Message) -> None:
        await m.answer(
            "Hi. I'm a router for your AI team.\n\n"
            "Send: `alice: <task>` or `sam: <task>`.\n"
            "Just text without prefix → goes to Alice.\n\n"
            f"Your Telegram id: `{m.from_user.id}` — paste into TELEGRAM_OWNER_ID.",
            parse_mode="Markdown",
        )

    @dp.message(Command("status"))
    async def status(m: Message) -> None:
        if not _is_owner(m): return
        with session() as s:
            recent = s.query(Task).order_by(Task.id.desc()).limit(10).all()
        if not recent:
            await m.answer("No tasks yet.")
            return
        lines = [
            f"#{t.id} [{t.agent}] {t.status.value} — {t.prompt[:60]}"
            for t in recent
        ]
        await m.answer("\n".join(lines))

    @dp.message(F.text)
    async def route(m: Message) -> None:
        if not _is_owner(m):
            await m.answer("You're not the configured owner.")
            return

        text = m.text or ""
        agent_name = "alice"
        prompt = text
        if ":" in text:
            head, rest = text.split(":", 1)
            head = head.strip().lower()
            if head in AGENTS:
                agent_name = head
                prompt = rest.strip()

        task_id = enqueue(agent_name, prompt, source="telegram",
                          requester=str(m.from_user.id))
        await m.answer(f"Task #{task_id} → {agent_name}. I'll reply when done.")

        # Wait up to 3 min for completion, then post the result back.
        for _ in range(90):
            await asyncio.sleep(2)
            with session() as s:
                t = s.get(Task, task_id)
            if t.status in (TaskStatus.done, TaskStatus.failed):
                prefix = "" if t.status == TaskStatus.done else "FAILED: "
                await m.answer(f"#{task_id} {prefix}\n{t.result}"[:4000])
                return
        await m.answer(f"#{task_id} still running — check /status later.")

    return dp


def _is_owner(m: Message) -> bool:
    if settings.telegram_owner_id is None:
        return True  # not configured yet — allow first user
    return m.from_user.id == settings.telegram_owner_id


async def run_bot() -> None:
    if not settings.telegram_bot_token:
        log.warning("TELEGRAM_BOT_TOKEN not set, skipping bot")
        return
    bot = Bot(token=settings.telegram_bot_token)
    dp = _build_dispatcher()
    log.info("telegram bot started")
    await dp.start_polling(bot)
