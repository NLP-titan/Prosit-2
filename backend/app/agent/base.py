from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.agent.state import SharedState, Task, AgentResult
from app.models.project import Project


@dataclass
class AgentEvent:
    """Events yielded by agents to the orchestrator/WebSocket layer.

    CRITICAL: These event types must match what the frontend expects.
    Do NOT rename or remove existing types. You may add new ones.

    Existing types (from prototype):
        agent_message_start, agent_message_delta, agent_message_end,
        tool_call_start, tool_call_result, build_complete,
        waiting_for_user, ask_user, error, stopped

    New types (Phase 2):
        phase_transition — when orchestrator changes phase
        task_start — when a task begins execution
        task_complete — when a task finishes
    """

    type: str
    data: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all specialist agents.

    Subclasses must set: name, model, system_prompt, tool_names
    Subclasses implement: run()

    The base class provides:
    - Tool schema filtering (only includes tools in self.tool_names)
    - The reusable ReAct loop via _run_react_loop()
    - Standard LLM call + tool execution + streaming pattern
    """

    name: str = ""
    model: str | None = None
    system_prompt: str = ""
    tool_names: list[str] = []
    max_tool_rounds: int = 20

    def __init__(self) -> None:
        self._pending_ask_user_tc_id: str | None = None
        self._result: AgentResult = AgentResult(status="success")
        self._cancelled: bool = False
        self._current_messages: list[dict] | None = None  # set by _run_react_loop

    def get_tool_schemas(self) -> list[dict]:
        """Filter global TOOL_SCHEMAS to only include this agent's tools."""
        from app.agent.prompts import TOOL_SCHEMAS

        if not self.tool_names:
            return TOOL_SCHEMAS
        return [
            s for s in TOOL_SCHEMAS if s["function"]["name"] in self.tool_names
        ]

    @abstractmethod
    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent work.

        Yields AgentEvent objects for streaming to the UI.

        Args:
            state: Current shared state (read from, don't mutate directly)
            project: The project being worked on
            task: Optional task from the manifest (for implementation agents)
            user_message: Optional user message (for conversational agents)

        Yields:
            AgentEvent objects (text streaming, tool calls, etc.)
        """
        ...

    async def get_result(self) -> AgentResult:
        """Called by orchestrator after run() completes to get structured result."""
        return self._result

    def cancel(self) -> None:
        self._cancelled = True

    async def _run_react_loop(
        self,
        messages: list[dict],
        project: Project,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Reusable ReAct loop: LLM call -> stream text -> execute tools -> loop.

        Extracted from the prototype's AgentSession._continue_agent_loop +
        _run_llm_turn. Specialist agents call this with their own messages
        and tool subset.

        Args:
            messages: The conversation messages (modified in-place as tools execute)
            project: The project for tool execution context
        """
        from app.agent.llm import chat_completion_stream
        from app.agent.tools import execute_tool

        self._current_messages = messages
        tools = self.get_tool_schemas()

        for _ in range(self.max_tool_rounds):
            if self._cancelled:
                yield AgentEvent(
                    type="stopped", data={"message": "Agent stopped by user"}
                )
                return

            # ── One LLM turn ────────────────────────────────────
            text_parts: list[str] = []
            tool_calls_acc: dict[int, dict] = {}
            started_text = False
            has_tool_calls = False

            try:
                async for chunk in chat_completion_stream(
                    messages, tools=tools, model=self.model
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
                        yield AgentEvent(
                            type="agent_message_delta",
                            data={"token": delta.content},
                        )
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
                                    tool_calls_acc[idx]["function"][
                                        "name"
                                    ] += tc.function.name
                                if tc.function.arguments:
                                    tool_calls_acc[idx]["function"][
                                        "arguments"
                                    ] += tc.function.arguments

            except Exception as e:
                yield AgentEvent(
                    type="error", data={"message": f"LLM error: {e}"}
                )
                self._result = AgentResult(
                    status="error", error=f"LLM error: {e}"
                )
                return

            if started_text:
                yield AgentEvent(type="agent_message_end")

            full_text = "".join(text_parts) if text_parts else None

            # ── Execute tool calls ──────────────────────────────
            if tool_calls_acc:
                has_tool_calls = True
                tool_calls_list = [
                    tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())
                ]

                # Add assistant message with tool calls to context
                msg: dict = {"role": "assistant", "tool_calls": tool_calls_list}
                if full_text:
                    msg["content"] = full_text
                messages.append(msg)

                for tc in tool_calls_list:
                    if self._cancelled:
                        return

                    func_name = tc["function"]["name"]
                    try:
                        args = (
                            json.loads(tc["function"]["arguments"])
                            if tc["function"]["arguments"]
                            else {}
                        )
                    except json.JSONDecodeError:
                        args = {}

                    # Handle ask_user — pause and yield event
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

                    result = await execute_tool(project, func_name, args)

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )

                    yield AgentEvent(
                        type="tool_call_result",
                        data={"tool": func_name, "result": result[:2000]},
                    )

                    # Check for sentinel returns that orchestrator intercepts
                    if result.startswith("__FINALIZE_SPEC__"):
                        self._result = AgentResult(status="success")
                        self._result.spec = _parse_spec_from_sentinel(result)
                        return

                    if result.startswith("__SUBMIT_PLAN__"):
                        self._result = AgentResult(status="success")
                        self._result.manifest = _parse_manifest_from_sentinel(
                            result
                        )
                        return

                    # Check if build_complete was called
                    if func_name == "build_complete":
                        yield AgentEvent(
                            type="build_complete",
                            data={
                                "swagger_url": project.swagger_url,
                                "api_url": project.api_url,
                            },
                        )
                        return

            elif full_text:
                # No tool calls, just text — add to messages
                messages.append({"role": "assistant", "content": full_text})

            # If no tool calls, the agent is done
            if not has_tool_calls:
                return

        # Safety: exhausted tool rounds
        yield AgentEvent(
            type="error",
            data={"message": "Agent exceeded maximum tool rounds"},
        )

    def resume_after_ask_user(
        self, messages: list[dict], user_answer: str
    ) -> str | None:
        """Inject user answer as tool result after ask_user pause.

        Returns the tool_call_id that was resumed, or None if not paused.
        """
        if self._pending_ask_user_tc_id is None:
            return None
        tc_id = self._pending_ask_user_tc_id
        self._pending_ask_user_tc_id = None
        messages.append(
            {"role": "tool", "tool_call_id": tc_id, "content": user_answer}
        )
        return tc_id

    @property
    def is_waiting_for_user(self) -> bool:
        return self._pending_ask_user_tc_id is not None


def _parse_spec_from_sentinel(result: str) -> "ProjectSpec | None":
    """Parse ProjectSpec from __FINALIZE_SPEC__ sentinel."""
    from app.agent.state import ProjectSpec

    try:
        json_str = result[len("__FINALIZE_SPEC__") :]
        data = json.loads(json_str)
        return ProjectSpec.from_dict(data)
    except Exception:
        return None


def _parse_manifest_from_sentinel(result: str) -> "TaskManifest | None":
    """Parse TaskManifest from __SUBMIT_PLAN__ sentinel."""
    from app.agent.state import TaskManifest

    try:
        json_str = result[len("__SUBMIT_PLAN__") :]
        data = json.loads(json_str)
        if isinstance(data, list):
            return TaskManifest.from_dict(data)
        return None
    except Exception:
        return None
