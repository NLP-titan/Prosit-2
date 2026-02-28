from __future__ import annotations

import logging
import time

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

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
    used_model = model or settings.OPENROUTER_MODEL
    logger.info(
        "[LLM] stream start  model=%s  msgs=%d  has_tools=%s",
        used_model, len(messages), bool(tools),
    )
    t0 = time.perf_counter()

    kwargs: dict = {
        "model": used_model,
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

    elapsed = time.perf_counter() - t0
    logger.info("[LLM] stream done   model=%s  %.1fs", used_model, elapsed)


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming completion for classification tasks.

    Returns the text content of the response.
    """
    used_model = model or settings.OPENROUTER_MODEL
    logger.info("[LLM] completion start  model=%s  msgs=%d", used_model, len(messages))
    t0 = time.perf_counter()

    client = get_client()
    response = await client.chat.completions.create(
        model=used_model,
        messages=messages,
        temperature=0.1,
    )
    result = response.choices[0].message.content or ""
    elapsed = time.perf_counter() - t0
    logger.info(
        "[LLM] completion done  model=%s  %.1fs  len=%d",
        used_model, elapsed, len(result),
    )
    return result
