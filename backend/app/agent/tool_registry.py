import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Coroutine[Any, Any, str]]


class ToolRegistry:
    """Registry for agent tools. Each tool is a function the LLM can call."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Coroutine[Any, Any, str]],
    ) -> None:
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

    def get_openai_schema(self) -> list[dict]:
        """Return tools in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    async def execute(
        self, name: str, arguments: dict, project_id: str
    ) -> str:
        """Execute a tool by name with the given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        try:
            result = await tool.handler(project_id=project_id, **arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {type(e).__name__}: {str(e)}"

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
