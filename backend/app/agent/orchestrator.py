from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.context import ScopedContext
from app.agent.state import (
    AgentError,
    AgentResult,
    Phase,
    SharedState,
    Task,
    TaskManifest,
)
from app.db import get_db
from app.models.project import Project, ProjectState
from app.services import project as project_svc

logger = logging.getLogger(__name__)


# ── Interruption classification prompt ──────────────────────────

CLASSIFY_PROMPT = """You are a routing classifier for a code generation system.
The system is currently in the '{phase}' phase, working on building a FastAPI backend.

Current project spec: {spec_summary}
Current task: {current_task}

The user just said: "{user_message}"

Classify this message as exactly one of:
- MINOR_EDIT: Small change to existing code (rename field, change type, fix typo)
- ADDITIVE: New entity, new endpoint, new feature that extends the project
- BREAKING: Fundamental architecture change requiring full re-plan
- UNRELATED: Question, comment, or request that doesn't change the project

Respond with ONLY the classification word, nothing else."""


class OrchestratorSession:
    """Manages one project session. Replaces AgentSession.

    Public interface (must match what chat.py expects):
        __init__(project: Project)
        handle_user_message(message: str) -> AsyncGenerator[AgentEvent, None]
        cancel() -> None
    """

    def __init__(self, project: Project) -> None:
        self.project = project
        self.state = SharedState(project_id=project.id)
        self._cancelled = False
        self._agents: dict[str, BaseAgent] = {}
        self._active_agent: BaseAgent | None = None
        self._current_task: Task | None = None
        self._shared_context: str | None = None
        self._fallback_session = None
        self._file_handler: logging.FileHandler | None = None
        self._setup_project_log()
        self._register_agents()

    # ── Per-project file logging ─────────────────────────────────

    def _setup_project_log(self) -> None:
        """Attach a FileHandler so all app.agent.* logs are also
        written to ``projects/{project_id}/agent.log``."""
        log_dir = self.project.directory
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "agent.log"

        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        # Attach to the ``app`` namespace so agent, tools, llm, orchestrator
        # logs all flow into the file.
        logging.getLogger("app").addHandler(handler)
        self._file_handler = handler
        logger.info(
            "[Orchestrator] Project log → %s", log_path,
        )

    def _teardown_project_log(self) -> None:
        if self._file_handler is not None:
            logging.getLogger("app").removeHandler(self._file_handler)
            self._file_handler.close()
            self._file_handler = None

    def __del__(self) -> None:
        self._teardown_project_log()

    def _register_agents(self) -> None:
        agents_to_register = [
            ("clarification", "app.agent.agents.clarification", "ClarificationAgent"),
            ("planning", "app.agent.agents.planning", "PlanningAgent"),
            ("scaffold", "app.agent.agents.scaffold", "ScaffoldAgent"),
            ("database", "app.agent.agents.database", "DatabaseAgent"),
            ("api", "app.agent.agents.api", "APIAgent"),
            ("devops", "app.agent.agents.devops", "DevOpsAgent"),
        ]
        for name, module_path, class_name in agents_to_register:
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                self._agents[name] = agent_class()
            except (ImportError, AttributeError) as e:
                logger.debug("Agent '%s' not available: %s", name, e)
        if self._agents:
            logger.info("[Orchestrator] Loaded agents: %s", list(self._agents.keys()))

    def cancel(self) -> None:
        self._cancelled = True
        if self._active_agent:
            self._active_agent.cancel()

    # ── Chat message persistence ────────────────────────────────

    async def _persist_message(
        self, role: str, content: str | None = None,
        tool_calls: list[dict] | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        """Write a single chat message to the chat_messages table."""
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO chat_messages
                   (project_id, role, content, tool_calls, tool_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    self.project.id, role, content,
                    json.dumps(tool_calls) if tool_calls else None,
                    tool_call_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def _track_assistant_message(self, content: str) -> None:
        """Add assistant message to in-memory conversation and persist to DB."""
        self.state.user_conversation.append(
            {"role": "assistant", "content": content}
        )
        await self._persist_message("assistant", content)

    async def _restore_conversation(self) -> None:
        """Load chat history from chat_messages into state.user_conversation."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT role, content FROM chat_messages "
                "WHERE project_id = ? AND role IN ('user', 'assistant') ORDER BY id",
                (self.project.id,),
            )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        self.state.user_conversation = []
        for row in rows:
            self.state.user_conversation.append(
                {"role": row["role"], "content": row["content"] or ""}
            )
        if self.state.user_conversation:
            logger.info(
                "[Orchestrator] Restored %d conversation messages",
                len(self.state.user_conversation),
            )

    # ── Project state helper ────────────────────────────────────

    async def _set_project_state(self, new_state: ProjectState) -> AgentEvent:
        """Update the project state in DB and return a state_update event for the frontend."""
        self.project.state = new_state
        await project_svc.update_project(self.project)
        return AgentEvent(
            type="state_update",
            data={
                "state": new_state.value,
                "swagger_url": self.project.swagger_url or "",
                "api_url": self.project.api_url or "",
            },
        )

    # ── State persistence ───────────────────────────────────────

    async def save_state(self) -> None:
        data = self.state.to_dict()
        db = await get_db()
        try:
            await db.execute(
                """INSERT OR REPLACE INTO shared_state
                   (project_id, current_phase, spec_json, manifest_json,
                    files_created, errors, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["project_id"],
                    data["current_phase"],
                    data.get("spec_json"),
                    data.get("manifest_json"),
                    data.get("files_created", "[]"),
                    data.get("errors", "[]"),
                    data.get("updated_at"),
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def restore_state(self) -> None:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM shared_state WHERE project_id = ?",
                (self.project.id,),
            )
            row = await cursor.fetchone()
        finally:
            await db.close()

        if row:
            self.state = SharedState.from_dict(dict(row))
            logger.info(
                "[Orchestrator] Restored state: phase=%s",
                self.state.current_phase.value,
            )

        # Always restore conversation history from chat_messages
        await self._restore_conversation()

    # ── Main entry point ────────────────────────────────────────

    async def handle_user_message(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        self._cancelled = False

        # Track conversation (in-memory + DB)
        self.state.user_conversation.append(
            {"role": "user", "content": message}
        )
        await self._persist_message("user", message)

        # 1. If pending ask_user, resume the active agent
        if self._active_agent and self._active_agent.is_waiting_for_user:
            async for event in self._resume_agent_with_answer(message):
                yield event
            return

        # 2. If in validation phase with no active agent, user is triggering deployment
        if self.state.current_phase == Phase.VALIDATION and not self._active_agent:
            logger.info("[Orchestrator] User triggered deployment in validation phase")
            async for event in self._run_validation():
                yield event
            return

        # 3. If in implementation/complete and a task is running,
        #    classify the interruption
        if self.state.current_phase in (
            Phase.IMPLEMENTATION,
            Phase.COMPLETE,
        ):
            async for event in self._handle_interruption_flow(message):
                yield event
            return

        # 4. Route to current phase
        logger.info(
            "[Orchestrator] handle_user_message → phase=%s",
            self.state.current_phase.value,
        )
        async for event in self._run_phase(message):
            yield event

    # ── Phase routing ───────────────────────────────────────────

    async def _run_phase(
        self, user_message: str | None = None
    ) -> AsyncGenerator[AgentEvent, None]:
        phase = self.state.current_phase

        if phase == Phase.RESEARCH:
            async for event in self._run_research(user_message):
                yield event

        elif phase == Phase.PLANNING:
            async for event in self._run_planning():
                yield event

        elif phase == Phase.IMPLEMENTATION:
            async for event in self._run_implementation():
                yield event

        elif phase == Phase.VALIDATION:
            async for event in self._run_validation():
                yield event

        elif phase == Phase.COMPLETE:
            # In complete phase, handle as conversational
            async for event in self._respond_conversational(user_message or ""):
                yield event

    # ── Research phase ──────────────────────────────────────────

    async def _run_research(
        self, user_message: str | None
    ) -> AsyncGenerator[AgentEvent, None]:
        if "clarification" not in self._agents:
            logger.warning("[Orchestrator] RESEARCH but no clarification agent, using fallback")
            async for event in self._fallback_to_prototype(user_message or ""):
                yield event
            return

        logger.info("[Orchestrator] Running Clarification agent (sending to OpenRouter)...")
        agent = self._agents["clarification"]
        self._active_agent = agent

        # Track streamed text so we can save assistant messages to user_conversation
        text_parts: list[str] = []

        async for event in agent.run(
            state=self.state,
            project=self.project,
            user_message=user_message,
        ):
            yield event
            # Accumulate assistant text for conversation history
            if event.type == "agent_message_delta":
                text_parts.append(event.data.get("token", ""))
            elif event.type == "agent_message_end" and text_parts:
                await self._track_assistant_message("".join(text_parts))
                text_parts.clear()
            if event.type == "ask_user":
                return  # Paused, waiting for user

        result = await agent.get_result()
        self._active_agent = None

        if result.spec:
            self.state.spec = result.spec
            logger.info(
                "[Orchestrator] Clarification done: spec captured (%d entities). Next: planning (no Planning agent yet).",
                len(result.spec.entities),
            )
            # Transition to planning
            status_msg = "Requirements captured! Planning your project structure..."
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": status_msg},
            )
            yield AgentEvent(type="agent_message_end")
            await self._track_assistant_message(status_msg)

            self.state.current_phase = Phase.PLANNING
            logger.info("[Orchestrator] Phase transition: research → planning")
            yield AgentEvent(
                type="phase_transition",
                data={"from": "research", "to": "planning"},
            )
            await self.save_state()

            # Auto-chain into planning
            async for event in self._run_planning():
                yield event

    # ── Planning phase ──────────────────────────────────────────

    async def _run_planning(self) -> AsyncGenerator[AgentEvent, None]:
        if "planning" not in self._agents:
            async for event in self._fallback_to_prototype(""):
                yield event
            return

        agent = self._agents["planning"]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
        ):
            yield event

        result = await agent.get_result()
        self._active_agent = None

        if result.manifest:
            self.state.manifest = result.manifest

            status_msg = "Plan ready! Starting implementation..."
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": status_msg},
            )
            yield AgentEvent(type="agent_message_end")
            await self._track_assistant_message(status_msg)

            self.state.current_phase = Phase.IMPLEMENTATION
            logger.info("[Orchestrator] Phase transition: planning → implementation")
            yield await self._set_project_state(ProjectState.GENERATING)
            yield AgentEvent(
                type="phase_transition",
                data={"from": "planning", "to": "implementation"},
            )
            await self.save_state()

            # Auto-chain into implementation
            async for event in self._run_implementation():
                yield event

    # ── Implementation phase ────────────────────────────────────

    async def _build_shared_context(self) -> str:
        """Pre-read common project files to inject into agent messages."""
        project_dir = self.project.directory
        parts: list[str] = []

        # Directory listing
        if project_dir.exists():
            entries = []
            for f in sorted(project_dir.rglob("*")):
                if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts:
                    entries.append(str(f.relative_to(project_dir)))
            parts.append(f"## Project Structure\n```\n" + "\n".join(entries) + "\n```")

        # Key files
        for rel_path, label in [
            ("app/database.py", "Database setup (Base class, session)"),
            ("app/main.py", "Main application file"),
            ("app/models/__init__.py", "Models init"),
        ]:
            full_path = project_dir / rel_path
            if full_path.exists():
                content = full_path.read_text()
                parts.append(f"## {label} (`{rel_path}`)\n```python\n{content}\n```")

        ctx = "\n\n".join(parts)
        logger.info("[Orchestrator] Built shared context: %d chars", len(ctx))
        return ctx

    async def _run_implementation(self) -> AsyncGenerator[AgentEvent, None]:
        if self.state.manifest is None:
            yield AgentEvent(
                type="error",
                data={"message": "No task manifest available for implementation"},
            )
            return

        while True:
            if self._cancelled:
                yield AgentEvent(
                    type="stopped", data={"message": "Agent stopped by user"}
                )
                return

            # Get all runnable tasks (excluding docker_up)
            runnable = [
                t for t in self.state.manifest.get_runnable_tasks()
                if t.type != "docker_up"
            ]

            if not runnable:
                if self.state.manifest.all_complete():
                    break
                # Check if only docker_up tasks remain
                pending_non_docker = [
                    t for t in self.state.manifest.tasks
                    if t.status == "pending" and t.type != "docker_up"
                ]
                if not pending_non_docker:
                    break  # Code is done, deployment waits for user
                # Check for stuck tasks (failed, not retryable)
                stuck = [
                    t for t in self.state.manifest.tasks
                    if t.status == "failed" and t.retries >= 3
                ]
                if stuck:
                    yield AgentEvent(
                        type="error",
                        data={"message": "No runnable tasks available (possible dependency deadlock)"},
                    )
                    return
                # Tasks still running or have unmet deps — shouldn't happen in sequential flow
                yield AgentEvent(
                    type="error",
                    data={"message": "No runnable tasks available (possible dependency deadlock)"},
                )
                return

            if len(runnable) == 1:
                # Single task — run directly (simpler, no queue overhead)
                task = runnable[0]
                async for event in self._run_single_task(task):
                    if event.type == "ask_user":
                        yield event
                        return
                    yield event

                # After scaffold, build shared context
                if task.type == "scaffold" and task.status == "completed":
                    self._shared_context = await self._build_shared_context()
            else:
                # Multiple independent tasks — run in parallel
                async for event in self._run_parallel_tasks(runnable):
                    yield event

            # Check if we hit an unrecoverable error
            fatal = any(
                t.status == "failed" and t.retries >= 3
                for t in self.state.manifest.tasks
            )
            if fatal:
                return

        # All code tasks complete — wait for user to trigger deployment
        status_msg = (
            "Your backend code is ready! "
            "Review the generated files, then click **Deploy** when you're ready to build and run it."
        )
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={"token": status_msg},
        )
        yield AgentEvent(type="agent_message_end")
        await self._track_assistant_message(status_msg)

        self.state.current_phase = Phase.VALIDATION
        logger.info("[Orchestrator] Phase transition: implementation → validation (awaiting deploy)")
        yield AgentEvent(
            type="phase_transition",
            data={"from": "implementation", "to": "validation"},
        )
        await self.save_state()

        yield AgentEvent(type="waiting_for_user")

    async def _run_single_task(self, task: Task) -> AsyncGenerator[AgentEvent, None]:
        """Run a single task sequentially."""
        self._current_task = task
        task.status = "running"
        logger.info(
            "[Orchestrator] Task dispatch: id=%s  agent=%s  desc=%s",
            task.id, task.agent, task.description[:100],
        )

        yield AgentEvent(
            type="task_start",
            data={
                "task_id": task.id,
                "description": task.description,
                "task_type": task.type,
            },
        )

        agent_name = task.agent
        if agent_name not in self._agents:
            async for event in self._fallback_to_prototype(""):
                yield event
            return

        agent = self._agents[agent_name]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
            task=task,
            shared_context=self._shared_context,
        ):
            yield event
            if event.type == "ask_user":
                return  # Paused
            if event.type == "build_complete":
                self.state.manifest.mark_complete(task.id)
                await self.save_state()
                return

        result = await agent.get_result()
        self._active_agent = None
        await self._handle_task_result(task, result)

        if result.status == "success":
            yield AgentEvent(type="task_complete", data={"task_id": task.id})
        elif result.status == "error" and task.retries >= 3:
            yield AgentEvent(
                type="error",
                data={
                    "message": (
                        "Something went wrong while building your project. "
                        "You can try clicking **Deploy** to retry, or adjust your requirements."
                    )
                },
            )

    async def _run_parallel_tasks(self, tasks: list[Task]) -> AsyncGenerator[AgentEvent, None]:
        """Run multiple independent tasks concurrently using asyncio.Queue."""
        queue: asyncio.Queue[tuple[str, str, AgentEvent | AgentResult]] = asyncio.Queue()
        file_lock = asyncio.Lock()

        logger.info(
            "[Orchestrator] Parallel dispatch: %d tasks [%s]",
            len(tasks),
            ", ".join(f"{t.id}({t.agent})" for t in tasks),
        )

        async def worker(task: Task) -> None:
            # Create FRESH agent instance so per-run state is isolated
            agent_cls = type(self._agents[task.agent])
            agent = agent_cls()
            agent._file_lock = file_lock
            try:
                async for event in agent.run(
                    state=self.state,
                    project=self.project,
                    task=task,
                    shared_context=self._shared_context,
                ):
                    event.data.setdefault("task_id", task.id)
                    await queue.put((task.id, "event", event))
            except Exception as e:
                logger.exception("[Orchestrator] Worker error for task %s", task.id)
                agent._result = AgentResult(status="error", error=str(e))
            finally:
                result = await agent.get_result()
                await queue.put((task.id, "done", result))

        # Emit task_start for all
        for task in tasks:
            task.status = "running"
            yield AgentEvent(
                type="task_start",
                data={
                    "task_id": task.id,
                    "description": task.description,
                    "task_type": task.type,
                },
            )

        # Check all agents are available
        for task in tasks:
            if task.agent not in self._agents:
                logger.error("[Orchestrator] Agent '%s' not available for parallel task %s", task.agent, task.id)
                task.status = "failed"
                task.error = f"Agent '{task.agent}' not available"
                yield AgentEvent(type="task_complete", data={"task_id": task.id})
                return

        # Launch workers
        workers = [asyncio.create_task(worker(t)) for t in tasks]

        completed = 0
        while completed < len(tasks):
            task_id, msg_type, payload = await queue.get()
            if msg_type == "done":
                result = payload  # type: AgentResult
                task = next(t for t in tasks if t.id == task_id)
                await self._handle_task_result(task, result)
                if result.status == "success":
                    yield AgentEvent(type="task_complete", data={"task_id": task_id})
                elif result.status == "error" and task.retries >= 3:
                    yield AgentEvent(
                        type="error",
                        data={
                            "message": (
                                "Something went wrong while building your project. "
                                "You can try clicking **Deploy** to retry, or adjust your requirements."
                            )
                        },
                    )
                completed += 1
            else:
                yield payload  # Forward AgentEvent to WebSocket

        await asyncio.gather(*workers, return_exceptions=True)

    async def _handle_task_result(self, task: Task, result: AgentResult) -> None:
        """Process task result: mark complete/failed, handle retries."""
        if result.status == "success":
            logger.info("[Orchestrator] Task %s completed successfully", task.id)
            self.state.manifest.mark_complete(task.id)
            if result.files_modified:
                self.state.files_created.extend(result.files_modified)
            await self.save_state()
        elif result.status == "error":
            logger.warning("[Orchestrator] Task %s failed: %s", task.id, result.error)
            self.state.manifest.mark_failed(task.id, result.error or "Unknown error")
            if task.retries < 3:
                self.state.manifest.reset_for_retry(task.id)
                logger.warning("Task %s failed (attempt %d), retrying", task.id, task.retries)
            else:
                self.state.errors.append(
                    AgentError(
                        agent=task.agent,
                        task_id=task.id,
                        message=result.error or "Unknown error",
                    )
                )
                await self.save_state()

    # ── Validation phase ────────────────────────────────────────

    async def _run_validation(self) -> AsyncGenerator[AgentEvent, None]:
        if "devops" not in self._agents:
            async for event in self._fallback_to_prototype(""):
                yield event
            return

        yield await self._set_project_state(ProjectState.BUILDING)

        agent = self._agents["devops"]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
        ):
            yield event
            if event.type == "build_complete":
                self.state.current_phase = Phase.COMPLETE
                yield AgentEvent(
                    type="phase_transition",
                    data={"from": "validation", "to": "complete"},
                )
                await self.save_state()
                self._active_agent = None
                return

        result = await agent.get_result()
        self._active_agent = None

        if result.status == "success":
            self.state.current_phase = Phase.COMPLETE
            yield AgentEvent(
                type="phase_transition",
                data={"from": "validation", "to": "complete"},
            )
            await self.save_state()
        elif result.status == "error":
            self.state.errors.append(
                AgentError(
                    agent="devops",
                    task_id=None,
                    message=result.error or "Validation failed",
                )
            )
            yield AgentEvent(
                type="error",
                data={
                    "message": (
                        "Deployment didn't complete successfully. "
                        "This can happen if the app has startup errors or the health check timed out. "
                        "You can click **Deploy** to try again."
                    )
                },
            )
            await self.save_state()
            yield AgentEvent(type="waiting_for_user")

    # ── Interruption handling ───────────────────────────────────

    async def _handle_interruption_flow(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        classification = await self._classify_interruption(message)
        logger.info("[Orchestrator] Interruption classified as: %s", classification)

        if classification == "UNRELATED":
            async for event in self._respond_conversational(message):
                yield event

        elif classification == "MINOR_EDIT":
            # Create ad-hoc task and dispatch to appropriate agent
            async for event in self._handle_minor_edit(message):
                yield event

        elif classification == "ADDITIVE":
            async for event in self._handle_additive(message):
                yield event

        elif classification == "BREAKING":
            async for event in self._handle_breaking(message):
                yield event

    async def _classify_interruption(self, message: str) -> str:
        from app.agent.llm import chat_completion

        prompt = CLASSIFY_PROMPT.format(
            phase=self.state.current_phase.value,
            spec_summary=str(self.state.spec) if self.state.spec else "None",
            current_task=(
                str(self._current_task.description)
                if self._current_task
                else "None"
            ),
            user_message=message,
        )
        try:
            response = await chat_completion(
                [{"role": "user", "content": prompt}]
            )
            classification = response.strip().upper()
            if classification not in (
                "MINOR_EDIT",
                "ADDITIVE",
                "BREAKING",
                "UNRELATED",
            ):
                return "UNRELATED"
            return classification
        except Exception:
            return "UNRELATED"

    async def _handle_minor_edit(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        # Determine which agent handles this edit
        # Default to api agent, fall back to prototype
        agent_name = "api"
        if any(
            kw in message.lower()
            for kw in ("model", "field", "column", "table", "entity", "database")
        ):
            agent_name = "database"

        if agent_name not in self._agents:
            async for event in self._fallback_to_prototype(message):
                yield event
            return

        ad_hoc_task = Task(
            id="adhoc_edit",
            type="minor_edit",
            description=message,
            agent=agent_name,
        )

        agent = self._agents[agent_name]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
            task=ad_hoc_task,
            user_message=message,
            shared_context=self._shared_context,
        ):
            yield event
            if event.type == "ask_user":
                return

        self._active_agent = None
        yield AgentEvent(type="waiting_for_user")

    async def _handle_additive(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        status_msg = "Got it! Updating the plan to include your new requirement..."
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={"token": status_msg},
        )
        yield AgentEvent(type="agent_message_end")
        await self._track_assistant_message(status_msg)

        if "planning" not in self._agents:
            async for event in self._fallback_to_prototype(message):
                yield event
            return

        # Go back to planning for delta tasks
        self.state.current_phase = Phase.PLANNING
        yield AgentEvent(
            type="phase_transition",
            data={"from": "implementation", "to": "planning"},
        )

        agent = self._agents["planning"]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
            user_message=message,
        ):
            yield event

        result = await agent.get_result()
        self._active_agent = None

        if result.manifest and result.manifest.tasks:
            if self.state.manifest is None:
                self.state.manifest = result.manifest
            else:
                self.state.manifest.append_tasks(result.manifest.tasks)

            self.state.current_phase = Phase.IMPLEMENTATION
            yield AgentEvent(
                type="phase_transition",
                data={"from": "planning", "to": "implementation"},
            )
            await self.save_state()

            async for event in self._run_implementation():
                yield event
        else:
            # No new tasks — go back to implementation
            self.state.current_phase = Phase.IMPLEMENTATION
            await self.save_state()
            yield AgentEvent(type="waiting_for_user")

    async def _handle_breaking(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        status_msg = "This is a major change. Saving current progress and re-planning..."
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={"token": status_msg},
        )
        yield AgentEvent(type="agent_message_end")
        await self._track_assistant_message(status_msg)

        # Safety checkpoint: git commit current state
        from app.agent.tools import execute_tool

        await execute_tool(
            self.project, "git_commit", {"message": "checkpoint before breaking change"}
        )

        # Reset to research
        self.state.current_phase = Phase.RESEARCH
        self.state.spec = None
        self.state.manifest = None
        yield AgentEvent(
            type="phase_transition",
            data={"from": self.state.current_phase.value, "to": "research"},
        )
        await self.save_state()

        async for event in self._run_research(message):
            yield event

    async def _respond_conversational(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        from app.agent.llm import chat_completion

        context_summary = ""
        if self.state.spec:
            context_summary = f"Project spec: {json.dumps(self.state.spec.to_dict())}\n"
        if self.state.current_phase:
            context_summary += f"Current phase: {self.state.current_phase.value}\n"

        try:
            response = await chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are BackendForge, an AI assistant building a FastAPI backend. "
                            "Answer the user's question helpfully and concisely.\n"
                            + context_summary
                        ),
                    },
                    {"role": "user", "content": message},
                ]
            )
        except Exception as e:
            response = f"Sorry, I encountered an error: {e}"

        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta", data={"token": response}
        )
        yield AgentEvent(type="agent_message_end")
        await self._track_assistant_message(response)
        yield AgentEvent(type="waiting_for_user")

    # ── Resume after ask_user ───────────────────────────────────

    async def _resume_agent_with_answer(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        agent = self._active_agent
        if agent is None:
            yield AgentEvent(type="waiting_for_user")
            return

        if agent._current_messages is None:
            yield AgentEvent(type="waiting_for_user")
            return

        agent.resume_after_ask_user(agent._current_messages, message)

        # Track streamed text for conversation history
        text_parts: list[str] = []

        # Continue the react loop
        async for event in agent._run_react_loop(
            agent._current_messages, self.project
        ):
            yield event
            if event.type == "agent_message_delta":
                text_parts.append(event.data.get("token", ""))
            elif event.type == "agent_message_end" and text_parts:
                await self._track_assistant_message("".join(text_parts))
                text_parts.clear()
            if event.type == "ask_user":
                return
            if event.type == "build_complete":
                if self._current_task and self.state.manifest:
                    self.state.manifest.mark_complete(self._current_task.id)
                await self.save_state()
                return

        result = await agent.get_result()
        self._active_agent = None

        # Handle post-agent completion based on current phase
        async for event in self._handle_agent_completion(result):
            yield event

    async def _handle_agent_completion(
        self, result: AgentResult
    ) -> AsyncGenerator[AgentEvent, None]:
        phase = self.state.current_phase
        logger.info(
            "[Orchestrator] _handle_agent_completion: phase=%s status=%s has_spec=%s has_manifest=%s",
            phase.value, result.status, result.spec is not None, result.manifest is not None,
        )

        if phase == Phase.RESEARCH and result.spec:
            self.state.spec = result.spec
            status_msg = "Requirements captured! Planning your project structure..."
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": status_msg},
            )
            yield AgentEvent(type="agent_message_end")
            await self._track_assistant_message(status_msg)
            self.state.current_phase = Phase.PLANNING
            yield AgentEvent(
                type="phase_transition",
                data={"from": "research", "to": "planning"},
            )
            await self.save_state()
            async for event in self._run_planning():
                yield event

        elif phase == Phase.IMPLEMENTATION:
            if self._current_task and self.state.manifest:
                if result.status == "success":
                    self.state.manifest.mark_complete(self._current_task.id)
                    yield AgentEvent(
                        type="task_complete",
                        data={"task_id": self._current_task.id},
                    )
                    await self.save_state()
                    # Continue with next tasks
                    async for event in self._run_implementation():
                        yield event
                else:
                    yield AgentEvent(type="waiting_for_user")
            else:
                yield AgentEvent(type="waiting_for_user")

        else:
            yield AgentEvent(type="waiting_for_user")

    # ── Fallback to prototype ───────────────────────────────────

    async def _fallback_to_prototype(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        from app.agent.core import AgentSession

        logger.info("[Orchestrator] Falling back to prototype AgentSession")
        if self._fallback_session is None:
            self._fallback_session = AgentSession(self.project)
            await self._fallback_session.context.load_from_db(self.project.id)

        async for event in self._fallback_session.handle_user_message(message):
            yield event
