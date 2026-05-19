from .registry import tool

# Gmail integration requires OAuth setup (client secret + first-run consent flow).
# Setup is non-trivial and best done interactively once. See deploy/README.md
# section "Wiring Gmail & Google Calendar" before enabling these tools.
#
# To enable: pip install google-api-python-client google-auth-oauthlib,
# replace the body of `_service()` with the standard creds.json + token.json
# flow, then unstub the handlers below.


@tool(
    name="gmail_list_unread",
    description="List unread emails in the inbox (TODO: enable Gmail in deploy/README.md).",
    input_schema={
        "type": "object",
        "properties": {
            "max_results": {"type": "integer", "default": 10},
        },
    },
)
async def gmail_list_unread(max_results: int = 10) -> str:
    return "STUB: Gmail not wired yet. See deploy/README.md to enable."


@tool(
    name="gmail_send",
    description="Send an email (TODO: enable Gmail in deploy/README.md).",
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to", "subject", "body"],
    },
)
async def gmail_send(to: str, subject: str, body: str) -> str:
    return "STUB: Gmail not wired yet. See deploy/README.md to enable."
