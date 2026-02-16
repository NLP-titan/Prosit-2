import json
import os
from pathlib import Path
from typing import AsyncGenerator

from app.agent.history import HistoryManager
from app.agent.llm_client import llm_client
from app.agent.prompts import build_system_prompt
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.command_tools import register_command_tools
from app.agent.tools.file_tools import register_file_tools
from app.agent.tools.git_tools import register_git_tools
from app.agent.tools.search_tools import register_search_tools
from app.agent.tools.user_tools import AskUserInterrupt, register_user_tools
from app.config import settings


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_file_tools(registry)
    register_search_tools(registry)
    register_command_tools(registry)
    register_git_tools(registry)
    register_user_tools(registry)
    return registry


def _list_project_files(project_id: str) -> list[str]:
    """List all files in the project for context."""
    project_dir = Path(settings.projects_base_dir) / project_id
    if not project_dir.exists():
        return []

    files = []
    for root, dirs, filenames in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for f in filenames:
            rel = os.path.relpath(os.path.join(root, f), project_dir)
            files.append(rel)
    return sorted(files)


class AgentLoop:
    """
    The core agent loop. Takes a user message, runs the LLM with tools,
    executes tool calls, and yields SSE events throughout.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.tools = _build_tool_registry()
        self.history = HistoryManager()
        self.max_iterations = settings.max_agent_iterations

    async def run(self, user_message: str) -> AsyncGenerator[str, None]:
        """
        Main entry. Yields SSE-formatted event strings.

        Handles the ask_user resumption flow: if there's a pending ask_user,
        the user_message is treated as the answer to that question.
        """
        # Check for pending ask_user
        pending = await self.history.get_pending_ask_user(self.project_id)
        if pending:
            # This message is the answer to a pending ask_user question
            await self.history.append(
                self.project_id,
                {
                    "role": "tool",
                    "tool_call_id": pending["tool_call_id"],
                    "content": user_message,
                    "name": "ask_user",
                },
            )
        else:
            # Normal user message
            await self.history.append(
                self.project_id, {"role": "user", "content": user_message}
            )

        yield self._sse("message_start", {})

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # Build messages for LLM
            existing_files = _list_project_files(self.project_id)
            system_prompt = build_system_prompt(self.project_id, existing_files)
            messages = await self.history.get_messages(self.project_id)

            # Call LLM with streaming
            tool_calls_accumulated = []
            text_accumulated = ""

            try:
                async for chunk in llm_client.stream_chat(
                    messages=[{"role": "system", "content": system_prompt}] + messages,
                    tools=self.tools.get_openai_schema(),
                ):
                    if not chunk.choices:
                        continue

                    delta = chunk.choices[0].delta

                    # Stream text content
                    if delta.content:
                        text_accumulated += delta.content
                        yield self._sse("text_delta", {"content": delta.content})

                    # Accumulate tool calls
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            self._accumulate_tool_call(tool_calls_accumulated, tc_delta)

            except Exception as e:
                yield self._sse("error", {"message": f"LLM error: {str(e)}"})
                break

            # Process the response
            if tool_calls_accumulated:
                # Build and save assistant message
                tc_dicts = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls_accumulated
                ]

                assistant_msg = {
                    "role": "assistant",
                    "content": text_accumulated or None,
                    "tool_calls": tc_dicts,
                }
                await self.history.append(self.project_id, assistant_msg)

                # Execute each tool call
                for tc in tool_calls_accumulated:
                    yield self._sse(
                        "tool_start",
                        {
                            "id": tc["id"],
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    )

                    try:
                        args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    # Special handling for ask_user
                    if tc["name"] == "ask_user":
                        question = args.get("question", "")
                        options = args.get("options", [])
                        # Save the tool call but don't execute — interrupt
                        yield self._sse(
                            "ask_user",
                            {
                                "question": question,
                                "options": options,
                                "tool_call_id": tc["id"],
                            },
                        )
                        yield self._sse("message_end", {})
                        return

                    # Execute the tool
                    result = await self.tools.execute(
                        name=tc["name"],
                        arguments=args,
                        project_id=self.project_id,
                    )

                    # Truncate result for SSE display
                    display_result = result
                    if len(display_result) > 3000:
                        display_result = (
                            display_result[:3000]
                            + f"\n... (truncated, {len(result)} chars)"
                        )

                    yield self._sse(
                        "tool_result",
                        {
                            "id": tc["id"],
                            "name": tc["name"],
                            "result": display_result,
                            "is_error": result.startswith("Error"),
                        },
                    )

                    # Save tool result to history
                    await self.history.append(
                        self.project_id,
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                            "name": tc["name"],
                        },
                    )

                # Loop back to call LLM again with tool results
                continue

            else:
                # LLM responded with text only — done
                if text_accumulated:
                    await self.history.append(
                        self.project_id,
                        {"role": "assistant", "content": text_accumulated},
                    )
                break

        yield self._sse("message_end", {})

    def _sse(self, event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    def _accumulate_tool_call(self, accumulated: list[dict], delta) -> None:
        """Merge streamed tool_call deltas into complete tool call objects."""
        idx = delta.index
        while len(accumulated) <= idx:
            accumulated.append({"id": "", "name": "", "arguments": ""})

        tc = accumulated[idx]
        if delta.id:
            tc["id"] = delta.id
        if delta.function:
            if delta.function.name:
                tc["name"] = delta.function.name
            if delta.function.arguments:
                tc["arguments"] += delta.function.arguments
