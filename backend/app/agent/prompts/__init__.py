# Re-export so "from app.agent.prompts import TOOL_SCHEMAS, SYSTEM_PROMPT" still works.
from app.agent.prompts._legacy import SYSTEM_PROMPT, TOOL_SCHEMAS  # noqa: I001

__all__ = ["SYSTEM_PROMPT", "TOOL_SCHEMAS"]
