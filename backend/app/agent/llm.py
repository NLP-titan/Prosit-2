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


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
):
    """Yield streaming chunks from OpenRouter.

    Args:
        model: If provided, use this model. Otherwise use settings.OPENROUTER_MODEL.
    """
    kwargs: dict = {
        "model": model or settings.OPENROUTER_MODEL,
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


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming completion for classification tasks.

    Returns the text content of the response.
    """
    client = get_client()
    response = await client.chat.completions.create(
        model=model or settings.OPENROUTER_MODEL,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""
