from app.agent.tool_registry import ToolRegistry


class AskUserInterrupt(Exception):
    """Raised when the agent needs to ask the user a question.

    The agent loop catches this, sends the question to the frontend,
    and pauses execution until the user responds.
    """

    def __init__(self, question: str, tool_call_id: str, options: list[dict] | None = None):
        self.question = question
        self.tool_call_id = tool_call_id
        self.options = options
        super().__init__(question)


async def ask_user(
    project_id: str,
    question: str,
    options: list[dict] | None = None,
    _tool_call_id: str = "",
) -> str:
    """Ask the user a clarifying question. This raises an interrupt."""
    raise AskUserInterrupt(question=question, tool_call_id=_tool_call_id, options=options)


def register_user_tools(registry: ToolRegistry) -> None:
    """Register user interaction tools with the registry."""
    registry.register(
        name="ask_user",
        description=(
            "Ask the user a clarifying question with selectable options. "
            "ALWAYS provide options as a list of choices the user can pick from. "
            "Each option has a label and description. Set multi_select to true "
            "if the user can pick multiple options. The user can also type a custom answer."
        ),
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user",
                },
                "options": {
                    "type": "array",
                    "description": "List of options the user can choose from. Always provide at least 2 options.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short label for the option (e.g., 'PostgreSQL', 'Yes, include auth')",
                            },
                            "description": {
                                "type": "string",
                                "description": "Brief explanation of what this option means",
                            },
                            "multi_select": {
                                "type": "boolean",
                                "description": "If true, user can select this alongside other options. Default false.",
                            },
                        },
                        "required": ["label"],
                    },
                },
            },
            "required": ["question", "options"],
        },
        handler=ask_user,
    )
