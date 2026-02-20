"""LLM client with retry logic for Track 4 agents.

Wraps the OpenAI SDK pointed at OpenRouter. Retries transient failures
(429 rate limit, 5xx server errors, timeouts, connection errors) with
exponential backoff. Does NOT retry mid-stream — only the initial
stream creation is retried.
"""

from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI, APIStatusError, APIConnectionError, APITimeoutError
import httpx

from app.config import settings
from app.agent.agents.constants import (
    LLM_MAX_RETRIES,
    LLM_RETRY_BASE_DELAY_SECONDS,
    LLM_RETRY_MAX_DELAY_SECONDS,
    LLM_RETRYABLE_STATUS_CODES,
)

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    return _client


def _is_retryable(exc: Exception) -> bool:
    """Determine if an exception is transient and worth retrying."""
    if isinstance(exc, APITimeoutError):
        return True
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in LLM_RETRYABLE_STATUS_CODES:
        return True
    return False


async def chat_completion_stream(
    messages: list[dict], tools: list[dict] | None = None
):
    """Yield streaming chunks from OpenRouter with retry on transient failures.

    Only the initial stream creation is retried. Once chunks start flowing,
    stream errors propagate to the caller (the agent's LLM loop handles them).
    """
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

    # Retry only the stream creation (initial HTTP handshake)
    stream = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            stream = await client.chat.completions.create(**kwargs)
            break  # connected successfully
        except Exception as exc:
            if attempt < LLM_MAX_RETRIES and _is_retryable(exc):
                delay = min(
                    LLM_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                    LLM_RETRY_MAX_DELAY_SECONDS,
                )
                logger.warning(
                    "LLM stream creation attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt,
                    LLM_MAX_RETRIES,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                raise

    # Stream chunks (no retry here — partial streams handled by caller)
    async for chunk in stream:
        yield chunk
