import os
from pathlib import Path

from app.agent.tool_registry import ToolRegistry
from app.config import settings


def _get_project_dir(project_id: str) -> Path:
    return Path(settings.projects_base_dir) / project_id


def _validate_path(project_id: str, relative_path: str) -> Path:
    """Resolve and validate that a path stays within the project directory."""
    project_dir = _get_project_dir(project_id)
    full_path = (project_dir / relative_path).resolve()
    if not str(full_path).startswith(str(project_dir.resolve())):
        raise PermissionError(f"Access denied: path escapes project directory")
    return full_path


async def read_file(project_id: str, path: str) -> str:
    """Read a file from the project."""
    file_path = _validate_path(project_id, path)
    if not file_path.exists():
        return f"Error: File not found: {path}"
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > 50000:
            return content[:50000] + f"\n... (truncated, {len(content)} chars total)"
        return content
    except UnicodeDecodeError:
        return f"Error: Binary file cannot be read: {path}"


async def write_file(project_id: str, path: str, content: str) -> str:
    """Write or create a file in the project."""
    file_path = _validate_path(project_id, path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Size limit: 1MB
    if len(content.encode("utf-8")) > 1_000_000:
        return "Error: File content exceeds 1MB limit"

    file_path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} chars to {path}"


async def edit_file(
    project_id: str, path: str, old_text: str, new_text: str
) -> str:
    """Replace old_text with new_text in a file."""
    file_path = _validate_path(project_id, path)
    if not file_path.exists():
        return f"Error: File not found: {path}"

    content = file_path.read_text(encoding="utf-8")
    if old_text not in content:
        return f"Error: old_text not found in {path}. The file may have changed."

    count = content.count(old_text)
    new_content = content.replace(old_text, new_text, 1)
    file_path.write_text(new_content, encoding="utf-8")

    return f"Successfully replaced text in {path} ({count} occurrence(s) found, replaced first)"


def register_file_tools(registry: ToolRegistry) -> None:
    """Register all file tools with the registry."""
    registry.register(
        name="read_file",
        description="Read the contents of a file in the project. Path is relative to the project root.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file (e.g., 'app/models.py')",
                },
            },
            "required": ["path"],
        },
        handler=read_file,
    )

    registry.register(
        name="write_file",
        description="Create or overwrite a file in the project. Creates parent directories automatically. Path is relative to the project root.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path for the file (e.g., 'app/models.py')",
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        handler=write_file,
    )

    registry.register(
        name="edit_file",
        description="Replace a specific text substring in a file. Use this for surgical edits instead of rewriting the entire file.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to find and replace",
                },
                "new_text": {
                    "type": "string",
                    "description": "The text to replace it with",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
        handler=edit_file,
    )
