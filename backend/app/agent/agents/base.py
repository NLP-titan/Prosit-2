"""BaseAgent — shared LLM streaming loop for all Track 4 implementation agents.

Extracts the duplicated ~90-line LLM loop from scaffold.py, database.py, and
api.py into a single reusable base class. Subclasses only implement the parts
that differ: task instruction building, tool result tracking, and final result.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator

from app.agent.context import ConversationContext
from app.agent.llm import chat_completion_stream
from app.agent.tools import execute_tool
from app.agent.state import AgentResult, SharedState, Task
from app.agent.agents.events import AgentEvent
from app.agent.agents.constants import (
    DEFAULT_MAX_TOOL_ROUNDS,
    TOOL_RESULT_EVENT_MAX_CHARS,
    ESTIMATED_CHARS_PER_TOKEN,
    MAX_CONTEXT_TOKENS,
    CONTEXT_PRUNE_KEEP_LAST_N,
    MAX_VERIFY_ATTEMPTS,
    VERIFY_TIMEOUT_SECONDS,
)
from app.models.project import Project

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for Track 4 implementation agents.

    Subclasses must define class-level attributes:
        name: str               — agent identifier
        tool_names: list[str]   — allowed tool names
        tool_schemas: list[dict]— OpenAI function-calling schemas
        system_prompt: str      — LLM system prompt
        max_tool_rounds: int    — safety cap on LLM loop iterations

    Subclasses must implement:
        _build_task_instruction(task) -> str
        _track_tool_result(func_name, args, files_modified) -> None
        _build_success_result(task, files_modified) -> AgentResult

    Subclasses may override:
        _validate_task(task) -> str | None
        _post_loop_hook(task, files_modified) -> AsyncGenerator[AgentEvent, None]
    """

    name: str
    tool_names: list[str]
    tool_schemas: list[dict]
    system_prompt: str
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS

    def __init__(self, project: Project) -> None:
        self.project = project

    # ------------------------------------------------------------------
    # Abstract methods — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def _build_task_instruction(self, task: Task) -> str:
        """Convert task context into the user message sent to the LLM."""
        ...

    @abstractmethod
    def _track_tool_result(
        self, func_name: str, args: dict, files_modified: list[str]
    ) -> None:
        """Update files_modified based on which tool ran."""
        ...

    @abstractmethod
    def _build_success_result(
        self, task: Task | None, files_modified: list[str]
    ) -> AgentResult:
        """Build the final AgentResult for a successful run."""
        ...

    # ------------------------------------------------------------------
    # Overridable hooks
    # ------------------------------------------------------------------

    def _validate_task(self, task: Task | None) -> str | None:
        """Return an error message if the task is invalid, else None."""
        return None

    async def _post_loop_hook(
        self, task: Task | None, files_modified: list[str]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run after the main loop (e.g. safety commits). Yields AgentEvents."""
        return
        yield  # makes this a valid async generator

    # ------------------------------------------------------------------
    # Code verification
    # ------------------------------------------------------------------

    async def _verify_files(
        self, files_modified: list[str]
    ) -> list[dict]:
        """Run py_compile on each modified .py file. Returns list of errors.

        Each error is a dict: {"file": str, "error": str}.
        Only checks syntax — does not verify imports or runtime behavior.
        """
        project_dir = self.project.directory
        errors: list[dict] = []

        # Deduplicate and filter to .py files only
        seen: set[str] = set()
        py_files: list[str] = []
        for f in files_modified:
            if f and f.endswith(".py") and f not in seen:
                seen.add(f)
                py_files.append(f)

        for rel_path in py_files:
            full_path = project_dir / rel_path
            if not full_path.exists():
                continue

            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", "-m", "py_compile", str(full_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=VERIFY_TIMEOUT_SECONDS
                )
                if proc.returncode != 0:
                    error_text = stderr.decode(errors="replace").strip()
                    errors.append({"file": rel_path, "error": error_text})
            except asyncio.TimeoutError:
                errors.append({
                    "file": rel_path,
                    "error": "Syntax check timed out",
                })
            except Exception as e:
                # If py_compile itself fails to run, skip verification
                logger.warning(
                    "%s: py_compile check failed for %s: %s",
                    self.name, rel_path, e,
                )

        return errors

    # ------------------------------------------------------------------
    # Context window management
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(messages: list[dict]) -> int:
        """Rough token estimate: total chars / 4."""
        total_chars = sum(
            len(str(m.get("content", "")))
            + len(str(m.get("tool_calls", "")))
            for m in messages
        )
        return total_chars // ESTIMATED_CHARS_PER_TOKEN

    @staticmethod
    def _prune_messages(messages: list[dict]) -> list[dict]:
        """Drop middle messages when context grows too large.

        Keeps: system message (index 0), first user instruction (index 1),
        and the last CONTEXT_PRUNE_KEEP_LAST_N * 2 messages.
        """
        keep_count = CONTEXT_PRUNE_KEEP_LAST_N * 2
        if len(messages) <= 2 + keep_count:
            return messages

        keep_prefix = messages[:2]
        keep_suffix = messages[-keep_count:]
        pruned_count = len(messages) - len(keep_prefix) - len(keep_suffix)

        summary = {
            "role": "system",
            "content": f"[{pruned_count} earlier messages pruned for context length]",
        }
        return keep_prefix + [summary] + keep_suffix

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(
        self, state: SharedState, task: Task | None = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute the agent task. Yields AgentEvents."""

        # Step 1: Validate task
        validation_error = self._validate_task(task)
        if validation_error:
            yield AgentEvent(
                type="agent_result",
                data=AgentResult(status="error", error=validation_error).__dict__,
            )
            return

        # Step 2: Build conversation
        context = ConversationContext()
        context.messages = [{"role": "system", "content": self.system_prompt}]

        instruction = self._build_task_instruction(task)
        context.messages.append({"role": "user", "content": instruction})

        files_modified: list[str] = []
        verify_attempts = 0

        # Step 3: LLM loop
        for _round in range(self.max_tool_rounds):

            # Context window management
            if self._estimate_tokens(context.messages) > MAX_CONTEXT_TOKENS:
                context.messages = self._prune_messages(context.messages)
                logger.info(
                    "%s: pruned context to %d messages",
                    self.name,
                    len(context.messages),
                )

            # --- LLM call ---
            text_parts: list[str] = []
            tool_calls_acc: dict[int, dict] = {}
            started_text = False

            try:
                async for chunk in chat_completion_stream(
                    context.get_messages(), tools=self.tool_schemas
                ):
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta is None:
                        continue

                    if delta.content:
                        if not started_text:
                            yield AgentEvent(type="agent_message_start")
                            started_text = True
                        yield AgentEvent(
                            type="agent_message_delta",
                            data={"token": delta.content},
                        )
                        text_parts.append(delta.content)

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
                yield AgentEvent(
                    type="agent_result",
                    data=AgentResult(status="error", error=str(e)).__dict__,
                )
                return

            if started_text:
                yield AgentEvent(type="agent_message_end")

            full_text = "".join(text_parts) if text_parts else None

            # --- Tool execution ---
            if tool_calls_acc:
                tool_calls_list = [
                    tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())
                ]
                context.messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": tool_calls_list,
                        **({"content": full_text} if full_text else {}),
                    }
                )

                for tc in tool_calls_list:
                    func_name = tc["function"]["name"]

                    # Parse arguments with error feedback to LLM
                    raw_args = tc["function"]["arguments"]
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError as je:
                        error_msg = (
                            f"Error: invalid JSON in tool arguments: {je}. "
                            f"Raw arguments: {raw_args[:200]}"
                        )
                        context.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": error_msg,
                            }
                        )
                        yield AgentEvent(
                            type="tool_call_result",
                            data={"tool": func_name, "result": error_msg},
                        )
                        continue

                    # Tool name filtering
                    if func_name not in self.tool_names:
                        result = (
                            f"Error: {func_name} is not available to "
                            f"{self.__class__.__name__}."
                        )
                        context.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result,
                            }
                        )
                        yield AgentEvent(
                            type="tool_call_result",
                            data={"tool": func_name, "result": result},
                        )
                        continue

                    yield AgentEvent(
                        type="tool_call_start",
                        data={"tool": func_name, "arguments": args},
                    )

                    # Execute with error handling
                    try:
                        result = await execute_tool(
                            self.project, func_name, args
                        )
                    except Exception as exc:
                        result = (
                            f"Error: tool {func_name} raised "
                            f"{type(exc).__name__}: {exc}"
                        )
                        logger.exception(
                            "%s: execute_tool(%s) failed",
                            self.name,
                            func_name,
                        )

                    context.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        }
                    )

                    yield AgentEvent(
                        type="tool_call_result",
                        data={
                            "tool": func_name,
                            "result": result[:TOOL_RESULT_EVENT_MAX_CHARS],
                        },
                    )

                    # Track modifications
                    self._track_tool_result(func_name, args, files_modified)

            else:
                # No tool calls — agent thinks it's done
                if full_text:
                    context.messages.append(
                        {"role": "assistant", "content": full_text}
                    )

                # Step 3b: Verify modified files before accepting
                if files_modified and verify_attempts < MAX_VERIFY_ATTEMPTS:
                    errors = await self._verify_files(files_modified)
                    if errors:
                        verify_attempts += 1
                        error_lines = [
                            "## Syntax Errors Detected",
                            "",
                            "The following files have syntax errors that "
                            "must be fixed before committing:",
                            "",
                        ]
                        for err in errors:
                            error_lines.append(
                                f"**{err['file']}**:\n```\n{err['error']}\n```"
                            )
                        error_lines.append(
                            "\nPlease read the broken file(s), fix the "
                            "syntax errors, and try again."
                        )
                        error_msg = "\n".join(error_lines)

                        context.messages.append(
                            {"role": "user", "content": error_msg}
                        )

                        yield AgentEvent(
                            type="error",
                            data={
                                "message": f"Syntax errors in "
                                f"{len(errors)} file(s), "
                                f"asking LLM to fix "
                                f"(attempt {verify_attempts}/"
                                f"{MAX_VERIFY_ATTEMPTS})"
                            },
                        )

                        logger.warning(
                            "%s: verification found %d error(s), "
                            "re-entering loop (attempt %d/%d)",
                            self.name,
                            len(errors),
                            verify_attempts,
                            MAX_VERIFY_ATTEMPTS,
                        )
                        continue  # re-enter the LLM loop to fix

                break  # verification passed or not applicable

        # Step 4: Post-loop hook (safety commits, etc.)
        async for event in self._post_loop_hook(task, files_modified):
            yield event

        # Step 5: Final result
        yield AgentEvent(
            type="agent_result",
            data=self._build_success_result(task, files_modified).__dict__,
        )
