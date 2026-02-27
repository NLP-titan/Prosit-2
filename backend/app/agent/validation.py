"""Track 5: ValidationRunner — pure Python utility for pre-Docker validation.

NOT an LLM agent. Runs syntax_check and optional import_check on .py files
before Docker build to catch obvious errors cheaply.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path


def syntax_check(file_path: Path) -> tuple[bool, str | None]:
    """Run python -m py_compile on file_path. Return (pass, None) or (fail, error_message)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=file_path.parent,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)
    if result.returncode == 0:
        return True, None
    return False, (result.stderr or result.stdout or "Unknown syntax error").strip()


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
        # Handle package==version, package[extra], package
        match = re.match(r"^([a-zA-Z0-9_-]+)", line)
        if match:
            names.add(_normalize_package_name(match.group(1)))
    return names


def _get_imports_from_file(file_path: Path) -> list[str]:
    """Parse Python file and return list of top-level module names imported."""
    try:
        text = file_path.read_text()
    except Exception:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if not top.startswith("_"):
                    modules.append(_normalize_package_name(top))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if not top.startswith("_"):
                    modules.append(_normalize_package_name(top))
    return modules


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


def import_check(file_path: Path, requirements_path: Path) -> tuple[bool, str | None]:
    """Verify file's imports resolve against requirements.txt. Return (pass, None) or (fail, message)."""
    allowed = _parse_requirements(requirements_path)
    if not allowed:
        return True, None  # No requirements.txt -> skip import check
    modules = _get_imports_from_file(file_path)
    if not modules:
        return True, None
    unresolved = []
    for m in set(modules):
        if m in _STDLIB:
            continue
        if m in allowed:
            continue
        # Allow submodules of allowed (e.g. fastapi -> fastapi.openapi)
        if any(_normalize_package_name(p) in allowed for p in (m.split("_")[0], m)):
            continue
        # Check if any requirement starts with this (e.g. pydantic matches pydantic)
        if any(m.startswith(a) or a.startswith(m) for a in allowed):
            continue
        unresolved.append(m)
    if not unresolved:
        return True, None
    return False, f"Unresolved imports: {', '.join(sorted(unresolved))}"


def validate_project(project_dir: Path) -> dict:
    """Run syntax_check on all .py files; optionally import_check if requirements.txt exists.

    Returns: {"passed": bool, "errors": [{"file": str, "message": str, "type": "syntax"|"import"}]}
    """
    project_dir = Path(project_dir)
    errors: list[dict] = []
    exclude_dirs = {"__pycache__", ".venv", "venv", ".git", "node_modules"}

    def collect_py(path: Path) -> list[Path]:
        out = []
        try:
            for item in path.iterdir():
                if item.name in exclude_dirs:
                    continue
                if item.is_dir():
                    out.extend(collect_py(item))
                elif item.suffix == ".py":
                    out.append(item)
        except OSError:
            pass
        return out

    py_files = collect_py(project_dir)
    requirements_path = project_dir / "requirements.txt"

    for fp in py_files:
        try:
            rel = fp.relative_to(project_dir)
        except ValueError:
            rel = Path(fp.name)
        ok, err = syntax_check(fp)
        if not ok:
            errors.append({"file": str(rel), "message": err or "Syntax error", "type": "syntax"})
            continue
        if requirements_path.exists():
            ok, err = import_check(fp, requirements_path)
            if not ok:
                errors.append({"file": str(rel), "message": err or "Import error", "type": "import"})

    return {"passed": len(errors) == 0, "errors": errors}
