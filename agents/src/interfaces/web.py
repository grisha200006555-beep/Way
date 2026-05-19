import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ..agents import AGENTS
from ..config import settings
from ..db import AgentState, Task, session
from ..orchestrator import enqueue

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

app = FastAPI(title="Mission Control")


def _require_token(request: Request) -> None:
    token = request.query_params.get("token") or request.cookies.get("token")
    if token != settings.web_token:
        raise HTTPException(status_code=401, detail="bad token")


def _metrics() -> dict:
    try:
        import psutil  # type: ignore
        return {
            "cpu": f"{psutil.cpu_percent(interval=0.1):.0f}%",
            "ram": f"{psutil.virtual_memory().used // (1024**2)}/{psutil.virtual_memory().total // (1024**2)}MB",
            "uptime": _uptime(),
        }
    except ImportError:
        return {"cpu": "n/a", "ram": "n/a", "uptime": _uptime()}


def _uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        d, rem = divmod(int(secs), 86400)
        h, rem = divmod(rem, 3600)
        m, _ = divmod(rem, 60)
        return f"{d}d {h}h {m}m"
    except Exception:
        return "n/a"


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    _require_token(request)
    with session() as s:
        tasks = s.query(Task).order_by(Task.id.desc()).limit(20).all()
        states = {a.name: s.get(AgentState, a.name) for a in AGENTS.values()}
    resp = TEMPLATES.TemplateResponse("dashboard.html", {
        "request": request,
        "agents": AGENTS,
        "states": states,
        "tasks": tasks,
        "metrics": _metrics(),
    })
    resp.set_cookie("token", request.query_params.get("token", ""), httponly=True)
    return resp


@app.post("/tasks")
async def create_task(request: Request, agent: str = Form(...), prompt: str = Form(...)):
    _require_token(request)
    if agent not in AGENTS:
        raise HTTPException(status_code=400, detail=f"unknown agent {agent}")
    enqueue(agent, prompt, source="web", requester="dashboard")
    return RedirectResponse(url="/?token=" + settings.web_token, status_code=303)
