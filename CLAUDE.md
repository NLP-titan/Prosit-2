# BackendForge

## Project Vision

BackendForge is a conversational AI platform that enables non-developers to build production-ready backend APIs through natural language. Users describe what they want, and an AI agent builds a fully dockerized FastAPI backend — handling architecture decisions, code generation, database setup, and documentation automatically.

## Current State: Working Prototype (Phase 1) ✅

The Phase 1 prototype is **fully functional** and preserved on the `prototype-v1` Git branch. It uses a single-agent architecture where one `AgentSession` in `core.py` handles the entire workflow. **DO NOT break existing functionality.** The frontend must continue to work without changes.

### Existing Architecture

```
backend/app/
├── main.py              # FastAPI entry point, CORS, routers
├── config.py            # Settings (OpenRouter key, paths, ports)
├── db.py                # SQLite persistence (aiosqlite, WAL mode)
├── routers/
│   ├── chat.py          # WebSocket endpoint — routes AgentSession events to frontend
│   └── projects.py      # Project CRUD endpoints
├── agent/
│   ├── core.py          # AgentSession — single ReAct loop (THE FILE BEING REPLACED)
│   ├── llm.py           # OpenRouter client — single model, streaming
│   ├── tools.py         # Tool implementations — flat execute_tool() with 13 tools
│   ├── prompts.py       # Single SYSTEM_PROMPT + TOOL_SCHEMAS list
│   └── context.py       # ConversationContext — flat message list with SQLite persistence
├── generator/
│   └── scaffold.py      # Jinja2 template renderer for fastapi-postgres
├── models/
│   └── project.py       # Project dataclass with ProjectState enum
└── services/
    ├── docker.py        # Docker compose operations
    ├── git.py           # Git operations
    └── project.py       # Project lifecycle (create, get, list, delete, update)
```

### How the Current System Works

1. `chat.py` creates an `AgentSession` per project
2. User messages go to `AgentSession.handle_user_message()`
3. AgentSession runs a ReAct loop: LLM call → tool execution → loop
4. Events are yielded as `AgentEvent` objects: `agent_message_start`, `agent_message_delta`, `agent_message_end`, `tool_call_start`, `tool_call_result`, `build_complete`, `waiting_for_user`, `ask_user`, `error`, `stopped`
5. `chat.py` sends these events over WebSocket to the frontend
6. The frontend renders them (chat messages, tool progress, Swagger iframe)

### Key Existing Files You Must Understand Before Changing

**`backend/app/agent/core.py`** — This is the file being replaced. Study it carefully:
- `AgentEvent` dataclass: `type: str`, `data: dict`
- `AgentSession.__init__()`: takes a `Project`, creates `ConversationContext`, sets `_max_tool_rounds = 30`
- `AgentSession.handle_user_message()`: yields `AgentEvent`s. Handles `_pending_ask_user_tc_id` for the ask_user tool pause/resume pattern.
- `AgentSession._continue_agent_loop()`: runs up to `_max_tool_rounds` iterations
- `AgentSession._run_llm_turn()`: one LLM call, streams text, accumulates tool calls, executes them
- The `ask_user` tool has special handling: it sets `_pending_ask_user_tc_id` and returns, pausing the loop. When the user responds, the answer is injected as a tool result and the loop continues.

**`backend/app/agent/llm.py`** — Simple OpenRouter client:
- `chat_completion_stream(messages, tools)` — uses `settings.OPENROUTER_MODEL` (currently `minimax/minimax-m2.5`)
- Returns an async generator of streaming chunks

**`backend/app/agent/context.py`** — `ConversationContext`:
- `messages: list[dict]` starting with `[{"role": "system", "content": SYSTEM_PROMPT}]`
- Methods: `add_user_message()`, `add_assistant_message()`, `add_assistant_tool_calls()`, `add_tool_result()`, `get_messages()`
- `load_from_db()`: restores from SQLite on session creation
- All mutations are persisted to SQLite via `_persist()`

**`backend/app/agent/tools.py`** — `execute_tool(project, tool_name, arguments)`:
- Big if/elif chain handling: `read_file`, `write_file`, `edit_file`, `list_directory`, `run_command`, `git_commit`, `git_log`, `docker_compose_up`, `docker_compose_down`, `docker_status`, `docker_logs`, `scaffold_project`, `build_complete`, `ask_user`
- Returns result as a string
- `ask_user` returns `"__ASK_USER__"` (handled specially by core.py)

**`backend/app/agent/prompts.py`** — `SYSTEM_PROMPT` string + `TOOL_SCHEMAS` list (OpenAI function-calling format)

**`backend/app/routers/chat.py`** — WebSocket handler:
- `_sessions: dict[str, AgentSession]` — active sessions keyed by project_id
- `_get_or_create_session()`: creates AgentSession, calls `context.load_from_db()`
- `chat_ws()`: accepts WebSocket, runs agent, sends events
- Sends sidebar updates (file tree, git commits) after file-modifying tool calls
- Handles `state_update` events when `project.state` changes

**`backend/app/models/project.py`** — `Project` dataclass:
- Fields: `id`, `name`, `description`, `state` (ProjectState enum), `app_port`, `db_port`, `created_at`, `swagger_url`, `api_url`
- `ProjectState`: CREATED, SCAFFOLDED, GENERATING, BUILDING, RUNNING, ERROR, STOPPED
- `directory` property: `settings.PROJECTS_DIR / self.id`

---

## Current Goal: Phase 2 — Multi-Agent Orchestrator (Track 1)

Build the **hybrid orchestrator** that replaces the monolithic `AgentSession`. This is the backbone that all specialist agents plug into. The orchestrator manages phases, shared state, agent dispatch, and user interruption handling.

### What You Are Building

You are building **Track 1** of a 5-track parallel development effort. Other team members are building specialist agents (clarification, planning, database, API, devops) that will plug into your orchestrator via a shared `BaseAgent` interface. Your job is to build that interface and the orchestrator that calls it.

### Files to Create

#### 1. `backend/app/agent/state.py` — Shared State and Data Contracts

This file defines ALL shared data structures. Every other track depends on this. It must be complete and stable.

```python
from __future__ import annotations
import enum
import json
from dataclasses import dataclass, field
from typing import Any


# ── Field and Entity Specs ──────────────────────────────────────

@dataclass
class FieldSpec:
    name: str
    type: str           # str, int, float, bool, datetime, text
    nullable: bool = False
    unique: bool = False
    default: Any = None

@dataclass
class EntitySpec:
    name: str
    fields: list[FieldSpec] = field(default_factory=list)

@dataclass
class Relationship:
    entity_a: str
    entity_b: str
    type: str           # one_to_one, one_to_many, many_to_many


# ── ProjectSpec — output of research phase ──────────────────────

@dataclass
class ProjectSpec:
    entities: list[EntitySpec] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    endpoints: str = "crud_default"     # crud_default or list of custom endpoints
    database: str = "postgresql"
    auth_required: bool = False
    extra_requirements: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if spec has minimum required information."""
        if not self.entities:
            return False
        for entity in self.entities:
            if not entity.fields:
                return False
        # If multiple entities exist, relationships should be defined
        if len(self.entities) > 1 and not self.relationships:
            return False
        return True

    def missing_fields(self) -> list[str]:
        """Return list of what's still needed."""
        missing = []
        if not self.entities:
            missing.append("At least one entity is required")
        for entity in self.entities:
            if not entity.fields:
                missing.append(f"Entity '{entity.name}' has no fields defined")
        if len(self.entities) > 1 and not self.relationships:
            missing.append("Relationships between entities are not defined")
        return missing


# ── Task and TaskManifest — output of planning phase ────────────

@dataclass
class Task:
    id: str
    type: str               # scaffold, create_models, create_routes, update_main, docker_up
    description: str
    agent: str              # scaffold, database, api, devops
    dependencies: list[str] = field(default_factory=list)   # task IDs
    context: dict = field(default_factory=dict)              # scoped data for this task
    status: str = "pending" # pending, running, completed, failed
    retries: int = 0
    error: str | None = None

@dataclass
class TaskManifest:
    tasks: list[Task] = field(default_factory=list)

    def get_next_task(self) -> Task | None:
        """Return next pending task whose dependencies are all completed."""
        completed_ids = {t.id for t in self.tasks if t.status == "completed"}
        for task in self.tasks:
            if task.status == "pending":
                if all(dep in completed_ids for dep in task.dependencies):
                    return task
        return None

    def all_complete(self) -> bool:
        return all(t.status == "completed" for t in self.tasks)

    def mark_complete(self, task_id: str) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.status = "completed"
                return

    def mark_failed(self, task_id: str, error: str) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.status = "failed"
                t.retries += 1
                t.error = error
                return

    def reset_for_retry(self, task_id: str) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.status = "pending"
                return

    def append_tasks(self, new_tasks: list[Task]) -> None:
        """For delta planning — append new tasks to existing manifest."""
        self.tasks.extend(new_tasks)


# ── Errors ──────────────────────────────────────────────────────

@dataclass
class AgentError:
    agent: str
    task_id: str | None
    message: str
    file_path: str | None = None
    timestamp: str = ""


# ── AgentResult — returned by every agent ───────────────────────

@dataclass
class AgentResult:
    status: str             # success, error, needs_user_input
    state_updates: dict = field(default_factory=dict)  # partial updates for SharedState
    files_modified: list[str] = field(default_factory=list)
    message: str | None = None      # message to show user
    error: str | None = None

    # Phase-specific outputs (set by specific agents)
    spec: ProjectSpec | None = None         # set by clarification agent
    manifest: TaskManifest | None = None    # set by planning agent


# ── SharedState — central state object ──────────────────────────

class Phase(str, enum.Enum):
    RESEARCH = "research"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    COMPLETE = "complete"

@dataclass
class SharedState:
    project_id: str
    current_phase: Phase = Phase.RESEARCH
    spec: ProjectSpec | None = None
    manifest: TaskManifest | None = None
    files_created: list[str] = field(default_factory=list)
    errors: list[AgentError] = field(default_factory=list)
    user_conversation: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for SQLite persistence."""
        return {
            "project_id": self.project_id,
            "current_phase": self.current_phase.value,
            "spec": json.dumps(self.spec.__dict__) if self.spec else None,
            "manifest": json.dumps([t.__dict__ for t in self.manifest.tasks]) if self.manifest else None,
            "files_created": json.dumps(self.files_created),
            "errors": json.dumps([e.__dict__ for e in self.errors]),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SharedState:
        """Deserialize from SQLite."""
        state = cls(project_id=data["project_id"])
        state.current_phase = Phase(data.get("current_phase", "research"))
        if data.get("spec"):
            spec_data = json.loads(data["spec"])
            state.spec = ProjectSpec(**spec_data)
        if data.get("manifest"):
            tasks_data = json.loads(data["manifest"])
            state.manifest = TaskManifest(tasks=[Task(**t) for t in tasks_data])
        if data.get("files_created"):
            state.files_created = json.loads(data["files_created"])
        if data.get("errors"):
            state.errors = [AgentError(**e) for e in json.loads(data["errors"])]
        return state
```

**IMPORTANT:** This dataclass structure is a starting point. Flesh out the serialization/deserialization to handle nested dataclasses properly (EntitySpec contains FieldSpec, Relationship is its own dataclass, etc.). Add proper JSON encoding that handles all nested types. Test round-trip serialization: `state == SharedState.from_dict(state.to_dict())`.

#### 2. `backend/app/agent/base.py` — Base Agent Class

Every specialist agent extends this. It provides the reusable ReAct loop extracted from the current `core.py`.

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator

from app.agent.state import SharedState, Task, AgentResult


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
    model: str | None = None                    # None = use default from settings
    system_prompt: str = ""
    tool_names: list[str] = []                  # subset of tools this agent can use
    max_tool_rounds: int = 20

    def get_tool_schemas(self) -> list[dict]:
        """Filter global TOOL_SCHEMAS to only include this agent's tools."""
        from app.agent.prompts import TOOL_SCHEMAS
        if not self.tool_names:
            return TOOL_SCHEMAS
        return [s for s in TOOL_SCHEMAS if s["function"]["name"] in self.tool_names]

    @abstractmethod
    async def run(
        self,
        state: SharedState,
        task: Task | None = None,
        user_message: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent work.

        Yields AgentEvent objects for streaming to the UI.
        The LAST event before returning should indicate the result.

        Args:
            state: Current shared state (read from, don't mutate directly)
            task: Optional task from the manifest (for implementation agents)
            user_message: Optional user message (for conversational agents)

        Yields:
            AgentEvent objects (text streaming, tool calls, etc.)
        """
        ...

    async def get_result(self) -> AgentResult:
        """Called by orchestrator after run() completes to get structured result.

        Override this in subclasses. Default returns success.
        """
        return AgentResult(status="success")
```

**IMPORTANT — ReAct Loop Extraction:**

The current `core.py` has the ReAct loop in `_run_llm_turn()` and `_continue_agent_loop()`. Extract this logic into a helper method on `BaseAgent` that subclasses can call:

```python
async def _run_react_loop(
    self,
    messages: list[dict],
    project: Project,
) -> AsyncGenerator[AgentEvent, None]:
    """Reusable ReAct loop: LLM call → stream text → execute tools → loop.

    This is the core loop extracted from the prototype's AgentSession.
    Specialist agents call this with their own messages and tool subset.
    """
    # ... extracted from core.py _continue_agent_loop + _run_llm_turn
    # Use self.model for the LLM call (passed to chat_completion_stream)
    # Use self.get_tool_schemas() for the tool list
    # Use self.max_tool_rounds as the safety limit
```

The key here is that the ReAct loop logic lives once in `BaseAgent` and every specialist agent gets it for free. They just configure `system_prompt`, `tool_names`, and `model`, then call `_run_react_loop()` from their `run()` method.

**Handle the ask_user pattern:** The current `_pending_ask_user_tc_id` pattern must work in the base class. When an agent calls `ask_user`, the loop pauses and yields an `ask_user` event. The orchestrator captures this state. When the user responds, the orchestrator calls the agent's `run()` again with the user's answer as `user_message`, and the agent injects it as a tool result and continues.

#### 3. `backend/app/agent/orchestrator.py` — The Hybrid Orchestrator

This replaces `AgentSession` as the main entry point. The WebSocket layer (`chat.py`) creates an `OrchestratorSession` instead of `AgentSession`.

```python
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
        self._agents: dict[str, BaseAgent] = {}     # registered agents by name
        self._active_agent: BaseAgent | None = None  # currently running agent
        self._pending_ask_user: dict | None = None   # ask_user pause state
        self._register_agents()

    def _register_agents(self) -> None:
        """Register all available specialist agents.

        Import and instantiate each agent. If an agent's module doesn't exist
        yet (other tracks haven't built it), skip it gracefully and log a warning.
        This allows incremental integration — the orchestrator works with whatever
        agents are available, and falls back to single-agent prototype for the rest.
        """
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
                import logging
                logging.getLogger(__name__).warning(f"Agent '{name}' not available: {e}")

    async def handle_user_message(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        """Process user message. Called by chat.py.

        CRITICAL: Must yield the same AgentEvent types as old AgentSession.
        """
        ...

    def cancel(self) -> None:
        self._cancelled = True
```

**Orchestrator Core Logic — implement this carefully:**

```
handle_user_message(message):
    1. Add message to state.user_conversation

    2. If _pending_ask_user is set:
       → Resume the active agent with the user's answer (inject as tool result)
       → Continue the agent's ReAct loop
       → yield events from the agent
       → Check if agent is done (returned AgentResult)
       → If done, handle phase transition
       → return

    3. If current_phase is IMPLEMENTATION and a task is in progress:
       → Classify the interruption (see below)
       → Handle based on classification
       → return

    4. Otherwise, route to the appropriate phase:

       RESEARCH:
         → If clarification agent is available: dispatch to it with user_message
         → If not available: fall back to single-agent AgentSession
         → When agent returns AgentResult with spec:
           → state.spec = result.spec
           → state.current_phase = Phase.PLANNING
           → yield AgentEvent(type="phase_transition", data={"from": "research", "to": "planning"})
           → Immediately run planning phase (no user message needed)

       PLANNING:
         → Dispatch to planning agent with state.spec
         → When agent returns AgentResult with manifest:
           → state.manifest = result.manifest
           → state.current_phase = Phase.IMPLEMENTATION
           → yield AgentEvent(type="phase_transition", data={"from": "planning", "to": "implementation"})
           → Begin implementation: pick first task, dispatch to agent

       IMPLEMENTATION:
         → Pick next task from manifest (get_next_task)
         → If no task available: all done → transition to VALIDATION
         → Dispatch to the agent named in task.agent
         → yield AgentEvent(type="task_start", data={"task_id": task.id, "description": task.description})
         → When agent returns AgentResult:
           → If success: mark_complete, yield task_complete, pick next task
           → If error: mark_failed, retry up to 3 times, then record error
         → When all tasks complete:
           → state.current_phase = Phase.VALIDATION
           → Dispatch to devops agent

       VALIDATION:
         → Dispatch to devops agent
         → If success: state.current_phase = Phase.COMPLETE
         → If error: feed error back to relevant implementation agent (retry loop)

       COMPLETE:
         → User wants changes? Classify as interruption, handle accordingly

    5. After every phase transition: persist state to SQLite via save_state()
```

**IMPORTANT — Automatic Phase Chaining:**

When the research phase completes, the orchestrator should NOT wait for another user message to start planning. It should immediately chain into planning, and then into implementation. The user only interacts during research (answering clarification questions) and during completion (testing their API). The planning → implementation → validation flow runs automatically.

Yield status events so the user sees what's happening:
```python
yield AgentEvent(type="agent_message_start")
yield AgentEvent(type="agent_message_delta", data={"token": "Planning your project structure..."})
yield AgentEvent(type="agent_message_end")
yield AgentEvent(type="phase_transition", data={"from": "research", "to": "planning"})
```

**Interruption Classification:**

When a user sends a message during implementation, make a lightweight LLM call:

```python
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

async def _classify_interruption(self, message: str) -> str:
    """Classify user interruption. Returns: MINOR_EDIT, ADDITIVE, BREAKING, UNRELATED"""
    from app.agent.llm import chat_completion
    prompt = CLASSIFY_PROMPT.format(
        phase=self.state.current_phase.value,
        spec_summary=str(self.state.spec) if self.state.spec else "None",
        current_task=str(self._current_task) if self._current_task else "None",
        user_message=message,
    )
    response = await chat_completion([{"role": "user", "content": prompt}])
    classification = response.strip().upper()
    if classification not in ("MINOR_EDIT", "ADDITIVE", "BREAKING", "UNRELATED"):
        return "UNRELATED"  # safe default
    return classification
```

**Interruption Handling:**

```python
async def _handle_interruption(self, classification: str, message: str):
    if classification == "MINOR_EDIT":
        # Stay in implementation
        # Create an ad-hoc edit task
        # Determine which agent should handle it (database agent for model changes, api agent for route changes)
        # Dispatch the edit task
        ...

    elif classification == "ADDITIVE":
        # Transition to PLANNING phase
        # Call planning agent in delta mode:
        #   - Pass existing manifest + new requirement description
        #   - Planning agent returns only NEW tasks
        # Append new tasks to existing manifest
        # Transition back to IMPLEMENTATION
        # Continue executing tasks
        ...

    elif classification == "BREAKING":
        # Git commit current state as safety checkpoint
        # Transition to RESEARCH phase
        # Clarification agent gathers new requirements
        # Full re-plan, then re-implement
        ...

    elif classification == "UNRELATED":
        # Respond directly, no phase change
        # Use a simple LLM call to answer the question using SharedState context
        yield AgentEvent(type="agent_message_start")
        yield AgentEvent(type="agent_message_delta", data={"token": response})
        yield AgentEvent(type="agent_message_end")
        yield AgentEvent(type="waiting_for_user")
```

**Fallback Behavior:**

If a specialist agent is not yet available (other tracks haven't built it), fall back to the old single-agent `AgentSession`. This ensures the system always works during incremental integration.

```python
async def _fallback_to_prototype(self, message: str) -> AsyncGenerator[AgentEvent, None]:
    """Fall back to single-agent prototype when specialist agents aren't ready."""
    from app.agent.core import AgentSession
    if not hasattr(self, '_fallback_session'):
        self._fallback_session = AgentSession(self.project)
        await self._fallback_session.context.load_from_db(self.project.id)
    async for event in self._fallback_session.handle_user_message(message):
        yield event
```

### Files to Modify

#### 4. `backend/app/agent/llm.py` — Multi-Model Support

Add a `model` parameter and a non-streaming function:

```python
async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,       # NEW: per-agent model override
):
    """Yield streaming chunks from OpenRouter.

    Args:
        model: If provided, use this model. Otherwise use settings.OPENROUTER_MODEL.
    """
    kwargs: dict = {
        "model": model or settings.OPENROUTER_MODEL,  # CHANGED
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    client = get_client()
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        yield chunk


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming completion for classification tasks (e.g., interruption classifier).

    Returns the text content of the response.
    """
    client = get_client()
    response = await client.chat.completions.create(
        model=model or settings.OPENROUTER_MODEL,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""
```

**Changes required:**
- Add `model` parameter to `chat_completion_stream()` with fallback to `settings.OPENROUTER_MODEL`
- Add new `chat_completion()` function (non-streaming) for the orchestrator's classification calls
- Keep all existing behavior intact when `model=None`

#### 5. `backend/app/agent/context.py` — Scoped Context

Add `ScopedContext` alongside the existing `ConversationContext` (do NOT remove it — the fallback path needs it):

```python
class ScopedContext:
    """Context for a single agent's conversation.

    Unlike ConversationContext which always uses the global SYSTEM_PROMPT,
    this takes a custom system prompt and can be seeded with relevant context.
    """

    def __init__(self, system_prompt: str, seed_messages: list[dict] | None = None) -> None:
        self.messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if seed_messages:
            self.messages.extend(seed_messages)

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_assistant_tool_calls(self, content: str | None, tool_calls: list[dict]) -> None:
        msg = {"role": "assistant", "tool_calls": tool_calls}
        if content:
            msg["content"] = content
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": result})

    def get_messages(self) -> list[dict]:
        return self.messages

    def reset(self, keep_system: bool = True) -> None:
        """Clear conversation but optionally keep the system prompt."""
        if keep_system and self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
```

The orchestrator also maintains a **master conversation** (the full user-facing chat, same as the old ConversationContext). Agent-scoped contexts are ephemeral — created for each agent dispatch, discarded after. The master conversation is what gets persisted.

#### 6. `backend/app/routers/chat.py` — Wire Up Orchestrator

Minimal changes — swap the session class:

```python
from app.agent.orchestrator import OrchestratorSession

# Change the session type
_sessions: dict[str, OrchestratorSession] = {}

async def _get_or_create_session(project_id: str) -> OrchestratorSession | None:
    if project_id in _sessions:
        return _sessions[project_id]
    project = await project_svc.get_project(project_id)
    if project is None:
        return None
    session = OrchestratorSession(project)
    await session.restore_state()  # NEW: restore SharedState from SQLite
    _sessions[project_id] = session
    return session
```

**CRITICAL:** The rest of `chat.py` should require ZERO other changes. `handle_user_message()` yields `AgentEvent` objects — the iteration loop is identical. The sidebar updates, state updates, build_complete handling — all stay the same.

New event types to handle (optional, for enhanced UI):
- `phase_transition`: `{"from": "research", "to": "planning"}` — frontend can show a phase indicator
- `task_start`: `{"task_id": "t1", "description": "Scaffolding project"}` — frontend can show progress
- `task_complete`: `{"task_id": "t1"}` — frontend can check off tasks

If the frontend doesn't handle these new events, it ignores them safely. No breakage.

#### 7. `backend/app/agent/tools.py` and `backend/app/agent/prompts.py` — New Tools

Add tool schemas and implementations for the research and planning agents.

**New tool schemas (add to the TOOL_SCHEMAS list in prompts.py):**

```python
{
    "type": "function",
    "function": {
        "name": "check_spec_completeness",
        "description": "Check if the current project specification has all required information. Returns a list of missing fields, or empty list if complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "spec_json": {
                    "type": "string",
                    "description": "The current ProjectSpec as a JSON string"
                }
            },
            "required": ["spec_json"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "finalize_spec",
        "description": "Submit the complete project specification. Call this when the user has confirmed the requirements summary. This signals the end of the research phase.",
        "parameters": {
            "type": "object",
            "properties": {
                "spec_json": {
                    "type": "string",
                    "description": "The complete ProjectSpec as a JSON string"
                }
            },
            "required": ["spec_json"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "submit_plan",
        "description": "Submit the task manifest for the project. This signals the end of the planning phase.",
        "parameters": {
            "type": "object",
            "properties": {
                "manifest_json": {
                    "type": "string",
                    "description": "The TaskManifest as a JSON string (array of task objects)"
                }
            },
            "required": ["manifest_json"],
        },
    },
},
```

**New tool implementations (add to execute_tool in tools.py):**

```python
elif tool_name == "check_spec_completeness":
    spec_json = arguments.get("spec_json", "{}")
    try:
        spec_data = json.loads(spec_json)
        spec = ProjectSpec(**spec_data)  # needs proper nested deserialization
        missing = spec.missing_fields()
        return json.dumps({"complete": len(missing) == 0, "missing": missing})
    except Exception as e:
        return f"Error parsing spec: {e}"

elif tool_name == "finalize_spec":
    spec_json = arguments.get("spec_json", "{}")
    return f"__FINALIZE_SPEC__{spec_json}"  # Orchestrator intercepts this

elif tool_name == "submit_plan":
    manifest_json = arguments.get("manifest_json", "[]")
    return f"__SUBMIT_PLAN__{manifest_json}"  # Orchestrator intercepts this
```

The `__FINALIZE_SPEC__` and `__SUBMIT_PLAN__` sentinel patterns follow the same approach as the existing `__ASK_USER__` pattern — the orchestrator intercepts these return values and handles them specially (updating SharedState, triggering phase transitions).

### SharedState Persistence

Add a new SQLite table for shared state. Add this to `db.py`'s `init_db()` function:

```sql
CREATE TABLE IF NOT EXISTS shared_state (
    project_id TEXT PRIMARY KEY,
    current_phase TEXT NOT NULL DEFAULT 'research',
    spec_json TEXT,
    manifest_json TEXT,
    files_created TEXT DEFAULT '[]',
    errors TEXT DEFAULT '[]',
    updated_at TEXT
);
```

The orchestrator calls `save_state()` after every phase transition and `restore_state()` on session creation.

### Backward Compatibility Checklist

Before considering this done, verify every item:

- [ ] `OrchestratorSession.handle_user_message()` yields the same `AgentEvent` types as old `AgentSession`
- [ ] The `ask_user` pause/resume pattern works identically
- [ ] `chat.py` changes are minimal (just swap session class + add restore_state call)
- [ ] Frontend receives events and renders them without any changes
- [ ] Fallback to single-agent `AgentSession` works when specialist agents aren't available
- [ ] SharedState persists to SQLite and restores correctly on session reload
- [ ] Existing project creation, listing, deletion still works
- [ ] Existing `ConversationContext` class still works (don't remove it)

### Testing Strategy

1. **Unit test `state.py`:** Round-trip serialization of all dataclasses including nested types
2. **Unit test `base.py`:** Tool schema filtering returns correct subset
3. **Unit test `TaskManifest`:** `get_next_task()` respects dependencies, `mark_complete()` works, `all_complete()` transitions correctly
4. **Integration test:** Create OrchestratorSession, send a user message, verify AgentEvents are yielded
5. **Fallback test:** Remove all agent modules from agents/, verify orchestrator falls back to single-agent
6. **Persistence test:** Create session, advance to planning phase, kill and restore session, verify phase is preserved
7. **Interruption test:** Send a message during implementation, verify classification returns valid type

### What NOT to Build

- Do NOT build any specialist agents (clarification, planning, database, api, devops) — other tracks own those
- Do NOT write system prompts for specialist agents — other tracks own those
- Do NOT modify the frontend — the WebSocket event interface stays identical
- Do NOT change docker.py — Track 5 owns Docker changes
- Do NOT change scaffold.py — Track 3 owns template changes
- Do NOT change the Project model or project service — keep those stable
- Do NOT delete or rename core.py — the fallback path needs it

### Definition of Done

- [ ] `state.py` defines all shared data structures with working nested serialization
- [ ] `base.py` provides BaseAgent with reusable ReAct loop that any agent can call
- [ ] `orchestrator.py` manages phase transitions: research → planning → implementation → validation → complete
- [ ] `orchestrator.py` automatically chains phases (research done → immediately runs planning → immediately runs implementation)
- [ ] `orchestrator.py` dispatches tasks from TaskManifest to registered agents by name
- [ ] `orchestrator.py` classifies user interruptions (MINOR_EDIT, ADDITIVE, BREAKING, UNRELATED)
- [ ] `orchestrator.py` handles ADDITIVE interruptions via delta planning
- [ ] `orchestrator.py` falls back to single-agent AgentSession when agents unavailable
- [ ] `llm.py` supports per-agent model override and non-streaming classification calls
- [ ] `context.py` provides ScopedContext with custom system prompts (old ConversationContext untouched)
- [ ] `chat.py` uses OrchestratorSession with zero frontend breakage
- [ ] New tools (check_spec_completeness, finalize_spec, submit_plan) registered in prompts.py and tools.py
- [ ] SharedState persists to SQLite (new table) and restores on session reload
- [ ] The ask_user pause/resume pattern works through the orchestrator
- [ ] All existing functionality preserved — the prototype still works via fallback