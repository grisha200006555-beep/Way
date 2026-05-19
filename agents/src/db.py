from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, create_engine, Session

from .config import settings


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(index=True)
    prompt: str
    status: TaskStatus = Field(default=TaskStatus.pending, index=True)
    result: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    source: str = "manual"  # manual | telegram | cron | webhook
    requester: str = ""     # telegram user id, "system", etc.


class AgentState(SQLModel, table=True):
    name: str = Field(primary_key=True)
    status: str = "idle"  # idle | thinking | working | offline
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    current_task_id: Optional[int] = None


_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def session() -> Session:
    return Session(_engine)
