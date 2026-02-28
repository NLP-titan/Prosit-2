from __future__ import annotations

import asyncio
from pathlib import Path


async def _run(cmd: list[str], cwd: Path, timeout: float = 120) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return "", "Command timed out", 1
    return stdout.decode(), stderr.decode(), proc.returncode


async def compose_up(project_dir: Path) -> tuple[bool, str]:
    out, err, rc = await _run(
        ["docker", "compose", "up", "-d", "--build"],
        project_dir,
        timeout=300,
    )
    return rc == 0, out + err


async def compose_down(project_dir: Path) -> tuple[bool, str]:
    out, err, rc = await _run(["docker", "compose", "down", "-v"], project_dir)
    return rc == 0, out + err


async def compose_status(project_dir: Path) -> dict:
    out, err, rc = await _run(["docker", "compose", "ps", "--format", "json"], project_dir)
    if rc != 0:
        return {"running": False, "error": err}
    return {"running": True, "output": out}


async def compose_logs(project_dir: Path, service: str = "", tail: int = 50) -> str:
    cmd = ["docker", "compose", "logs", "--tail", str(tail)]
    if service:
        cmd.append(service)
    out, err, rc = await _run(cmd, project_dir)
    return out + err
