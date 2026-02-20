"""AgentEvent — the single canonical event type for Track 4 agents.

Previously duplicated in scaffold.py, database.py, api.py, and core.py.
All agent files now import from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentEvent:
    """Events yielded by agent loops to the WebSocket/orchestration layer.

    Known types:
        agent_message_start  — LLM started producing text
        agent_message_delta  — streaming text token: data={"token": str}
        agent_message_end    — LLM finished text for this turn
        tool_call_start      — about to execute: data={"tool": str, "arguments": dict}
        tool_call_result     — execution done: data={"tool": str, "result": str}
        agent_result         — final result: data=AgentResult.__dict__
        error                — non-fatal error: data={"message": str}
    """

    type: str
    data: dict = field(default_factory=dict)
