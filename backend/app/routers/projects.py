from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.services import project as project_svc
from app.services import docker as docker_svc

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str = ""
    description: str = ""


@router.post("")
async def create_project(body: CreateProjectRequest):
    p = await project_svc.create_project(name=body.name, description=body.description)
    return p.to_dict()


@router.get("")
async def list_projects():
    projects = await project_svc.list_projects()
    return [p.to_dict() for p in projects]


@router.get("/{project_id}")
async def get_project(project_id: str):
    p = await project_svc.get_project(project_id)
    if p is None:
        raise HTTPException(404, "Project not found")
    return p.to_dict()


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    p = await project_svc.get_project(project_id)
    if p is None:
        raise HTTPException(404, "Project not found")
    # Stop containers first if running
    if p.directory.exists() and (p.directory / "docker-compose.yml").exists():
        await docker_svc.compose_down(p.directory)
    await project_svc.delete_project(project_id)
    return {"ok": True}


@router.get("/{project_id}/files")
async def list_files(project_id: str):
    """Return flat list of relative file paths in the project (excludes .git)."""
    p = await project_svc.get_project(project_id)
    if p is None:
        raise HTTPException(404, "Project not found")
    if not p.directory.exists():
        return []
    files = []
    for f in sorted(p.directory.rglob("*")):
        if f.is_file() and ".git" not in f.parts:
            files.append(str(f.relative_to(p.directory)))
    return files


@router.get("/{project_id}/files/content")
async def get_file_content(project_id: str, path: str):
    """Return the content of a specific file in the project."""
    p = await project_svc.get_project(project_id)
    if p is None:
        raise HTTPException(404, "Project not found")
    file_path = (p.directory / path).resolve()
    # Path traversal protection
    if not str(file_path).startswith(str(p.directory.resolve())):
        raise HTTPException(403, "Access denied")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File not found")
    try:
        content = file_path.read_text(errors="replace")
    except Exception:
        raise HTTPException(500, "Failed to read file")
    return PlainTextResponse(content)
