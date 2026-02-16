import asyncio
from pathlib import Path

from app.agent.tool_registry import ToolRegistry
from app.config import settings


def _get_project_dir(project_id: str) -> Path:
    return Path(settings.projects_base_dir) / project_id


async def git_commit(project_id: str, message: str) -> str:
    """Stage all changes and commit with the given message."""
    project_dir = _get_project_dir(project_id)

    if not (project_dir / ".git").exists():
        return "Error: Not a git repository"

    try:
        # Stage all changes
        proc = await asyncio.create_subprocess_exec(
            "git", "add", "-A",
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        # Check if there are changes to commit
        proc = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()

        if not stdout.strip():
            return "No changes to commit"

        # Commit
        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", message,
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return f"Error: git commit failed: {stderr.decode()}"

        return f"Committed: {message}\n{stdout.decode().strip()}"

    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"


def register_git_tools(registry: ToolRegistry) -> None:
    """Register git tools with the registry."""
    registry.register(
        name="git_commit",
        description="Stage all current changes and create a git commit with the given message. Use after completing a logical unit of work.",
        parameters={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The commit message describing what was done",
                },
            },
            "required": ["message"],
        },
        handler=git_commit,
    )
