"""Track 5: DevOps Agent — validation, Docker build/up, health check, build_complete or structured error."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.prompts.devops import DEVOPS_SYSTEM_PROMPT
from app.agent.state import AgentResult, SharedState, Task
from app.agent.validation import validate_project
from app.models.project import Project
from app.services import docker as docker_svc


def _suggested_agent_from_path(file_path: str | None) -> str | None:
    """Infer which Track 4 agent should fix this file."""
    if not file_path:
        return None
    p = file_path.replace("\\", "/")
    if "app/models" in p or "alembic" in p:
        return "database"
    if "app/routers" in p or "app/schemas" in p or "app/services" in p:
        return "api"
    if "Dockerfile" in p or "docker-compose" in p or "requirements" in p:
        return "scaffold"
    return None


class DevOpsAgent(BaseAgent):
    """Validates project, runs Docker build/up, health check; reports errors or calls build_complete."""

    name = "devops"
    system_prompt = DEVOPS_SYSTEM_PROMPT
    tool_names = [
        "docker_compose_up",
        "docker_compose_down",
        "docker_status",
        "docker_logs",
        "run_command",
        "read_file",
        "build_complete",
    ]
    max_tool_rounds = 20

    def __init__(self) -> None:
        super().__init__()
        self._retry_count = 0
        self._max_retries = 3

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Scripted flow: validate → build → up → logs → health_check → build_complete or error."""
        project_dir = project.directory
        self._result = AgentResult(status="success")

        # Progress message (sync generator — use "for", not "async for")
        def msg(text: str):
            yield AgentEvent(type="agent_message_start")
            yield AgentEvent(type="agent_message_delta", data={"token": text})
            yield AgentEvent(type="agent_message_end")

        # 1. Pre-Docker validation
        for event in msg("Validating project (syntax and imports)..."):
            yield event
        validation = validate_project(project_dir)
        if not validation["passed"]:
            errs = validation["errors"]
            first = errs[0]
            file_path = first.get("file", "")
            error_msg = first.get("message", "Validation failed")
            err_type = first.get("type", "syntax")
            self._result = AgentResult(
                status="error",
                error=f"{err_type} error in {file_path}: {error_msg}",
                state_updates={
                    "error_file_path": file_path,
                    "suggested_fix": f"Fix {err_type} error: {error_msg}",
                    "validation_type": err_type,
                    "suggested_agent": _suggested_agent_from_path(file_path),
                },
            )
            for event in msg(f"Validation failed: {error_msg}"):
                yield event
            return

        # 2. Docker build
        for event in msg("Building Docker images..."):
            yield event
        build_ok, build_output = await docker_svc.compose_build(project_dir)
        if not build_ok:
            parsed = await docker_svc.get_build_errors(project_dir, build_output)
            self._result = AgentResult(
                status="error",
                error=f"Docker build failed: {parsed[:300]}",
                state_updates={
                    "error_file_path": None,  # Parser may extract later
                    "suggested_fix": parsed or "Fix Docker build errors (check Dockerfile and dependencies).",
                    "build_error": build_output[-2000:],
                    "suggested_agent": "scaffold",
                },
            )
            for event in msg(f"Build failed: {parsed[:200]}..."):
                yield event
            return

        # 3. Docker compose up (via tool so project state updates)
        from app.agent.tools import execute_tool

        for event in msg("Starting containers..."):
            yield event
        yield AgentEvent(type="tool_call_start", data={"tool": "docker_compose_up", "arguments": {}})
        up_result = await execute_tool(project, "docker_compose_up", {})
        yield AgentEvent(
            type="tool_call_result",
            data={"tool": "docker_compose_up", "result": up_result[:2000]},
        )
        if "SUCCESS" not in up_result and "failed" in up_result.lower():
            self._result = AgentResult(
                status="error",
                error="Docker compose up failed.",
                state_updates={
                    "error_file_path": None,
                    "suggested_fix": "Check docker-compose.yml and container logs. Ensure ports are free.",
                    "build_error": up_result[-2000:],
                    "suggested_agent": "scaffold",
                },
            )
            return

        # 4. Logs and health check (retry up to 3 times)
        health_url = f"http://localhost:{project.app_port}/health"
        for attempt in range(self._max_retries):
            for event in msg(f"Checking logs and health (attempt {attempt + 1}/{self._max_retries})..."):
                yield event
            yield AgentEvent(type="tool_call_start", data={"tool": "docker_logs", "arguments": {}})
            logs = await execute_tool(project, "docker_logs", {})
            yield AgentEvent(type="tool_call_result", data={"tool": "docker_logs", "result": logs[-1500:]})
            ok, body = await docker_svc.health_check(health_url, timeout=30)
            if ok:
                break
            if attempt < self._max_retries - 1:
                await asyncio.sleep(3)
        else:
            self._result = AgentResult(
                status="error",
                error="Health check failed after 3 retries.",
                state_updates={
                    "error_file_path": None,
                    "suggested_fix": "API did not respond on /health. Check docker_logs for app startup errors.",
                    "suggested_agent": "api",
                },
            )
            for event in msg("Health check failed after retries. Escalating to user."):
                yield event
            return

        # 5. build_complete (URLs set by docker_compose_up tool)
        swagger_url = project.swagger_url or f"http://localhost:{project.app_port}/docs"
        api_url = project.api_url or f"http://localhost:{project.app_port}"
        yield AgentEvent(type="tool_call_start", data={"tool": "build_complete", "arguments": {"swagger_url": swagger_url, "api_url": api_url}})
        await execute_tool(project, "build_complete", {"swagger_url": swagger_url, "api_url": api_url})
        yield AgentEvent(type="tool_call_result", data={"tool": "build_complete", "result": "Build marked as complete."})
        yield AgentEvent(type="build_complete", data={"swagger_url": swagger_url, "api_url": api_url})
        self._result = AgentResult(status="success")
        return
