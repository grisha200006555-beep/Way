import asyncio
import shlex

from ..config import settings
from .registry import tool


@tool(
    name="shell",
    description=(
        "Run a single shell command on the VPS. Only commands whose first "
        "token is in the configured whitelist are allowed. No shell metacharacters "
        "like &&, ||, ;, |, >, < — pass a single command with arguments."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command line to execute, e.g. 'df -h' or 'systemctl status nginx'.",
            },
        },
        "required": ["command"],
    },
)
async def shell(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return f"ERROR: bad command: {e}"

    if not parts:
        return "ERROR: empty command"

    head = parts[0].split("/")[-1]  # strip absolute path
    if head not in settings.shell_allowed:
        return (
            f"ERROR: '{head}' not in whitelist. Allowed: "
            f"{sorted(settings.shell_allowed)}"
        )

    forbidden = {"&&", "||", ";", "|", ">", "<", "`", "$("}
    if any(f in command for f in forbidden):
        return "ERROR: shell metacharacters not allowed"

    try:
        proc = await asyncio.create_subprocess_exec(
            *parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        return "ERROR: command timed out after 30s"

    out = stdout.decode(errors="replace")
    if len(out) > 8000:
        out = out[:8000] + "\n... [truncated]"
    return f"exit={proc.returncode}\n{out}"
