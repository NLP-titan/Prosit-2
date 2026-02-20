from __future__ import annotations

import asyncio
import json
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.orchestrator import OrchestratorSession
from app.services import project as project_svc
from app.services import git as git_svc
from app.db import get_db

router = APIRouter(tags=["chat"])

# Active agent sessions keyed by project_id
_sessions: dict[str, OrchestratorSession] = {}


async def _get_or_create_session(project_id: str) -> OrchestratorSession | None:
    if project_id in _sessions:
        return _sessions[project_id]
    project = await project_svc.get_project(project_id)
    if project is None:
        return None
    session = OrchestratorSession(project)
    await session.restore_state()
    _sessions[project_id] = session
    return session


async def _send(ws: WebSocket, msg_type: str, data: dict | None = None):
    await ws.send_text(json.dumps({"type": msg_type, **(data or {})}))


@router.websocket("/ws/chat/{project_id}")
async def chat_ws(ws: WebSocket, project_id: str):
    await ws.accept()

    session = await _get_or_create_session(project_id)
    if session is None:
        await _send(ws, "error", {"message": "Project not found"})
        await ws.close()
        return

    agent_task: asyncio.Task | None = None

    async def run_agent(user_message: str):
        try:
            last_state = session.project.state
            async for event in session.handle_user_message(user_message):
                await _send(ws, event.type, event.data)

                # After tool calls that modify files, send file tree and git updates
                if event.type == "tool_call_result":
                    tool = event.data.get("tool")
                    if tool in ("write_file", "edit_file", "scaffold_project", "git_commit"):
                        await _send_sidebar_updates(ws, session)

                    # Send project state update if state changed
                    if session.project.state != last_state:
                        last_state = session.project.state
                        await _send(ws, "state_update", {
                            "state": session.project.state.value,
                            "swagger_url": session.project.swagger_url,
                            "api_url": session.project.api_url,
                        })

                # Handle ask_user event — pause and wait for user response
                if event.type == "ask_user":
                    return  # The agent loop is paused, waiting for answer

        except asyncio.CancelledError:
            await _send(ws, "stopped", {"message": "Agent stopped by user"})
        except Exception:
            await _send(ws, "error", {"message": traceback.format_exc()[-1000:]})

    try:
        while True:
            raw = await ws.receive_text()
            payload = json.loads(raw)

            # Handle stop request
            if payload.get("type") == "stop":
                session.cancel()
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                await _send(ws, "stopped", {"message": "Agent stopped by user"})
                continue

            user_message = payload.get("message", "")
            if not user_message:
                continue

            # Cancel any existing run before starting a new one
            if agent_task and not agent_task.done():
                session.cancel()
                agent_task.cancel()

            agent_task = asyncio.create_task(run_agent(user_message))

    except WebSocketDisconnect:
        if agent_task and not agent_task.done():
            session.cancel()
            agent_task.cancel()


async def _send_sidebar_updates(ws: WebSocket, session: OrchestratorSession):
    """Send file tree and git log updates to the frontend."""
    project_dir = session.project.directory
    if not project_dir.exists():
        return

    # File tree
    files = []
    for f in sorted(project_dir.rglob("*")):
        if f.is_file() and ".git" not in f.parts:
            files.append(str(f.relative_to(project_dir)))
    await _send(ws, "file_tree_update", {"files": files})

    # Git log
    if (project_dir / ".git").exists():
        log = await git_svc.git_log(project_dir)
        await _send(ws, "git_update", {"commits": log})


@router.get("/projects/{project_id}/chat/history")
async def get_chat_history(project_id: str):
    """Return chat messages formatted for frontend display."""
    project = await project_svc.get_project(project_id)
    if project is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT role, content, tool_calls, tool_call_id FROM chat_messages WHERE project_id = ? ORDER BY id",
            (project_id,),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    messages = []
    for row in rows:
        role = row["role"]
        content = row["content"]
        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content or ""})
        # tool roles are internal, skip for frontend display
    return messages
