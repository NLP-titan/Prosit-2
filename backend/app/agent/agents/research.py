"""
Track 2: Clarification (Research) Agent.

First agent in a new project. Receives empty or partial SharedState,
conducts structured requirement gathering, and extracts a full ProjectSpec.
Never generates code or infrastructure scaffolding.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.state import ProjectSpec, SharedState
from app.config import settings
from app.models.project import Project


# Import prompt from dedicated module
def _get_system_prompt() -> str:
    from app.agent.prompts.research import RESEARCH_SYSTEM_PROMPT
    return RESEARCH_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


class ClarificationAgent(BaseAgent):
    """Clarification Agent: requirement gathering only. Uses ask_user, check_spec_completeness, finalize_spec."""

    name = "clarification"
    model = settings.OPENROUTER_MODEL  # Minimax via OpenRouter
    system_prompt = ""  # Set in run() from prompts.research
    tool_names = ["ask_user", "check_spec_completeness", "finalize_spec"]
    max_tool_rounds = 25

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: None = None,
        user_message: str | None = None,
        shared_context: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Run the clarification loop: update spec, check completeness, ask follow-ups, then finalize on confirmation."""
        logger.info("[ClarificationAgent] run() started, building messages and calling OpenRouter...")
        self.system_prompt = _get_system_prompt()
        messages = self._build_initial_messages(state, user_message)
        async for event in self._run_react_loop(messages, project):
            yield event

    def _build_initial_messages(
        self, state: SharedState, user_message: str | None
    ) -> list[dict]:
        """Build conversation history: system, prior conversation, optional current spec, and latest user message."""
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
        ]
        # Replay stored conversation (without tool calls) so the model has context
        for turn in state.user_conversation:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
        # If we have a partial spec, add a short context line so the model can continue from it
        if state.spec is not None:
            spec_json = json.dumps(state.spec.to_dict())
            messages.append({
                "role": "user",
                "content": "[Current partial spec from previous turns]\n" + spec_json,
            })
        # Note: latest user message is already in state.user_conversation (orchestrator appends before calling run)
        return messages
