"""Shared state dataclasses for the multi-agent architecture.

Defined by the Phase 2 spec (Section 3). Track 1 (Sam) owns this file.
This is a minimal version with the contracts needed by implementation agents.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    name: str
    type: str  # str, int, float, bool, datetime, text
    nullable: bool = False
    unique: bool = False
    default: str | None = None


@dataclass
class EntitySpec:
    name: str
    fields: list[FieldSpec] = field(default_factory=list)


@dataclass
class Relationship:
    entity_a: str
    entity_b: str
    type: str  # one_to_one | one_to_many | many_to_one | many_to_many


@dataclass
class ProjectSpec:
    entities: list[EntitySpec] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    endpoints: str = "crud_default"
    database: str = "postgresql"
    auth_required: bool = False
    extra_requirements: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str = field(default_factory=lambda: f"t-{uuid.uuid4().hex[:8]}")
    type: str = ""  # scaffold | create_models | create_routes | docker_up
    description: str = ""
    agent: str = ""  # scaffold | database | api | devops
    dependencies: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    status: str = "pending"  # pending | in_progress | completed | error


@dataclass
class TaskManifest:
    tasks: list[Task] = field(default_factory=list)

    def get_ready_tasks(self) -> list[Task]:
        completed_ids = {t.id for t in self.tasks if t.status == "completed"}
        return [
            t for t in self.tasks
            if t.status == "pending"
            and all(dep in completed_ids for dep in t.dependencies)
        ]

    def all_complete(self) -> bool:
        return all(t.status == "completed" for t in self.tasks)


@dataclass
class AgentError:
    agent: str
    task_id: str | None
    message: str
    error_type: str = "unknown"  # retryable | permanent | validation | unknown
    file_path: str | None = None
    suggested_fix: str | None = None


@dataclass
class AgentResult:
    status: str  # success | error | needs_user_input
    state_updates: dict = field(default_factory=dict)
    files_modified: list[str] = field(default_factory=list)
    message: str | None = None
    error: str | None = None


@dataclass
class SharedState:
    project_id: str = ""
    spec: ProjectSpec | None = None
    manifest: TaskManifest | None = None
    current_phase: str = "research"
    pending_tasks: list[Task] = field(default_factory=list)
    completed_tasks: list[Task] = field(default_factory=list)
    files_created: list[str] = field(default_factory=list)
    errors: list[AgentError] = field(default_factory=list)
    user_conversation: list[dict] = field(default_factory=list)
