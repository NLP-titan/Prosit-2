from __future__ import annotations

import json
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.prompts.planning import PLANNING_SYSTEM_PROMPT
from app.agent.state import SharedState, Task
from app.models.project import Project


class PlanningAgent(BaseAgent):
    """Converts a ProjectSpec into a TaskManifest.

    Operates in two modes:
    - Full planning: receives a ProjectSpec, produces a complete TaskManifest
    - Delta planning: receives an existing manifest + a change description,
      produces only new tasks to append
    """

    name = "planning"
    system_prompt = PLANNING_SYSTEM_PROMPT
    tool_names = ["read_file", "list_directory", "submit_plan"]
    max_tool_rounds = 10

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages = [{"role": "system", "content": self.system_prompt}]

        if state.spec is None:
            self._result.status = "error"
            self._result.error = "No ProjectSpec available for planning"
            yield AgentEvent(
                type="error",
                data={"message": "No ProjectSpec available for planning"},
            )
            return

        spec_json = json.dumps(state.spec.to_dict(), indent=2)

        if user_message and state.manifest:
            existing_manifest = json.dumps(state.manifest.to_dict(), indent=2)
            content = (
                f"## Existing TaskManifest\n"
                f"```json\n{existing_manifest}\n```\n\n"
                f"## Project Spec\n"
                f"```json\n{spec_json}\n```\n\n"
                f"## New Requirement\n"
                f"{user_message}\n\n"
                f"Produce ONLY the new tasks to append to the existing manifest. "
                f"Do NOT repeat existing tasks. Continue task IDs from where the "
                f"existing manifest left off."
            )
        else:
            content = (
                f"## Project Spec\n"
                f"```json\n{spec_json}\n```\n\n"
                f"Produce a complete TaskManifest for this project."
            )

        messages.append({"role": "user", "content": content})

        async for event in self._run_react_loop(messages, project):
            yield event
