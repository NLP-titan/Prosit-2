import asyncio
from pathlib import Path

from app.agent.tool_registry import ToolRegistry
from app.config import settings

# Commands that are allowed to run with shell=True
ALLOWED_SHELL_PREFIXES = [
    "pip",
    "python",
    "alembic",
    "docker",
    "git",
    "pytest",
    "ruff",
    "black",
    "mypy",
    "ls",
    "cat",
    "echo",
    "mkdir",
    "cp",
    "mv",
    "touch",
]


def _get_project_dir(project_id: str) -> Path:
    return Path(settings.projects_base_dir) / project_id


def _is_command_allowed(command: str) -> bool:
    """Check if a command is in the allowlist."""
    cmd_stripped = command.strip()
    return any(cmd_stripped.startswith(prefix) for prefix in ALLOWED_SHELL_PREFIXES)


async def run_command(
    project_id: str, command: str, working_dir: str = "."
) -> str:
    """Run a shell command in the project directory."""
    project_dir = _get_project_dir(project_id)
    cwd = (project_dir / working_dir).resolve()

    # Validate cwd stays within project
    if not str(cwd).startswith(str(project_dir.resolve())):
        return "Error: working_dir must be within the project directory"

    if not cwd.exists():
        return f"Error: Directory not found: {working_dir}"

    # Basic command safety check
    if not _is_command_allowed(command):
        return (
            f"Error: Command not allowed. Allowed prefixes: {', '.join(ALLOWED_SHELL_PREFIXES)}"
        )

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        output = ""
        if stdout:
            output += stdout.decode(errors="replace")
        if stderr:
            output += "\n[stderr]\n" + stderr.decode(errors="replace")

        # Truncate long output
        if len(output) > 5000:
            output = output[:5000] + f"\n... (truncated, {len(output)} chars total)"

        if proc.returncode != 0:
            output = f"[exit code: {proc.returncode}]\n{output}"

        return output.strip() or "(no output)"

    except asyncio.TimeoutError:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error running command: {type(e).__name__}: {str(e)}"


def register_command_tools(registry: ToolRegistry) -> None:
    """Register command tools with the registry."""
    registry.register(
        name="run_command",
        description=(
            "Run a shell command in the project directory. "
            "Use for: pip install, alembic commands, pytest, docker compose, git operations. "
            "Commands must start with an allowed prefix. Timeout: 30 seconds."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Subdirectory to run in (relative to project root, default: '.')",
                    "default": ".",
                },
            },
            "required": ["command"],
        },
        handler=run_command,
    )
