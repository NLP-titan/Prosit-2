from __future__ import annotations

import asyncio
from pathlib import Path


async def _run(cmd: list[str], cwd: Path) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode


async def git_init(project_dir: Path) -> str:
    out, err, rc = await _run(["git", "init"], project_dir)
    if rc != 0:
        raise RuntimeError(f"git init failed: {err}")
    # Configure user for this repo so commits work in containers
    await _run(["git", "config", "user.email", "backendforge@local"], project_dir)
    await _run(["git", "config", "user.name", "BackendForge"], project_dir)
    return out.strip()


async def git_commit(project_dir: Path, message: str) -> str:
    await _run(["git", "add", "-A"], project_dir)
    out, err, rc = await _run(["git", "commit", "-m", message, "--allow-empty"], project_dir)
    if rc != 0:
        raise RuntimeError(f"git commit failed: {err}")
    # Extract commit hash
    hash_out, _, _ = await _run(["git", "rev-parse", "--short", "HEAD"], project_dir)
    return hash_out.strip()


async def git_log(project_dir: Path, max_count: int = 20) -> list[dict[str, str]]:
    out, _, rc = await _run(
        ["git", "log", f"--max-count={max_count}", "--pretty=format:%h|%s"],
        project_dir,
    )
    if rc != 0:
        return []
    entries = []
    for line in out.strip().splitlines():
        if "|" in line:
            hash_, msg = line.split("|", 1)
            entries.append({"hash": hash_, "message": msg})
    return entries


async def git_reset(project_dir: Path, commit_hash: str) -> str:
    out, err, rc = await _run(["git", "reset", "--hard", commit_hash], project_dir)
    if rc != 0:
        raise RuntimeError(f"git reset failed: {err}")
    return out.strip()
