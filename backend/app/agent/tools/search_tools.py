import fnmatch
import os
from pathlib import Path

from app.agent.tool_registry import ToolRegistry
from app.config import settings


def _get_project_dir(project_id: str) -> Path:
    return Path(settings.projects_base_dir) / project_id


async def list_directory(project_id: str, path: str = ".") -> str:
    """List the contents of a directory as a tree."""
    project_dir = _get_project_dir(project_id)
    target = (project_dir / path).resolve()

    if not str(target).startswith(str(project_dir.resolve())):
        return "Error: Access denied"
    if not target.exists():
        return f"Error: Directory not found: {path}"
    if not target.is_dir():
        return f"Error: Not a directory: {path}"

    lines = []
    _build_tree(target, project_dir, lines, prefix="", max_depth=4, current_depth=0)
    if not lines:
        return "(empty directory)"
    return "\n".join(lines)


def _build_tree(
    current: Path,
    root: Path,
    lines: list[str],
    prefix: str,
    max_depth: int,
    current_depth: int,
) -> None:
    if current_depth > max_depth:
        lines.append(f"{prefix}... (depth limit)")
        return

    try:
        entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name))
    except PermissionError:
        return

    # Filter out noise
    entries = [
        e
        for e in entries
        if e.name not in ("__pycache__", ".git", "node_modules", ".ruff_cache")
    ]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "│   "
            _build_tree(
                entry, root, lines, prefix + extension, max_depth, current_depth + 1
            )
        else:
            size = entry.stat().st_size
            lines.append(f"{prefix}{connector}{entry.name} ({size}B)")


async def search_codebase(
    project_id: str, pattern: str, file_glob: str = "*.py"
) -> str:
    """Search for a text pattern across project files."""
    project_dir = _get_project_dir(project_id)
    if not project_dir.exists():
        return "Error: Project directory not found"

    results = []
    count = 0
    max_results = 50

    for root, dirs, files in os.walk(project_dir):
        # Skip noise directories
        dirs[:] = [
            d
            for d in dirs
            if d not in ("__pycache__", ".git", "node_modules", ".ruff_cache", "venv")
        ]

        for filename in files:
            if not fnmatch.fnmatch(filename, file_glob):
                continue

            file_path = Path(root) / filename
            rel_path = file_path.relative_to(project_dir)

            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                if pattern.lower() in line.lower():
                    results.append(f"{rel_path}:{line_num}: {line.strip()}")
                    count += 1
                    if count >= max_results:
                        results.append(
                            f"... (stopped at {max_results} results)"
                        )
                        return "\n".join(results)

    if not results:
        return f"No matches found for '{pattern}' in {file_glob} files"
    return "\n".join(results)


def register_search_tools(registry: ToolRegistry) -> None:
    """Register search tools with the registry."""
    registry.register(
        name="list_directory",
        description="List the contents of a directory in the project as a tree structure. Shows files with sizes.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the directory (default: '.' for project root)",
                    "default": ".",
                },
            },
            "required": [],
        },
        handler=list_directory,
    )

    registry.register(
        name="search_codebase",
        description="Search for a text pattern across all project files. Returns matching lines with file paths and line numbers.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The text pattern to search for (case-insensitive)",
                },
                "file_glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (default: '*.py')",
                    "default": "*.py",
                },
            },
            "required": ["pattern"],
        },
        handler=search_codebase,
    )
