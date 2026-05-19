import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from anthropic import AsyncAnthropic

from ..config import settings
from ..tools import ToolRegistry

log = logging.getLogger(__name__)

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

StatusCallback = Callable[[str, str], Awaitable[None]]  # (agent_name, status)


@dataclass
class Agent:
    name: str
    role: str
    system_prompt: str
    tools: ToolRegistry
    model: str = field(default_factory=lambda: settings.claude_model)
    max_iterations: int = field(default_factory=lambda: settings.max_agent_iterations)

    async def run(self, prompt: str, on_status: StatusCallback | None = None) -> str:
        messages: list[dict] = [{"role": "user", "content": prompt}]
        tool_specs = self.tools.anthropic_list()

        for i in range(self.max_iterations):
            if on_status:
                await on_status(self.name, "thinking")

            resp = await _client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=tool_specs if tool_specs else None,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                return _extract_text(resp.content)

            if resp.stop_reason == "tool_use":
                if on_status:
                    await on_status(self.name, "working")
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        log.info("[%s] tool %s args=%s", self.name, block.name, block.input)
                        result = await self.tools.run(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            # max_tokens or anything else — stop and return what we have
            return _extract_text(resp.content) or f"(stopped: {resp.stop_reason})"

        return f"(hit {self.max_iterations} iteration cap)"


def _extract_text(blocks) -> str:
    return "\n".join(b.text for b in blocks if getattr(b, "type", None) == "text").strip()
