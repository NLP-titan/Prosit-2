"""Track 5: ValidationRunner — pure Python utility for pre-Docker validation.

NOT an LLM agent. Runs syntax and import checks on .py files before Docker
build to catch obvious errors cheaply.

All checks are in-process (no subprocesses) for speed — a single ast.parse()
per file handles both syntax validation and import extraction.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


def _normalize_package_name(name: str) -> str:
    """Normalize pip package name for comparison (e.g. pydantic-settings -> pydantic_settings)."""
    return name.lower().replace("-", "_")


def _parse_requirements(requirements_path: Path) -> set[str]:
    """Parse requirements.txt and return set of top-level package names (normalized)."""
    if not requirements_path.exists():
        return set()
    names = set()
    for line in requirements_path.read_text().splitlines():
        line = line.strip().split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"^([a-zA-Z0-9_-]+)", line)
        if match:
            names.add(_normalize_package_name(match.group(1)))
    return names


def _check_file(
    file_path: Path,
    allowed_packages: set[str] | None,
) -> tuple[str | None, list[str]]:
    """Parse a single .py file. Returns (syntax_error, [import_errors]).

    A single ast.parse() call validates syntax and extracts imports.
    """
    try:
        source = file_path.read_text()
    except Exception as e:
        return f"Cannot read file: {e}", []

    # ast.parse catches the same errors as py_compile, without subprocess overhead
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        msg = f"line {e.lineno}: {e.msg}" if e.lineno else str(e.msg)
        return msg, []

    # If no requirements to check against, skip import check
    if not allowed_packages:
        return None, []

    # Extract top-level imports from the parsed AST
    import_errors: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _normalize_package_name(alias.name.split(".")[0])
                if not top.startswith("_"):
                    seen.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = _normalize_package_name(node.module.split(".")[0])
                if not top.startswith("_"):
                    seen.add(top)

    for m in sorted(seen):
        if m in _STDLIB:
            continue
        if m in allowed_packages:
            continue
        # Allow local "app" package
        if m == "app":
            continue
        # Check prefix matches (e.g. pydantic matches pydantic_settings)
        if any(m.startswith(a) or a.startswith(m) for a in allowed_packages):
            continue
        import_errors.append(m)

    return None, import_errors


# Standard library modules (common ones; we skip these for import_check)
_STDLIB = frozenset(
    {
        "abc", "aifc", "argparse", "array", "ast", "asyncio", "atexit", "base64",
        "bdb", "binascii", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
        "chunk", "cmath", "cmd", "code", "codecs", "collections", "colorsys",
        "compileall", "concurrent", "configparser", "contextlib", "contextvars",
        "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses", "dataclasses",
        "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
        "email", "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
        "fileinput", "fnmatch", "fractions", "ftplib", "functools", "gc", "getopt",
        "getpass", "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq",
        "hmac", "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib",
        "inspect", "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
        "linecache", "locale", "logging", "lzma", "mailbox", "mailcap", "marshal",
        "math", "mimetypes", "mmap", "modulefinder", "multiprocessing", "netrc",
        "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
        "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
        "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random",
        "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
        "subprocess", "sunau", "symtable", "sys", "sysconfig", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap", "threading", "time",
        "timeit", "tkinter", "token", "tokenize", "trace", "traceback", "tracemalloc",
        "tty", "turtle", "turtledemo", "types", "typing", "unicodedata", "unittest",
        "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile",
        "zipimport", "zlib", "_thread",
    }
)


def validate_project(project_dir: Path) -> dict:
    """Validate all .py files: syntax + import check in a single pass per file.

    Returns: {"passed": bool, "errors": [{"file": str, "message": str, "type": "syntax"|"import"}]}
    """
    project_dir = Path(project_dir)
    errors: list[dict] = []
    exclude_dirs = {"__pycache__", ".venv", "venv", ".git", "node_modules"}

    # Collect all .py files
    py_files: list[Path] = []
    for item in project_dir.rglob("*.py"):
        if not any(part in exclude_dirs for part in item.parts):
            py_files.append(item)

    # Parse requirements once (not per-file)
    requirements_path = project_dir / "requirements.txt"
    allowed = _parse_requirements(requirements_path) if requirements_path.exists() else None

    for fp in py_files:
        try:
            rel = fp.relative_to(project_dir)
        except ValueError:
            rel = Path(fp.name)

        syntax_err, import_errs = _check_file(fp, allowed)

        if syntax_err:
            errors.append({"file": str(rel), "message": syntax_err, "type": "syntax"})
        elif import_errs:
            errors.append({
                "file": str(rel),
                "message": f"Unresolved imports: {', '.join(import_errs)}",
                "type": "import",
            })

    return {"passed": len(errors) == 0, "errors": errors}
