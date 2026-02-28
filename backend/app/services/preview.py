from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agent.state import EntitySpec, FieldSpec, ProjectSpec
from app.db import get_db


async def get_project_spec(project_id: str) -> Optional[ProjectSpec]:
    """Load ProjectSpec for a project from the shared_state table, if present."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT spec_json FROM shared_state WHERE project_id = ?",
            (project_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    if row is None:
        return None

    spec_json = row["spec_json"]
    if not spec_json:
        return None

    try:
        data = json.loads(spec_json)
    except Exception:
        return None

    try:
        return ProjectSpec.from_dict(data)
    except Exception:
        return None


def _friendly_field_type(field: FieldSpec) -> str:
    t = (field.type or "").lower()
    if t in ("bool", "boolean"):
        return "Yes/No"
    if t in ("int", "integer", "float", "number"):
        return "Number"
    if t in ("datetime", "timestamp"):
        return "Date/Time"
    if t in ("text", "longtext"):
        return "Long Text"
    return "Short Text"


def _entity_description(entity: EntitySpec) -> str:
    name = entity.name or "entity"
    return f"Information about {name}."


def build_database_preview(spec: ProjectSpec) -> Dict[str, List[Dict[str, Any]]]:
    """Convert ProjectSpec into a database preview DTO for the frontend."""
    models: List[Dict[str, Any]] = []
    for entity in spec.entities:
        fields: List[Dict[str, str]] = []
        for field in entity.fields:
            fields.append(
                {
                    "name": field.name,
                    "type_label": _friendly_field_type(field),
                }
            )
        models.append(
            {
                "name": entity.name,
                "description": _entity_description(entity),
                "fields": fields,
            }
        )
    return {"models": models}


def _group_name_for_entity(entity_name: str) -> str:
    base = entity_name or "Resource"
    lower = base.lower()
    if "user" in lower or "account" in lower:
        return "User Accounts"
    if "post" in lower or "blog" in lower:
        return "Blog Posts"
    if lower.endswith("y"):
        return base[:-1].capitalize() + "ies"
    if not lower.endswith("s"):
        return base.capitalize() + "s"
    return base.capitalize()


def build_capabilities_preview(spec: ProjectSpec) -> Dict[str, List[Dict[str, Any]]]:
    """Convert ProjectSpec into a capabilities preview DTO for the frontend."""
    groups: List[Dict[str, Any]] = []
    for entity in spec.entities:
        resource = entity.name or "Resource"
        group_name = _group_name_for_entity(resource)
        singular = resource.capitalize()
        plural = _group_name_for_entity(resource)
        items = [
            f"Create a new {singular}",
            f"Get a list of all {plural}",
            f"Get details for a single {singular}",
            f"Update an existing {singular}",
            f"Delete a {singular}",
        ]
        groups.append({"name": group_name, "items": items})
    return {"groups": groups}

