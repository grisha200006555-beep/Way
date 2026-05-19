from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., Awaitable[str]]

    def to_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass
class ToolRegistry:
    tools: dict[str, ToolSpec] = field(default_factory=dict)

    def add(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def anthropic_list(self) -> list[dict]:
        return [s.to_anthropic() for s in self.tools.values()]

    async def run(self, name: str, args: dict[str, Any]) -> str:
        if name not in self.tools:
            return f"ERROR: unknown tool '{name}'"
        try:
            return await self.tools[name].handler(**args)
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"


def tool(name: str, description: str, input_schema: dict):
    """Decorator to declare an async tool handler."""
    def decorator(fn: Callable[..., Awaitable[str]]) -> ToolSpec:
        return ToolSpec(name=name, description=description,
                        input_schema=input_schema, handler=fn)
    return decorator
