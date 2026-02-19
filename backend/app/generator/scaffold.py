from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, BaseLoader

from app.config import settings
from app.models.project import Project

TEMPLATE_DIR = settings.TEMPLATES_DIR / "fastapi-postgres"


def scaffold_project(project: Project) -> None:
    """Copy and render the FastAPI+PostgreSQL template into the project directory."""
    project_dir = project.directory
    project_dir.mkdir(parents=True, exist_ok=True)

    project_name = project.name or project.id
    # Sanitize: lowercase, replace spaces with underscores
    project_name = project_name.lower().replace(" ", "_").replace("-", "_")

    context = {
        "project_name": project_name,
        "app_port": project.app_port,
        "db_port": project.db_port,
    }

    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)

    for src_path in TEMPLATE_DIR.rglob("*"):
        # Compute relative path, replacing {{project_name}} with actual name
        rel = src_path.relative_to(TEMPLATE_DIR)
        rel_str = str(rel).replace("{{project_name}}", project_name)
        dest = project_dir / rel_str

        if src_path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            continue

        # Render file content through Jinja2
        raw = src_path.read_text()
        try:
            rendered = env.from_string(raw).render(**context)
        except Exception:
            rendered = raw  # If Jinja fails, use raw content

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered)
