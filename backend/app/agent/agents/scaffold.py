"""ScaffoldAgent — creates the base project from a template.

This is the simplest implementation agent. It calls scaffold_project to render
the FastAPI+PostgreSQL template, then commits the initial scaffold to git.

Tools used: scaffold_project, git_commit
"""

from __future__ import annotations

from app.agent.state import AgentResult, Task
from app.agent.agents.base import BaseAgent
from app.agent.agents.events import AgentEvent  # re-export for backward compat
from app.agent.agents.constants import SCAFFOLD_MAX_TOOL_ROUNDS


SCAFFOLD_SYSTEM_PROMPT = """\
You are the ScaffoldAgent for BackendForge. Your ONLY job is to create the \
initial project skeleton from a template.

## Instructions
1. Call scaffold_project to create the base FastAPI+PostgreSQL project structure.
2. Call git_commit with message "Initial scaffold from template".
3. You are done. Do NOT write any business logic, models, or routes.

## Rules
- You have exactly TWO tools: scaffold_project and git_commit.
- Call scaffold_project first, then git_commit. Nothing else.
- Do NOT ask the user any questions.
- Do NOT generate any code — the template handles everything.
"""

SCAFFOLD_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "scaffold_project",
            "description": "Create the base project from the FastAPI+PostgreSQL template.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
]


class ScaffoldAgent(BaseAgent):
    """Creates the initial project scaffold from a template."""

    name = "scaffold"
    tool_names = ["scaffold_project", "git_commit"]
    tool_schemas = SCAFFOLD_TOOL_SCHEMAS
    system_prompt = SCAFFOLD_SYSTEM_PROMPT
    max_tool_rounds = SCAFFOLD_MAX_TOOL_ROUNDS

    def _build_task_instruction(self, task: Task) -> str:
        template_name = (
            task.context.get("template_name", "fastapi-postgres")
            if task
            else "fastapi-postgres"
        )
        return (
            f"Scaffold the project using the '{template_name}' template. "
            f"Then commit the initial scaffold."
        )

    def _track_tool_result(
        self, func_name: str, args: dict, files_modified: list[str]
    ) -> None:
        if func_name == "scaffold_project":
            files_modified.append("(scaffold template files)")
        elif func_name == "git_commit":
            files_modified.append("(committed)")

    def _build_success_result(
        self, task: Task | None, files_modified: list[str]
    ) -> AgentResult:
        return AgentResult(
            status="success",
            files_modified=files_modified,
            message="Project scaffolded and committed.",
        )
