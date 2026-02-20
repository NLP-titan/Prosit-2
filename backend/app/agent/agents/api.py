"""APIAgent — generates Pydantic schemas, service layer, and FastAPI routers.

Creates full CRUD for each entity: list (with pagination), get by id, create,
update, delete. Reads existing model files to understand the schema before
writing. Updates main.py to include new routers. Commits after each entity.

Tools used: read_file, write_file, edit_file, list_directory, run_command, git_commit
"""

from __future__ import annotations

from typing import AsyncGenerator

from app.agent.prompts.api import API_SYSTEM_PROMPT, API_TOOL_SCHEMAS
from app.agent.tools import execute_tool
from app.agent.state import AgentResult, Task
from app.agent.agents.base import BaseAgent
from app.agent.agents.events import AgentEvent
from app.agent.agents.constants import COMMIT_RESULT_PREVIEW_CHARS


class APIAgent(BaseAgent):
    """Creates Pydantic schemas, service functions, and FastAPI routers.

    The task context must contain:
      - entity: dict with 'name' and 'fields' (list of FieldSpec dicts)
      - relationships: list of relationship dicts involving this entity (optional)
    """

    name = "api"
    tool_names = [
        "read_file", "write_file", "edit_file",
        "list_directory", "run_command", "git_commit",
    ]
    tool_schemas = API_TOOL_SCHEMAS
    system_prompt = API_SYSTEM_PROMPT
    max_tool_rounds = 20

    def _validate_task(self, task: Task | None) -> str | None:
        if task is None:
            return "APIAgent requires a task"
        if "entity" not in task.context:
            return "APIAgent requires 'entity' in task.context"
        return None

    def _build_task_instruction(self, task: Task) -> str:
        """Convert the task context into a clear LLM instruction."""
        entity = task.context.get("entity", {})
        entity_name = entity.get("name", "Unknown")
        fields = entity.get("fields", [])
        relationships = task.context.get("relationships", [])

        lines = [
            f"Create the Pydantic schemas, service layer, and FastAPI router "
            f"for the **{entity_name}** entity.",
            "",
            "## Entity Fields",
        ]
        for f in fields:
            parts = [f"- **{f['name']}**: type=`{f['type']}`"]
            if f.get("nullable"):
                parts.append("nullable")
            if f.get("unique"):
                parts.append("unique")
            lines.append(", ".join(parts))

        if relationships:
            lines.append("")
            lines.append("## Relationships")
            for rel in relationships:
                lines.append(
                    f"- {rel['entity_a']} → {rel['entity_b']} "
                    f"(type: {rel['type']})"
                )

        lines.extend([
            "",
            "## Steps",
            "1. Read the project structure (list_directory '.').",
            f"2. Read the {entity_name} model file to understand columns and types.",
            f"3. Create `app/schemas/{entity_name.lower()}.py` with Create, Update, Response schemas.",
            f"4. Create `app/services/{entity_name.lower()}.py` with CRUD service functions.",
            f"5. Create `app/routers/{entity_name.lower()}.py` with full CRUD router.",
            "6. Update `app/main.py` to import and include the new router.",
            "7. Create __init__.py files in schemas/, services/, routers/ if missing.",
            f"8. Commit with message: \"Add {entity_name} CRUD (schemas, services, router)\".",
        ])

        return "\n".join(lines)

    def _track_tool_result(
        self, func_name: str, args: dict, files_modified: list[str]
    ) -> None:
        if func_name in ("write_file", "edit_file"):
            files_modified.append(args.get("path", ""))

    async def _post_loop_hook(
        self, task: Task | None, files_modified: list[str]
    ) -> AsyncGenerator[AgentEvent, None]:
        """Safety commit if LLM forgot to commit."""
        if not files_modified or task is None:
            return
        entity_name = task.context.get("entity", {}).get("name", "entity")
        try:
            commit_result = await execute_tool(
                self.project,
                "git_commit",
                {"message": f"Add {entity_name} CRUD (schemas, services, router)"},
            )
            if "nothing to commit" not in commit_result.lower():
                yield AgentEvent(
                    type="tool_call_result",
                    data={
                        "tool": "git_commit",
                        "result": commit_result[:COMMIT_RESULT_PREVIEW_CHARS],
                    },
                )
        except Exception:
            pass  # best-effort safety commit

    def _build_success_result(
        self, task: Task | None, files_modified: list[str]
    ) -> AgentResult:
        entity_name = (
            task.context.get("entity", {}).get("name", "entity")
            if task
            else "entity"
        )
        return AgentResult(
            status="success",
            files_modified=files_modified,
            message=f"{entity_name} CRUD (schemas, services, router) created and committed.",
        )
