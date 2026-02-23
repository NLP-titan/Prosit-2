from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, BaseLoader

from app.config import settings
from app.models.project import Project


# ── Registry Data Structures ────────────────────────────────────


@dataclass
class TemplateInfo:
    name: str
    path: Path
    description: str
    supported_addons: list[str] = field(default_factory=list)


@dataclass
class AddonInfo:
    """Describes a composable addon that layers onto a base template.

    Addons are NOT standalone templates. They extend a base template with
    additional files and configuration (e.g., auth middleware, caching layer).
    The `compatible_bases` field declares which base templates this addon
    can compose with.

    Addon directories do not exist yet — these entries define the convention
    for where addon files will live when they are created in future sprints.
    """

    name: str
    path: Path
    description: str
    compatible_bases: list[str] = field(default_factory=list)
    priority: int = 0


# ── Registry Population ─────────────────────────────────────────

TEMPLATE_REGISTRY: dict[str, TemplateInfo] = {
    "fastapi-postgres": TemplateInfo(
        name="fastapi-postgres",
        path=settings.TEMPLATES_DIR / "fastapi-postgres",
        description="FastAPI + PostgreSQL + async SQLAlchemy",
        supported_addons=["auth", "relations", "redis"],
    ),
    # Future base templates (not yet created):
    # "fastapi-mongodb": TemplateInfo(...)   — Priority 3
    # "fastapi-mysql": TemplateInfo(...)     — Priority 4
}

ADDON_REGISTRY: dict[str, AddonInfo] = {
    "auth": AddonInfo(
        name="auth",
        path=settings.TEMPLATES_DIR / "addons" / "auth",
        description="JWT auth, Users table, bcrypt, protected routes, token refresh",
        compatible_bases=["fastapi-postgres"],
        priority=1,
    ),
    "relations": AddonInfo(
        name="relations",
        path=settings.TEMPLATES_DIR / "addons" / "relations",
        description="Many-to-many junction tables, nested serialization, cascade config",
        compatible_bases=["fastapi-postgres"],
        priority=2,
    ),
    "redis": AddonInfo(
        name="redis",
        path=settings.TEMPLATES_DIR / "addons" / "redis",
        description="Composable cache layer for any base template",
        compatible_bases=["fastapi-postgres"],
        priority=5,
    ),
}

# Backward-compat alias used by other modules
TEMPLATE_DIR = TEMPLATE_REGISTRY["fastapi-postgres"].path


# ── Registry Lookup ──────────────────────────────────────────────


def get_template_dir(template_name: str) -> Path:
    """Resolve a template name to its directory path."""
    info = TEMPLATE_REGISTRY.get(template_name)
    if info is None:
        available = ", ".join(TEMPLATE_REGISTRY.keys())
        raise ValueError(
            f"Unknown template '{template_name}'. Available: {available}"
        )
    return info.path


def get_available_templates() -> list[TemplateInfo]:
    """Return all registered base templates."""
    return list(TEMPLATE_REGISTRY.values())


def get_compatible_addons(template_name: str) -> list[AddonInfo]:
    """Return addons compatible with the given base template."""
    return [
        addon
        for addon in ADDON_REGISTRY.values()
        if template_name in addon.compatible_bases
    ]


# ── Scaffold Function ────────────────────────────────────────────


def scaffold_project(
    project: Project,
    template_name: str = "fastapi-postgres",
) -> None:
    """Copy and render a template into the project directory."""
    template_dir = get_template_dir(template_name)
    project_dir = project.directory
    project_dir.mkdir(parents=True, exist_ok=True)

    project_name = project.name or project.id
    project_name = project_name.lower().replace(" ", "_").replace("-", "_")

    context = {
        "project_name": project_name,
        "app_port": project.app_port,
        "db_port": project.db_port,
    }

    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)

    for src_path in template_dir.rglob("*"):
        rel = src_path.relative_to(template_dir)
        rel_str = str(rel).replace("{{project_name}}", project_name)
        dest = project_dir / rel_str

        if src_path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue

        raw = src_path.read_text()
        try:
            rendered = env.from_string(raw).render(**context)
        except Exception:
            rendered = raw

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered)
