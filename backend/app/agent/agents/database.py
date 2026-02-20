"""DatabaseAgent — generates SQLAlchemy models from entity specifications.

Handles field types (str, int, float, bool, datetime, text), nullable/unique
constraints, and relationships (one_to_many, many_to_one, many_to_many,
one_to_one). Commits after each entity.

Tools used: read_file, write_file, edit_file, list_directory, run_command, git_commit
"""

from __future__ import annotations

from typing import AsyncGenerator

from app.agent.prompts.database import DATABASE_SYSTEM_PROMPT, DATABASE_TOOL_SCHEMAS
from app.agent.tools import execute_tool
from app.agent.state import AgentResult, Task
from app.agent.agents.base import BaseAgent
from app.agent.agents.events import AgentEvent
from app.agent.agents.constants import COMMIT_RESULT_PREVIEW_CHARS


class DatabaseAgent(BaseAgent):
    """Creates SQLAlchemy models based on EntitySpec from the task context.

    The task context must contain:
      - entity: dict with 'name' and 'fields' (list of FieldSpec dicts)
      - relationships: list of relationship dicts involving this entity (optional)
    """

    name = "database"
    tool_names = [
        "read_file", "write_file", "edit_file",
        "list_directory", "run_command", "git_commit",
    ]
    tool_schemas = DATABASE_TOOL_SCHEMAS
    system_prompt = DATABASE_SYSTEM_PROMPT
    max_tool_rounds = 20

    def _validate_task(self, task: Task | None) -> str | None:
        if task is None:
            return "DatabaseAgent requires a task"
        if "entity" not in task.context:
            return "DatabaseAgent requires 'entity' in task.context"
        entity = task.context["entity"]
        if "name" not in entity or "fields" not in entity:
            return "DatabaseAgent: entity must have 'name' and 'fields'"
        return None

    def _build_task_instruction(self, task: Task) -> str:
        """Convert the task context into a clear LLM instruction."""
        entity = task.context.get("entity", {})
        entity_name = entity.get("name", "Unknown")
        fields = entity.get("fields", [])
        relationships = task.context.get("relationships", [])

        lines = [
            f"Create the SQLAlchemy model for the **{entity_name}** entity.",
            "",
            "## Fields",
        ]
        for f in fields:
            parts = [f"- **{f['name']}**: type=`{f['type']}`"]
            if f.get("nullable"):
                parts.append("nullable")
            if f.get("unique"):
                parts.append("unique")
            if f.get("default") is not None:
                parts.append(f"default={f['default']}")
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
            "1. Read the existing project structure (list_directory '.').",
            "2. Read any existing model files to understand imports and Base.",
            "3. Write the model file at the appropriate path.",
            "4. Update models/__init__.py to import the new model.",
            "5. Run alembic migration if alembic.ini exists.",
            f"6. Commit with message: \"Add {entity_name} model\".",
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
                {"message": f"Add {entity_name} model"},
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
            message=f"{entity_name} model created and committed.",
        )
