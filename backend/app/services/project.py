from __future__ import annotations

import shutil

from app.config import settings
from app.db import get_db
from app.models.project import Project, ProjectState


async def _next_ports() -> tuple[int, int]:
    """Allocate the next available app_port and db_port."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT MAX(app_port) as max_app, MAX(db_port) as max_db FROM projects")
        row = await cursor.fetchone()
        max_app = row["max_app"] if row["max_app"] else 0
        max_db = row["max_db"] if row["max_db"] else 0

        app_port = max(settings.APP_PORT_START, max_app + 1)
        db_port = max(settings.DB_PORT_START, max_db + 1)
        return app_port, db_port
    finally:
        await db.close()


async def create_project(name: str = "", description: str = "") -> Project:
    app_port, db_port = await _next_ports()
    project = Project(name=name, description=description, app_port=app_port, db_port=db_port)
    project.directory.mkdir(parents=True, exist_ok=True)

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO projects (id, name, description, state, app_port, db_port, created_at, swagger_url, api_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project.id, project.name, project.description, project.state.value,
             project.app_port, project.db_port, project.created_at, project.swagger_url, project.api_url),
        )
        await db.commit()
    finally:
        await db.close()

    return project


async def get_project(project_id: str) -> Project | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return Project.from_row(row)
    finally:
        await db.close()


async def list_projects() -> list[Project]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Project.from_row(r) for r in rows]
    finally:
        await db.close()


async def delete_project(project_id: str) -> bool:
    project = await get_project(project_id)
    if project is None:
        return False

    db = await get_db()
    try:
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
    finally:
        await db.close()

    if project.directory.exists():
        shutil.rmtree(project.directory)
    return True


async def update_project(project: Project) -> None:
    """Persist current project state to SQLite."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE projects SET name=?, description=?, state=?, app_port=?, db_port=?,
               swagger_url=?, api_url=? WHERE id=?""",
            (project.name, project.description, project.state.value, project.app_port,
             project.db_port, project.swagger_url, project.api_url, project.id),
        )
        await db.commit()
    finally:
        await db.close()
