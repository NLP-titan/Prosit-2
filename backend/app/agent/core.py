from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.agent.context import ConversationContext
from app.agent.llm import chat_completion_stream
from app.agent.prompts import TOOL_SCHEMAS
from app.agent.tools import execute_tool
from app.models.project import Project


@dataclass
class AgentEvent:
    """Events yielded by the agent loop to the WebSocket layer."""
    type: str  # agent_message_start, agent_message_delta, agent_message_end,
               # tool_call_start, tool_call_result, build_complete,
               # waiting_for_user, ask_user, error, stopped
    data: dict = field(default_factory=dict)


class AgentSession:
    """Manages one conversation session for a project."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.context = ConversationContext()
        self._max_tool_rounds = 30  # safety limit per user message
        self._cancelled = False
        self._pending_ask_user_tc_id: str | None = None

    def cancel(self) -> None:
        """Cancel the current agent run."""
        self._cancelled = True

    async def handle_user_message(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        """Process a user message and yield events (streamed text + tool calls)."""
        self._cancelled = False

        # If there's a pending ask_user, inject the response as a tool result
        if self._pending_ask_user_tc_id is not None:
            tc_id = self._pending_ask_user_tc_id
            self._pending_ask_user_tc_id = None
            await self.context.add_tool_result(tc_id, message)
            # Continue the agent loop after injecting the answer
            async for event in self._continue_agent_loop():
                yield event
            return

        await self.context.add_user_message(message)

        async for event in self._continue_agent_loop():
            yield event

    async def _continue_agent_loop(self) -> AsyncGenerator[AgentEvent, None]:
        """Run the agent loop (LLM calls + tool execution)."""
        for _ in range(self._max_tool_rounds):
            if self._cancelled:
                yield AgentEvent(type="stopped", data={"message": "Agent stopped by user"})
                return

            has_tool_calls = False
            async for event in self._run_llm_turn():
                if self._cancelled:
                    yield AgentEvent(type="stopped", data={"message": "Agent stopped by user"})
                    return
                yield event
                if event.type == "tool_call_start":
                    has_tool_calls = True
                if event.type == "build_complete":
                    return
                if event.type == "ask_user":
                    return  # Pause — waiting for user answer

            # If no tool calls, the agent is done or waiting for user
            if not has_tool_calls:
                yield AgentEvent(type="waiting_for_user")
                return

        # Safety: if we exhaust tool rounds, unfreeze the UI
        yield AgentEvent(type="waiting_for_user")

    async def _run_llm_turn(self) -> AsyncGenerator[AgentEvent, None]:
        """Run one LLM call, stream text, accumulate tool calls, execute them."""
        text_parts: list[str] = []
        tool_calls_acc: dict[int, dict] = {}
        started_text = False

        try:
            async for chunk in chat_completion_stream(
                self.context.get_messages(), tools=TOOL_SCHEMAS
            ):
                if self._cancelled:
                    return

                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # Stream text content
                if delta.content:
                    if not started_text:
                        yield AgentEvent(type="agent_message_start")
                        started_text = True
                    yield AgentEvent(type="agent_message_delta", data={"token": delta.content})
                    text_parts.append(delta.content)

                # Accumulate tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

        except Exception as e:
            yield AgentEvent(type="error", data={"message": f"LLM error: {e}"})
            return

        if started_text:
            yield AgentEvent(type="agent_message_end")

        full_text = "".join(text_parts) if text_parts else None

        # If there are tool calls, execute them
        if tool_calls_acc:
            tool_calls_list = [tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())]
            await self.context.add_assistant_tool_calls(full_text, tool_calls_list)

            for tc in tool_calls_list:
                if self._cancelled:
                    return

                func_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                # Handle ask_user specially — pause and yield event
                if func_name == "ask_user":
                    self._pending_ask_user_tc_id = tc["id"]
                    yield AgentEvent(
                        type="ask_user",
                        data={
                            "question": args.get("question", ""),
                            "options": args.get("options", []),
                            "tool_call_id": tc["id"],
                        },
                    )
                    return  # Pause the loop

                yield AgentEvent(
                    type="tool_call_start",
                    data={"tool": func_name, "arguments": args},
                )

                result = await execute_tool(self.project, func_name, args)

                await self.context.add_tool_result(tc["id"], result)

                yield AgentEvent(
                    type="tool_call_result",
                    data={"tool": func_name, "result": result[:2000]},
                )

                # Check if build_complete was called
                if func_name == "build_complete":
                    yield AgentEvent(
                        type="build_complete",
                        data={
                            "swagger_url": self.project.swagger_url,
                            "api_url": self.project.api_url,
                        },
                    )
                    return
        elif full_text:
            await self.context.add_assistant_message(full_text)
