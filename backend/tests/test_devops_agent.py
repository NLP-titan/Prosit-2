"""Tests for Track 5: DevOpsAgent — validation failure, structured error, and (mocked) happy path."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.agents.devops import DevOpsAgent, _suggested_agent_from_path
from app.agent.state import AgentResult, SharedState
from app.models.project import Project


def test_suggested_agent_from_path():
    assert _suggested_agent_from_path("app/models/book.py") == "database"
    assert _suggested_agent_from_path("app/routers/book.py") == "api"
    assert _suggested_agent_from_path("app/schemas/book.py") == "api"
    assert _suggested_agent_from_path("app/services/book.py") == "api"
    assert _suggested_agent_from_path("Dockerfile") == "scaffold"
    assert _suggested_agent_from_path(None) is None
    assert _suggested_agent_from_path("app/main.py") is None


def test_devops_agent_tool_names():
    agent = DevOpsAgent()
    assert agent.name == "devops"
    assert "docker_compose_up" in agent.tool_names
    assert "build_complete" in agent.tool_names
    assert "write_file" not in agent.tool_names
    assert "edit_file" not in agent.tool_names
    assert "ask_user" not in agent.tool_names


@pytest.mark.asyncio
async def test_devops_agent_validation_failure(tmp_path):
    """When a .py file has syntax error, agent returns error result with file path and suggested_fix."""
    broken = tmp_path / "app" / "models"
    broken.mkdir(parents=True)
    (broken / "book.py").write_text("def x(\n")  # syntax error
    project = Project(id="test-devops", name="test", app_port=9000, db_port=5400)
    with patch.object(Project, "directory", tmp_path):
        agent = DevOpsAgent()
        state = SharedState(project_id=project.id)
        events = []
        async for event in agent.run(state, project):
            events.append(event)
        result = await agent.get_result()
    assert result.status == "error"
    assert result.error
    assert "error_file_path" in result.state_updates
    assert "suggested_fix" in result.state_updates
    assert result.state_updates.get("validation_type") in ("syntax", "import")


@pytest.mark.asyncio
async def test_devops_agent_build_failure(tmp_path):
    """When compose_build fails, agent returns error with build_error in state_updates."""
    # No docker-compose.yml -> build will fail
    project = Project(id="test-devops-build", name="test", app_port=9001, db_port=5401)
    with patch.object(Project, "directory", tmp_path):
        agent = DevOpsAgent()
        state = SharedState(project_id=project.id)
        async for _ in agent.run(state, project):
            pass
        result = await agent.get_result()
    assert result.status == "error"
    assert "Docker build failed" in (result.error or "") or "Build" in (result.error or "")
    assert "suggested_fix" in result.state_updates or "build_error" in result.state_updates


@pytest.mark.asyncio
async def test_devops_agent_mocked_happy_path(tmp_path):
    """With valid project and mocked docker/tools, agent reaches build_complete."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('ok')\n")
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    project = Project(id="test-devops-ok", name="test", app_port=9002, db_port=5402)
    project.swagger_url = f"http://localhost:{project.app_port}/docs"
    project.api_url = f"http://localhost:{project.app_port}"

    async def fake_tool(proj, tool_name, args):
        if tool_name == "docker_compose_up":
            return "SUCCESS: Containers started and running."
        if tool_name == "docker_logs":
            return "Uvicorn running"
        if tool_name == "build_complete":
            return "Build marked as complete."
        return "ok"

    with patch.object(Project, "directory", tmp_path):
        with patch("app.agent.agents.devops.docker_svc.compose_build", AsyncMock(return_value=(True, "ok"))):
            with patch("app.agent.agents.devops.docker_svc.health_check", AsyncMock(return_value=(True, "{}"))):
                with patch("app.agent.tools.execute_tool", side_effect=fake_tool):
                    agent = DevOpsAgent()
                    state = SharedState(project_id=project.id)
                    build_complete_events = []
                    async for event in agent.run(state, project):
                        if getattr(event, "type", None) == "build_complete":
                            build_complete_events.append(event)
                    result = await agent.get_result()
    assert result.status == "success"
    assert len(build_complete_events) == 1
    assert build_complete_events[0].data.get("swagger_url")
    assert build_complete_events[0].data.get("api_url")
