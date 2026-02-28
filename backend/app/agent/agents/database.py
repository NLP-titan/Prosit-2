"""Track 4: Database Agent — creates SQLAlchemy models for entities."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.prompts.database import DATABASE_SYSTEM_PROMPT
from app.agent.state import SharedState, Task
from app.models.project import Project


class DatabaseAgent(BaseAgent):
    """Creates SQLAlchemy models for a single entity based on the task context."""

    name = "database"
    system_prompt = DATABASE_SYSTEM_PROMPT
    tool_names = [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "run_command",
        "git_commit",
    ]
    max_tool_rounds = 20

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
        shared_context: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages = [{"role": "system", "content": self.system_prompt}]

        if shared_context:
            messages.append({"role": "user", "content": shared_context})
            messages.append({"role": "assistant", "content":
                "I've reviewed the project structure and existing code. Ready to proceed."})

        content = self._build_task_instruction(task, user_message)
        messages.append({"role": "user", "content": content})

        async for event in self._run_react_loop(messages, project):
            yield event

        # Track modified files from task context
        if self._result.status == "success" and task:
            entity = task.context.get("entity", "unknown")
            self._result.files_modified.append(f"app/models/{entity.lower()}.py")

    @staticmethod
    def _build_task_instruction(
        task: Task | None, user_message: str | None
    ) -> str:
        """Build the LLM instruction from task context or user message."""
        if user_message:
            return user_message

        if task is None:
            return "Create database models for the project."

        entity_name = task.context.get("entity", "Unknown")
        fields = task.context.get("fields", [])
        relationships = task.context.get("relationships", [])

        parts = [
            f"## Task: {task.description}\n",
            f"Create the SQLAlchemy model for the **{entity_name}** entity.\n",
        ]

        if fields:
            parts.append("### Fields\n```json\n" + json.dumps(fields, indent=2) + "\n```\n")

        if relationships:
            parts.append(
                "### Relationships\n```json\n"
                + json.dumps(relationships, indent=2)
                + "\n```\n"
            )

        parts.append(
            "### Steps\n"
            f"1. Create the {entity_name} model file with proper columns and relationships\n"
            "2. Update models/__init__.py to import the new model (if it exists)\n"
            f'3. Commit with message "Add {entity_name} model"\n\n'
            "NOTE: The project structure and key files (database.py, main.py, models/__init__.py) "
            "have already been provided. Do NOT call list_directory or read_file for these files. "
            "Only read files if you need something not already provided.\n"
        )

        return "\n".join(parts)
