from ..tools import ToolRegistry
from ..tools.gcal import gcal_create_event, gcal_list_today
from ..tools.gmail import gmail_list_unread, gmail_send
from .base import Agent

_tools = ToolRegistry()
for t in (gmail_list_unread, gmail_send, gcal_list_today, gcal_create_event):
    _tools.add(t)


alice = Agent(
    name="alice",
    role="Personal Assistant",
    tools=_tools,
    system_prompt=(
        "You are Alice, the CEO's personal assistant. You handle email triage, "
        "calendar management, drafting replies, and quick research. "
        "\n\n"
        "Style: warm but concise. Russian or English — match the user's language. "
        "Always confirm before sending email or creating calendar events. "
        "If a tool returns STUB, tell the user that integration is not wired yet "
        "and what they need to do (point them at deploy/README.md)."
    ),
)
