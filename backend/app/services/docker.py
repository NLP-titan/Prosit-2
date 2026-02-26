from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx


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


async def compose_build(project_dir: Path, timeout: float = 300) -> tuple[bool, str]:
    """Build images only (docker compose build). Returns (success, combined_output)."""
    out, err, rc = await _run(
        ["docker", "compose", "build"],
        project_dir,
        timeout=timeout,
    )
    combined = out + err
    return rc == 0, combined


async def health_check(url: str, timeout: float = 30) -> tuple[bool, str]:
    """HTTP GET to url (e.g. /health). Returns (True, response_text) on 200, (False, error_message) otherwise."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout)
            if resp.status_code == 200:
                return True, resp.text
            return False, f"HTTP {resp.status_code}: {resp.text[:500]}"
    except Exception as e:
        return False, str(e)


def _parse_build_output(output: str) -> str:
    """Extract a short error summary from docker compose build output."""
    if not output:
        return "Build failed (no output)."
    lines = output.splitlines()
    # Prefer Python traceback: File "...", line N, then error type (e.g. SyntaxError: ...)
    file_line_re = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)')
    for i, line in enumerate(lines):
        m = file_line_re.search(line)
        if m:
            path, num = m.group(1), m.group(2)
            short_path = path.split("/")[-1] if "/" in path else path
            # Include the next line (code snippet) and any following line that looks like an error
            parts = [f"{short_path}, line {num}"]
            if i + 1 < len(lines):
                parts.append(lines[i + 1].strip())
            for j in range(i + 2, min(i + 4, len(lines))):
                if lines[j].strip() and ("Error" in lines[j] or "error" in lines[j].lower()):
                    parts.append(lines[j].strip())
                    break
            return ": ".join(parts) if len(parts) > 1 else f"{short_path}:{num}"
    # Look for ERROR or Error line
    for line in reversed(lines):
        line = line.strip()
        if line and ("error" in line.lower() or "Error" in line):
            return line[-500:] if len(line) > 500 else line
    # Last non-empty line
    for line in reversed(lines):
        line = line.strip()
        if line:
            return line[-500:] if len(line) > 500 else line
    return "Build failed (see logs)."


async def get_build_errors(project_dir: Path, build_output: str | None = None) -> str:
    """Parse build output to extract the main error. If build_output is None, run docker compose build first."""
    if build_output is None:
        ok, output = await compose_build(project_dir)
        if ok:
            return ""
        build_output = output
    return _parse_build_output(build_output)
