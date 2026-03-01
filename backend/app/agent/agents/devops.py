"""Track 5: DevOps Agent — validation, Docker build/up, health check, build_complete or structured error."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

from app.agent.base import AgentEvent, BaseAgent
from app.agent.prompts.devops import DEVOPS_SYSTEM_PROMPT
from app.agent.state import AgentResult, SharedState, Task
from app.agent.validation import validate_project
from app.models.project import Project
from app.services import docker as docker_svc

logger = logging.getLogger(__name__)


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
    max_tool_rounds = 30

    _INITIAL_WAIT = 5       # seconds to wait after compose up before first health check
    _RETRY_WAIT = 5         # seconds between health check retries
    _MAX_RETRIES = 5        # number of health check attempts
    _HEALTH_TIMEOUT = 15    # per-request timeout for health check

    def __init__(self) -> None:
        super().__init__()

    async def run(
        self,
        state: SharedState,
        project: Project,
        task: Task | None = None,
        user_message: str | None = None,
        shared_context: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Scripted flow: validate → build → up → health_check → build_complete or error.

        Progress is reported via tool_call_start/result events (which fold into
        the build progress card) rather than agent_message events (which would
        spam the chat with separate bubbles).
        """
        from app.agent.tools import execute_tool

        project_dir = project.directory
        self._result = AgentResult(status="success")

        # ── 1. Pre-Docker validation ────────────────────────────
        yield AgentEvent(type="tool_call_start", data={
            "tool": "validate_project", "arguments": {},
        })
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
            yield AgentEvent(type="tool_call_result", data={
                "tool": "validate_project",
                "result": f"Validation failed: {error_msg}",
            })
            return

        yield AgentEvent(type="tool_call_result", data={
            "tool": "validate_project", "result": "Validation passed",
        })

        # ── 2. Docker build ─────────────────────────────────────
        yield AgentEvent(type="tool_call_start", data={
            "tool": "docker_build", "arguments": {},
        })
        build_ok, build_output = await docker_svc.compose_build(project_dir)
        if not build_ok:
            parsed = await docker_svc.get_build_errors(project_dir, build_output)
            self._result = AgentResult(
                status="error",
                error=f"Docker build failed: {parsed[:300]}",
                state_updates={
                    "error_file_path": None,
                    "suggested_fix": parsed or "Fix Docker build errors (check Dockerfile and dependencies).",
                    "build_error": build_output[-2000:],
                    "suggested_agent": "scaffold",
                },
            )
            yield AgentEvent(type="tool_call_result", data={
                "tool": "docker_build",
                "result": f"Build failed: {parsed[:200]}",
            })
            return

        yield AgentEvent(type="tool_call_result", data={
            "tool": "docker_build", "result": "Docker images built successfully",
        })

        # ── 3. Docker compose up ────────────────────────────────
        yield AgentEvent(type="tool_call_start", data={
            "tool": "docker_compose_up", "arguments": {},
        })
        up_result = await execute_tool(project, "docker_compose_up", {})
        yield AgentEvent(type="tool_call_result", data={
            "tool": "docker_compose_up", "result": up_result[:2000],
        })
        if "SUCCESS" not in up_result and "failed" in up_result.lower():
            parsed_up = docker_svc.parse_up_output(up_result)
            self._result = AgentResult(
                status="error",
                error=f"Docker compose up failed: {parsed_up}",
                state_updates={
                    "error_file_path": None,
                    "suggested_fix": parsed_up
                    or "Check docker-compose.yml and container logs. Ensure ports are free.",
                    "build_error": up_result[-2000:],
                    "suggested_agent": "scaffold",
                },
            )
            return

        # ── 4. Health check with retries ────────────────────────
        # Give containers time to start before first health check
        await asyncio.sleep(self._INITIAL_WAIT)

        health_url = f"http://localhost:{project.app_port}/health"
        last_error = ""
        for attempt in range(self._MAX_RETRIES):
            logger.info(
                "[DevOps] Health check attempt %d/%d → %s",
                attempt + 1, self._MAX_RETRIES, health_url,
            )
            ok, body = await docker_svc.health_check(health_url, timeout=self._HEALTH_TIMEOUT)
            if ok:
                logger.info("[DevOps] Health check passed")
                break
            last_error = body
            logger.warning("[DevOps] Health check failed: %s", body[:200])
            if attempt < self._MAX_RETRIES - 1:
                await asyncio.sleep(self._RETRY_WAIT)
        else:
            # All retries exhausted — check if containers are actually running
            # before declaring failure
            yield AgentEvent(type="tool_call_start", data={
                "tool": "docker_logs", "arguments": {},
            })
            logs = await execute_tool(project, "docker_logs", {})
            yield AgentEvent(type="tool_call_result", data={
                "tool": "docker_logs", "result": logs[-1500:],
            })

            # Try /docs as a fallback — the app might be running without /health
            docs_url = f"http://localhost:{project.app_port}/docs"
            docs_ok, _ = await docker_svc.health_check(docs_url, timeout=self._HEALTH_TIMEOUT)
            if docs_ok:
                logger.info("[DevOps] /health failed but /docs responds — treating as success")
            else:
                self._result = AgentResult(
                    status="error",
                    error=f"Health check failed after {self._MAX_RETRIES} retries: {last_error[:200]}",
                    state_updates={
                        "error_file_path": None,
                        "suggested_fix": "API did not respond on /health. Check docker_logs for app startup errors.",
                        "suggested_agent": "api",
                    },
                )
                return

        # ── 5. build_complete ───────────────────────────────────
        swagger_url = project.swagger_url or f"http://localhost:{project.app_port}/docs"
        api_url = project.api_url or f"http://localhost:{project.app_port}"
        yield AgentEvent(type="tool_call_start", data={
            "tool": "build_complete",
            "arguments": {"swagger_url": swagger_url, "api_url": api_url},
        })
        await execute_tool(project, "build_complete", {
            "swagger_url": swagger_url, "api_url": api_url,
        })
        yield AgentEvent(type="tool_call_result", data={
            "tool": "build_complete", "result": "Build marked as complete.",
        })
        yield AgentEvent(type="build_complete", data={
            "swagger_url": swagger_url, "api_url": api_url,
        })
        self._result = AgentResult(status="success")
