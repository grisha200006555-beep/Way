import asyncio
import logging
from datetime import datetime

from sqlmodel import select

from .agents import AGENTS
from .db import AgentState, Task, TaskStatus, session

log = logging.getLogger(__name__)


async def _set_status(name: str, status: str, task_id: int | None = None) -> None:
    with session() as s:
        state = s.get(AgentState, name) or AgentState(name=name)
        state.status = status
        state.last_seen = datetime.utcnow()
        state.current_task_id = task_id
        s.add(state)
        s.commit()


async def _run_task(task_id: int) -> None:
    with session() as s:
        task = s.get(Task, task_id)
        if not task or task.status != TaskStatus.pending:
            return
        task.status = TaskStatus.running
        task.started_at = datetime.utcnow()
        s.add(task)
        s.commit()
        prompt, agent_name = task.prompt, task.agent

    agent = AGENTS.get(agent_name)
    if agent is None:
        with session() as s:
            t = s.get(Task, task_id)
            t.status = TaskStatus.failed
            t.result = f"unknown agent: {agent_name}"
            t.finished_at = datetime.utcnow()
            s.add(t); s.commit()
        return

    async def on_status(name: str, status: str) -> None:
        await _set_status(name, status, task_id)

    try:
        result = await agent.run(prompt, on_status=on_status)
        status = TaskStatus.done
    except Exception as e:
        log.exception("agent %s failed", agent_name)
        result = f"{type(e).__name__}: {e}"
        status = TaskStatus.failed

    with session() as s:
        t = s.get(Task, task_id)
        t.status = status
        t.result = result
        t.finished_at = datetime.utcnow()
        s.add(t); s.commit()

    await _set_status(agent_name, "idle", None)


async def worker_loop(poll_interval: float = 2.0) -> None:
    log.info("orchestrator started, polling every %.1fs", poll_interval)
    for name in AGENTS:
        await _set_status(name, "idle")

    while True:
        with session() as s:
            pending = s.exec(
                select(Task).where(Task.status == TaskStatus.pending).order_by(Task.created_at)
            ).all()
            task_ids = [t.id for t in pending]

        if not task_ids:
            await asyncio.sleep(poll_interval)
            continue

        await asyncio.gather(*(_run_task(tid) for tid in task_ids))


def enqueue(agent: str, prompt: str, *, source: str = "manual", requester: str = "") -> int:
    with session() as s:
        t = Task(agent=agent, prompt=prompt, source=source, requester=requester)
        s.add(t); s.commit(); s.refresh(t)
        return t.id
