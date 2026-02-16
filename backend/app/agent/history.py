import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import ChatMessage


class HistoryManager:
    """Manages conversation history for a project, persisted in SQLite."""

    async def append(self, project_id: str, message: dict) -> None:
        """Append a message to the conversation history."""
        async with async_session() as session:
            chat_msg = ChatMessage(
                project_id=project_id,
                role=message.get("role", ""),
                content=message.get("content"),
                tool_calls=(
                    json.dumps(message["tool_calls"])
                    if message.get("tool_calls")
                    else None
                ),
                tool_call_id=message.get("tool_call_id"),
                tool_name=message.get("name"),
            )
            session.add(chat_msg)
            await session.commit()

    async def get_messages(self, project_id: str) -> list[dict]:
        """Get all messages for a project in OpenAI format."""
        async with async_session() as session:
            result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.project_id == project_id)
                .order_by(ChatMessage.created_at)
            )
            messages = result.scalars().all()

        openai_messages = []
        for msg in messages:
            entry = {"role": msg.role}

            if msg.role == "assistant":
                if msg.content:
                    entry["content"] = msg.content
                if msg.tool_calls:
                    entry["tool_calls"] = json.loads(msg.tool_calls)
                    if not msg.content:
                        entry["content"] = None
            elif msg.role == "tool":
                entry["content"] = msg.content or ""
                entry["tool_call_id"] = msg.tool_call_id
            else:
                entry["content"] = msg.content or ""

            openai_messages.append(entry)

        return openai_messages

    async def get_pending_ask_user(self, project_id: str) -> dict | None:
        """Check if there's a pending ask_user tool call awaiting a response."""
        async with async_session() as session:
            # Find the last assistant message with tool_calls
            result = await session.execute(
                select(ChatMessage)
                .where(
                    ChatMessage.project_id == project_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.tool_calls.isnot(None),
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            last_assistant = result.scalar_one_or_none()

            if not last_assistant or not last_assistant.tool_calls:
                return None

            tool_calls = json.loads(last_assistant.tool_calls)

            # Check if the last tool call was ask_user
            for tc in tool_calls:
                func = tc.get("function", {})
                if func.get("name") == "ask_user":
                    # Check if there's already a tool response for this
                    tc_id = tc.get("id")
                    response_result = await session.execute(
                        select(ChatMessage).where(
                            ChatMessage.project_id == project_id,
                            ChatMessage.role == "tool",
                            ChatMessage.tool_call_id == tc_id,
                        )
                    )
                    if not response_result.scalar_one_or_none():
                        return {
                            "tool_call_id": tc_id,
                            "question": json.loads(func.get("arguments", "{}")).get(
                                "question", ""
                            ),
                        }

        return None
