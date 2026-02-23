"""Track 4: API Agent — creates Pydantic schemas, services, and FastAPI routers."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.prompts.api import API_SYSTEM_PROMPT
from app.agent.state import SharedState, Task
from app.models.project import Project


class APIAgent(BaseAgent):
    """Creates schemas, service layer, and router for a single entity."""

    name = "api"
    system_prompt = API_SYSTEM_PROMPT
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
    ) -> AsyncGenerator[AgentEvent, None]:
        messages = [{"role": "system", "content": self.system_prompt}]

        content = self._build_task_instruction(task, user_message)
        messages.append({"role": "user", "content": content})

        async for event in self._run_react_loop(messages, project):
            yield event

        # Track modified files from task context
        if self._result.status == "success" and task:
            entity = task.context.get("entity", "unknown").lower()
            self._result.files_modified.extend([
                f"app/schemas/{entity}.py",
                f"app/services/{entity}.py",
                f"app/routers/{entity}.py",
            ])

    @staticmethod
    def _build_task_instruction(
        task: Task | None, user_message: str | None
    ) -> str:
        """Build the LLM instruction from task context or user message."""
        if user_message:
            return user_message

        if task is None:
            return "Create API routes for the project."

        entity_name = task.context.get("entity", "Unknown")
        fields = task.context.get("fields", [])

        parts = [
            f"## Task: {task.description}\n",
            f"Create the Pydantic schemas, service layer, and FastAPI router "
            f"for the **{entity_name}** entity.\n",
        ]

        if fields:
            parts.append("### Fields\n```json\n" + json.dumps(fields, indent=2) + "\n```\n")

        parts.append(
            "### Steps\n"
            "1. List the project directory to understand the structure\n"
            f"2. Read the {entity_name} model file to understand exact column definitions\n"
            "3. Read the existing app structure (main.py, existing routers)\n"
            f"4. Create Pydantic schemas in app/schemas/{entity_name.lower()}.py\n"
            f"5. Create the service layer in app/services/{entity_name.lower()}.py\n"
            f"6. Create the FastAPI router in app/routers/{entity_name.lower()}.py\n"
            "7. Register the router in the main app file\n"
            f'8. Commit with message "Add {entity_name} API (schemas, service, router)"\n'
        )

        return "\n".join(parts)
