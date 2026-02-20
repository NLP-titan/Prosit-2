from __future__ import annotations

import enum
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── Field and Entity Specs ──────────────────────────────────────


@dataclass
class FieldSpec:
    name: str
    type: str  # str, int, float, bool, datetime, text
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
    type: str  # one_to_one, one_to_many, many_to_many


# ── ProjectSpec — output of research phase ──────────────────────


@dataclass
class ProjectSpec:
    entities: list[EntitySpec] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    endpoints: str = "crud_default"
    database: str = "postgresql"
    auth_required: bool = False
    extra_requirements: list[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        if not self.entities:
            return False
        for entity in self.entities:
            if not entity.fields:
                return False
        if len(self.entities) > 1 and not self.relationships:
            return False
        return True

    def missing_fields(self) -> list[str]:
        missing = []
        if not self.entities:
            missing.append("At least one entity is required")
        for entity in self.entities:
            if not entity.fields:
                missing.append(f"Entity '{entity.name}' has no fields defined")
        if len(self.entities) > 1 and not self.relationships:
            missing.append("Relationships between entities are not defined")
        return missing

    def to_dict(self) -> dict:
        return {
            "entities": [
                {
                    "name": e.name,
                    "fields": [asdict(f) for f in e.fields],
                }
                for e in self.entities
            ],
            "relationships": [asdict(r) for r in self.relationships],
            "endpoints": self.endpoints,
            "database": self.database,
            "auth_required": self.auth_required,
            "extra_requirements": self.extra_requirements,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectSpec:
        entities = []
        for e_data in data.get("entities", []):
            fields = [FieldSpec(**f) for f in e_data.get("fields", [])]
            entities.append(EntitySpec(name=e_data["name"], fields=fields))
        relationships = [
            Relationship(**r) for r in data.get("relationships", [])
        ]
        return cls(
            entities=entities,
            relationships=relationships,
            endpoints=data.get("endpoints", "crud_default"),
            database=data.get("database", "postgresql"),
            auth_required=data.get("auth_required", False),
            extra_requirements=data.get("extra_requirements", []),
        )


# ── Task and TaskManifest — output of planning phase ────────────


@dataclass
class Task:
    id: str
    type: str  # scaffold, create_models, create_routes, update_main, docker_up
    description: str
    agent: str  # scaffold, database, api, devops
    dependencies: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    retries: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        return cls(
            id=data["id"],
            type=data["type"],
            description=data["description"],
            agent=data["agent"],
            dependencies=data.get("dependencies", []),
            context=data.get("context", {}),
            status=data.get("status", "pending"),
            retries=data.get("retries", 0),
            error=data.get("error"),
        )


@dataclass
class TaskManifest:
    tasks: list[Task] = field(default_factory=list)

    def get_next_task(self) -> Task | None:
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
        self.tasks.extend(new_tasks)

    def to_dict(self) -> list[dict]:
        return [t.to_dict() for t in self.tasks]

    @classmethod
    def from_dict(cls, data: list[dict]) -> TaskManifest:
        return cls(tasks=[Task.from_dict(t) for t in data])


# ── Errors ──────────────────────────────────────────────────────


@dataclass
class AgentError:
    agent: str
    task_id: str | None
    message: str
    file_path: str | None = None
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AgentError:
        return cls(**data)


# ── AgentResult — returned by every agent ───────────────────────


@dataclass
class AgentResult:
    status: str  # success, error, needs_user_input
    state_updates: dict = field(default_factory=dict)
    files_modified: list[str] = field(default_factory=list)
    message: str | None = None
    error: str | None = None
    spec: ProjectSpec | None = None
    manifest: TaskManifest | None = None


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
        return {
            "project_id": self.project_id,
            "current_phase": self.current_phase.value,
            "spec_json": json.dumps(self.spec.to_dict()) if self.spec else None,
            "manifest_json": (
                json.dumps(self.manifest.to_dict()) if self.manifest else None
            ),
            "files_created": json.dumps(self.files_created),
            "errors": json.dumps([e.to_dict() for e in self.errors]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SharedState:
        state = cls(project_id=data["project_id"])
        state.current_phase = Phase(data.get("current_phase", "research"))
        if data.get("spec_json"):
            spec_data = json.loads(data["spec_json"])
            state.spec = ProjectSpec.from_dict(spec_data)
        if data.get("manifest_json"):
            tasks_data = json.loads(data["manifest_json"])
            state.manifest = TaskManifest.from_dict(tasks_data)
        if data.get("files_created"):
            state.files_created = json.loads(data["files_created"])
        if data.get("errors"):
            errors_data = json.loads(data["errors"])
            state.errors = [AgentError.from_dict(e) for e in errors_data]
        return state
