from __future__ import annotations

import json
import logging
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
from app.models.project import Project

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
        self._fallback_session = None
        self._register_agents()

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
                logger.warning(f"Agent '{name}' not available: {e}")

    def cancel(self) -> None:
        self._cancelled = True
        if self._active_agent:
            self._active_agent.cancel()

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

    # ── Main entry point ────────────────────────────────────────

    async def handle_user_message(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        self._cancelled = False

        # Track conversation
        self.state.user_conversation.append(
            {"role": "user", "content": message}
        )

        # 1. If pending ask_user, resume the active agent
        if self._active_agent and self._active_agent.is_waiting_for_user:
            async for event in self._resume_agent_with_answer(message):
                yield event
            return

        # 2. If in implementation/validation/complete and a task is running,
        #    classify the interruption
        if self.state.current_phase in (
            Phase.IMPLEMENTATION,
            Phase.VALIDATION,
            Phase.COMPLETE,
        ):
            async for event in self._handle_interruption_flow(message):
                yield event
            return

        # 3. Route to current phase
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
            # Fallback to prototype
            async for event in self._fallback_to_prototype(user_message or ""):
                yield event
            return

        agent = self._agents["clarification"]
        self._active_agent = agent

        async for event in agent.run(
            state=self.state,
            project=self.project,
            user_message=user_message,
        ):
            yield event
            if event.type == "ask_user":
                return  # Paused, waiting for user

        result = await agent.get_result()
        self._active_agent = None

        if result.spec:
            self.state.spec = result.spec
            # Transition to planning
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": "Requirements captured! Planning your project structure..."},
            )
            yield AgentEvent(type="agent_message_end")

            self.state.current_phase = Phase.PLANNING
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

            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": "Plan ready! Starting implementation..."},
            )
            yield AgentEvent(type="agent_message_end")

            self.state.current_phase = Phase.IMPLEMENTATION
            yield AgentEvent(
                type="phase_transition",
                data={"from": "planning", "to": "implementation"},
            )
            await self.save_state()

            # Auto-chain into implementation
            async for event in self._run_implementation():
                yield event

    # ── Implementation phase ────────────────────────────────────

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

            task = self.state.manifest.get_next_task()
            if task is None:
                if self.state.manifest.all_complete():
                    break
                # No runnable task but not all complete — stuck
                yield AgentEvent(
                    type="error",
                    data={"message": "No runnable tasks available (possible dependency deadlock)"},
                )
                return

            self._current_task = task
            task.status = "running"

            yield AgentEvent(
                type="task_start",
                data={"task_id": task.id, "description": task.description},
            )

            # Dispatch to the named agent
            agent_name = task.agent
            if agent_name not in self._agents:
                # Fallback: use the prototype for this task
                async for event in self._fallback_to_prototype(""):
                    yield event
                return

            agent = self._agents[agent_name]
            self._active_agent = agent

            async for event in agent.run(
                state=self.state,
                project=self.project,
                task=task,
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

            if result.status == "success":
                self.state.manifest.mark_complete(task.id)
                if result.files_modified:
                    self.state.files_created.extend(result.files_modified)
                yield AgentEvent(
                    type="task_complete",
                    data={"task_id": task.id},
                )
                await self.save_state()
            elif result.status == "error":
                self.state.manifest.mark_failed(task.id, result.error or "Unknown error")
                if task.retries < 3:
                    self.state.manifest.reset_for_retry(task.id)
                    logger.warning(
                        f"Task {task.id} failed (attempt {task.retries}), retrying"
                    )
                else:
                    self.state.errors.append(
                        AgentError(
                            agent=agent_name,
                            task_id=task.id,
                            message=result.error or "Unknown error",
                        )
                    )
                    yield AgentEvent(
                        type="error",
                        data={
                            "message": f"Task '{task.description}' failed after 3 retries: {result.error}"
                        },
                    )
                    await self.save_state()
                    return

        # All tasks complete — transition to validation
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={"token": "All tasks complete! Validating your project..."},
        )
        yield AgentEvent(type="agent_message_end")

        self.state.current_phase = Phase.VALIDATION
        yield AgentEvent(
            type="phase_transition",
            data={"from": "implementation", "to": "validation"},
        )
        await self.save_state()

        async for event in self._run_validation():
            yield event

    # ── Validation phase ────────────────────────────────────────

    async def _run_validation(self) -> AsyncGenerator[AgentEvent, None]:
        if "devops" not in self._agents:
            async for event in self._fallback_to_prototype(""):
                yield event
            return

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
                data={"message": f"Validation failed: {result.error}"},
            )
            await self.save_state()

    # ── Interruption handling ───────────────────────────────────

    async def _handle_interruption_flow(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        classification = await self._classify_interruption(message)

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
        ):
            yield event
            if event.type == "ask_user":
                return

        self._active_agent = None
        yield AgentEvent(type="waiting_for_user")

    async def _handle_additive(
        self, message: str
    ) -> AsyncGenerator[AgentEvent, None]:
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={"token": "Got it! Updating the plan to include your new requirement..."},
        )
        yield AgentEvent(type="agent_message_end")

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
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(
            type="agent_message_delta",
            data={
                "token": "This is a major change. Saving current progress and re-planning..."
            },
        )
        yield AgentEvent(type="agent_message_end")

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

        # Continue the react loop
        async for event in agent._run_react_loop(
            agent._current_messages, self.project
        ):
            yield event
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

        if phase == Phase.RESEARCH and result.spec:
            self.state.spec = result.spec
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(
                type="agent_message_delta",
                data={"token": "Requirements captured! Planning your project structure..."},
            )
            yield AgentEvent(type="agent_message_end")
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

        if self._fallback_session is None:
            self._fallback_session = AgentSession(self.project)
            await self._fallback_session.context.load_from_db(self.project.id)

        async for event in self._fallback_session.handle_user_message(message):
            yield event
