from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


class ProjectState(str, enum.Enum):
    CREATED = "created"
    SCAFFOLDED = "scaffolded"
    GENERATING = "generating"
    BUILDING = "building"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class Project:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    state: ProjectState = ProjectState.CREATED
    app_port: int = 0
    db_port: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    swagger_url: str = ""
    api_url: str = ""

    @property
    def directory(self) -> Path:
        return settings.PROJECTS_DIR / self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "app_port": self.app_port,
            "db_port": self.db_port,
            "created_at": self.created_at,
            "swagger_url": self.swagger_url,
            "api_url": self.api_url,
        }

    @classmethod
    def from_row(cls, row) -> Project:
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            state=ProjectState(row["state"]),
            app_port=row["app_port"],
            db_port=row["db_port"],
            created_at=row["created_at"],
            swagger_url=row["swagger_url"],
            api_url=row["api_url"],
        )
