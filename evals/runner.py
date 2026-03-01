"""WebSocket conversation driver — sends prompts, collects events, handles ask_user."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx
import websockets

from evals.config import (
    API_BASE,
    BUILD_TIMEOUT,
    WS_BASE,
    WS_MESSAGE_TIMEOUT,
)
from evals.scenarios import Scenario

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Raw output from running a single scenario."""

    scenario_id: str
    project_id: str | None = None
    app_port: int | None = None

    # Outcome
    completed: bool = False           # did we get build_complete?
    error: str | None = None          # first fatal error, if any
    swagger_url: str | None = None
    api_url: str | None = None

    # Timing
    start_time: float = 0.0
    end_time: float = 0.0

    # Events log
    events: list[dict] = field(default_factory=list)

    # Counters
    tool_calls: int = 0
    agent_messages: int = 0
    ask_user_count: int = 0

    @property
    def build_time(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


async def _create_project(name: str, description: str) -> dict:
    """POST /projects → returns project dict."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await client.post(
            "/projects",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json()


async def _delete_project(project_id: str) -> None:
    """DELETE /projects/{id} — best-effort cleanup."""
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            await client.delete(f"/projects/{project_id}")
    except Exception:
        pass


async def _stop_project(project_id: str) -> None:
    """POST /projects/{id}/stop — best-effort cleanup."""
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
            await client.post(f"/projects/{project_id}/stop")
    except Exception:
        pass


async def run_scenario(
    scenario: Scenario,
    *,
    cleanup: bool = True,
) -> RunResult:
    """Drive a full conversation for one scenario.

    1. Create project via REST
    2. Connect WebSocket
    3. Send the scenario prompt
    4. Collect events until build_complete or timeout
    5. Handle ask_user automatically
    6. Optionally clean up (stop + delete project)
    """
    result = RunResult(scenario_id=scenario.id)
    ask_answers = list(scenario.ask_user_answers)  # copy so we can pop
    ask_answer_idx = 0

    # ── 1. Create project ──────────────────────────────────────
    try:
        project = await _create_project(
            name=f"eval_{scenario.id}",
            description=f"Eval scenario: {scenario.name}",
        )
        result.project_id = project["id"]
        result.app_port = project.get("app_port", 0)
        logger.info("[%s] Created project %s (port %s)", scenario.id, result.project_id, result.app_port)
    except Exception as e:
        result.error = f"Failed to create project: {e}"
        logger.error("[%s] %s", scenario.id, result.error)
        return result

    # ── 2. Connect WebSocket ───────────────────────────────────
    ws_url = f"{WS_BASE}/ws/chat/{result.project_id}"
    result.start_time = time.time()

    try:
        async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
            # ── 3. Send prompt ─────────────────────────────────
            await ws.send(json.dumps({"message": scenario.prompt}))
            logger.info("[%s] Sent prompt (%d chars)", scenario.id, len(scenario.prompt))

            # ── 4. Collect events ──────────────────────────────
            deadline = time.time() + BUILD_TIMEOUT

            while time.time() < deadline:
                remaining = deadline - time.time()
                timeout = min(remaining, WS_MESSAGE_TIMEOUT)

                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning("[%s] Timed out waiting for message", scenario.id)
                    result.error = f"Timed out after {BUILD_TIMEOUT}s"
                    break

                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")
                result.events.append(event)

                # Count metrics
                if event_type == "tool_call_start":
                    result.tool_calls += 1
                elif event_type == "agent_message_start":
                    result.agent_messages += 1

                # ── build_complete → success ───────────────────
                if event_type == "build_complete":
                    result.completed = True
                    result.swagger_url = event.get("swagger_url")
                    result.api_url = event.get("api_url")
                    result.end_time = time.time()
                    logger.info(
                        "[%s] Build complete in %.1fs (swagger: %s)",
                        scenario.id, result.build_time, result.swagger_url,
                    )
                    break

                # ── ask_user → auto-respond ────────────────────
                if event_type == "ask_user":
                    result.ask_user_count += 1
                    question = event.get("question", "")
                    options = event.get("options", [])
                    logger.info("[%s] ask_user: %s (options: %s)", scenario.id, question[:80], options)

                    # Use pre-defined answer or pick first option or say "yes"
                    if ask_answer_idx < len(ask_answers):
                        answer = ask_answers[ask_answer_idx]
                        ask_answer_idx += 1
                    elif options:
                        answer = options[0]
                    else:
                        answer = "yes"

                    logger.info("[%s] Responding: %s", scenario.id, answer)
                    await ws.send(json.dumps({"message": answer}))

                # ── error → record but keep going ──────────────
                if event_type == "error":
                    err_msg = event.get("message", "unknown error")
                    logger.warning("[%s] Error event: %s", scenario.id, err_msg[:200])
                    if not result.error:
                        result.error = err_msg

                # ── stopped → agent gave up ────────────────────
                if event_type == "stopped":
                    if not result.error:
                        result.error = "Agent stopped unexpectedly"
                    break

            else:
                # Loop ended without break → timeout
                if not result.error:
                    result.error = f"Build did not complete within {BUILD_TIMEOUT}s"

    except websockets.exceptions.ConnectionClosed as e:
        result.error = f"WebSocket closed: {e}"
        logger.error("[%s] %s", scenario.id, result.error)
    except Exception as e:
        result.error = f"WebSocket error: {e}"
        logger.error("[%s] %s", scenario.id, result.error)

    if not result.end_time:
        result.end_time = time.time()

    # ── 5. Cleanup ─────────────────────────────────────────────
    if cleanup and result.project_id:
        await _stop_project(result.project_id)
        await _delete_project(result.project_id)
        logger.info("[%s] Cleaned up project %s", scenario.id, result.project_id)

    return result
