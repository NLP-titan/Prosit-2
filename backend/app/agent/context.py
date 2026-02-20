from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agent.prompts import SYSTEM_PROMPT
from app.db import get_db


class ConversationContext:
    """Manages the message history for one agent session."""

    def __init__(self) -> None:
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._project_id: str | None = None

    async def _persist(self, role: str, content: str | None = None,
                       tool_calls: list[dict] | None = None,
                       tool_call_id: str | None = None) -> None:
        if self._project_id is None:
            return
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO chat_messages (project_id, role, content, tool_calls, tool_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (self._project_id, role, content,
                 json.dumps(tool_calls) if tool_calls else None,
                 tool_call_id,
                 datetime.now(timezone.utc).isoformat()),
            )
            await db.commit()
        finally:
            await db.close()

    async def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        await self._persist("user", content)

    async def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})
        await self._persist("assistant", content)

    async def add_assistant_tool_calls(self, content: str | None, tool_calls: list[dict]) -> None:
        msg: dict = {"role": "assistant", "tool_calls": tool_calls}
        if content:
            msg["content"] = content
        self.messages.append(msg)
        await self._persist("assistant", content, tool_calls=tool_calls)

    async def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": content}
        )
        await self._persist("tool", content, tool_call_id=tool_call_id)

    def get_messages(self) -> list[dict]:
        return self.messages

    async def load_from_db(self, project_id: str) -> None:
        """Restore conversation from SQLite. Called on session creation."""
        self._project_id = project_id
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT role, content, tool_calls, tool_call_id FROM chat_messages WHERE project_id = ? ORDER BY id",
                (project_id,),
            )
            rows = await cursor.fetchall()
        finally:
            await db.close()

        for row in rows:
            role = row["role"]
            content = row["content"]
            tool_calls_json = row["tool_calls"]
            tool_call_id = row["tool_call_id"]

            if role == "user":
                self.messages.append({"role": "user", "content": content})
            elif role == "assistant":
                msg: dict = {"role": "assistant"}
                if content:
                    msg["content"] = content
                if tool_calls_json:
                    msg["tool_calls"] = json.loads(tool_calls_json)
                self.messages.append(msg)
            elif role == "tool":
                self.messages.append(
                    {"role": "tool", "tool_call_id": tool_call_id, "content": content}
                )


class ScopedContext:
    """Context for a single agent's conversation.

    Unlike ConversationContext which always uses the global SYSTEM_PROMPT,
    this takes a custom system prompt and can be seeded with relevant context.
    Ephemeral — not persisted to SQLite.
    """

    def __init__(
        self, system_prompt: str, seed_messages: list[dict] | None = None
    ) -> None:
        self.messages: list[dict] = [
            {"role": "system", "content": system_prompt}
        ]
        if seed_messages:
            self.messages.extend(seed_messages)

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_assistant_tool_calls(
        self, content: str | None, tool_calls: list[dict]
    ) -> None:
        msg: dict = {"role": "assistant", "tool_calls": tool_calls}
        if content:
            msg["content"] = content
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append(
            {"role": "tool", "tool_call_id": tool_call_id, "content": result}
        )

    def get_messages(self) -> list[dict]:
        return self.messages

    def reset(self, keep_system: bool = True) -> None:
        if keep_system and self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
