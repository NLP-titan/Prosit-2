from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
    return _client


async def chat_completion_stream(messages: list[dict], tools: list[dict] | None = None):
    """Yield streaming chunks from OpenRouter."""
    kwargs: dict = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.2,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    client = get_client()
    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        yield chunk
