import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.core import AgentLoop
from app.database import get_session
from app.models import ChatMessage, Project

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# In-memory stream queues (single-process, Phase 1)
active_streams: dict[str, asyncio.Queue] = {}


class ChatSendRequest(BaseModel):
    message: str


@router.post("/{project_id}/send")
async def send_message(
    project_id: str,
    body: ChatSendRequest,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    queue = asyncio.Queue()
    active_streams[project_id] = queue

    # Run agent loop in background
    asyncio.create_task(_run_agent(project_id, body.message, queue))

    return {"status": "accepted"}


@router.get("/{project_id}/stream")
async def stream_response(project_id: str):
    queue = active_streams.get(project_id)
    if not queue:
        return StreamingResponse(
            iter([_sse("error", {"message": "No active stream"})]),
            media_type="text/event-stream",
        )

    async def event_generator():
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield event
                if '"message_end"' in event or '"error"' in event:
                    break
        except asyncio.TimeoutError:
            yield _sse("error", {"message": "Stream timeout"})
        finally:
            active_streams.pop(project_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id}/history")
async def get_history(
    project_id: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "tool_calls": json.loads(m.tool_calls) if m.tool_calls else None,
            "tool_call_id": m.tool_call_id,
            "tool_name": m.tool_name,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


async def _run_agent(project_id: str, message: str, queue: asyncio.Queue):
    agent = AgentLoop(project_id)
    try:
        async for event in agent.run(message):
            await queue.put(event)
    except Exception as e:
        await queue.put(_sse("error", {"message": str(e)}))
        await queue.put(_sse("message_end", {}))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
