"""Track 4: Scaffold Agent — creates the base project structure from a template."""

from __future__ import annotations

from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.state import SharedState, Task
from app.models.project import Project


SCAFFOLD_SYSTEM_PROMPT = """\
You are the Scaffold Agent for BackendForge. Your ONLY job is to create the base project \
structure from a template.

## Instructions

1. Call `scaffold_project` to create the base FastAPI + PostgreSQL project from the template.
2. After scaffolding succeeds, call `git_commit` with message "Initial scaffold from template".
3. You are done.

## Rules

- Call `scaffold_project` first with no arguments.
- Then commit the generated files.
- Do NOT modify any generated files.
- Do NOT create models, schemas, or routes — other agents handle that.
- Do NOT call any other tools.
"""


class ScaffoldAgent(BaseAgent):
    """Creates the base project from the FastAPI + PostgreSQL template."""

    name = "scaffold"
    system_prompt = SCAFFOLD_SYSTEM_PROMPT
    tool_names = ["scaffold_project", "git_commit"]
    max_tool_rounds = 10

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
        shared_context: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages = [{"role": "system", "content": self.system_prompt}]

        content = "Scaffold the base project from the FastAPI + PostgreSQL template."
        if task and task.context:
            template = task.context.get("template_name", "fastapi-postgres")
            content += f" Use the '{template}' template."

        messages.append({"role": "user", "content": content})

        async for event in self._run_react_loop(messages, project):
            yield event

        # Mark files modified for orchestrator tracking
        if self._result.status == "success":
            self._result.files_modified = ["(scaffold)"]
