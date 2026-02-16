import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from app.config import settings

router = APIRouter(prefix="/api/v1/files", tags=["files"])


@router.get("/{project_id}/tree")
async def get_file_tree(project_id: str):
    project_dir = Path(settings.projects_base_dir) / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    return _build_tree(project_dir, project_dir)


@router.get("/{project_id}/content")
async def get_file_content(project_id: str, path: str = Query(...)):
    project_dir = Path(settings.projects_base_dir) / project_id
    file_path = (project_dir / path).resolve()

    # Path traversal protection
    if not str(file_path).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Binary file, cannot display")

    return {"path": path, "content": content}


def _build_tree(root: Path, current: Path) -> dict:
    """Build a JSON tree of the directory structure."""
    name = current.name or root.name
    node = {"name": name, "type": "directory", "children": []}

    try:
        entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name))
    except PermissionError:
        return node

    for entry in entries:
        # Skip hidden files and common noise
        if entry.name.startswith(".") and entry.name not in (".env",):
            continue
        if entry.name in ("__pycache__", "node_modules", ".git"):
            continue

        if entry.is_dir():
            node["children"].append(_build_tree(root, entry))
        else:
            rel_path = str(entry.relative_to(root))
            node["children"].append(
                {
                    "name": entry.name,
                    "type": "file",
                    "path": rel_path,
                    "size": entry.stat().st_size,
                }
            )

    return node
