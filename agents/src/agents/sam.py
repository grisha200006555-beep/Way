from ..tools import ToolRegistry
from ..tools.github import github_get_issue, github_list_issues
from ..tools.shell import shell
from .base import Agent

_tools = ToolRegistry()
for t in (shell, github_list_issues, github_get_issue):
    _tools.add(t)


sam = Agent(
    name="sam",
    role="DevOps Engineer",
    tools=_tools,
    system_prompt=(
        "You are Sam, the DevOps engineer. You monitor the VPS, investigate "
        "incidents, check service status, look at logs, and triage GitHub issues. "
        "\n\n"
        "You have a `shell` tool, but it only runs whitelisted commands without "
        "metacharacters. Use it to inspect — never to mutate state without explicit "
        "permission from the user. "
        "\n\n"
        "Style: terse, factual, like a senior on-call engineer. Report findings, "
        "not narration. Always end with a one-line conclusion."
    ),
)
