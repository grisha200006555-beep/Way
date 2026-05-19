from .registry import tool

# Google Calendar uses the same OAuth client as Gmail. See deploy/README.md
# section "Wiring Gmail & Google Calendar" before enabling these tools.


@tool(
    name="gcal_list_today",
    description="List today's calendar events (TODO: enable in deploy/README.md).",
    input_schema={"type": "object", "properties": {}},
)
async def gcal_list_today() -> str:
    return "STUB: Google Calendar not wired yet. See deploy/README.md to enable."


@tool(
    name="gcal_create_event",
    description="Create a calendar event (TODO: enable in deploy/README.md).",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "start": {"type": "string", "description": "ISO 8601 datetime"},
            "end": {"type": "string", "description": "ISO 8601 datetime"},
            "description": {"type": "string"},
        },
        "required": ["title", "start", "end"],
    },
)
async def gcal_create_event(title: str, start: str, end: str, description: str = "") -> str:
    return "STUB: Google Calendar not wired yet. See deploy/README.md to enable."
