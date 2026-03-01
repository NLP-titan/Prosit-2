from __future__ import annotations

import asyncio
import logging
import time

from httpx import Timeout
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
            timeout=Timeout(
                connect=10.0,
                read=float(settings.LLM_TIMEOUT),
                write=10.0,
                pool=10.0,
            ),
            max_retries=0,  # we handle retries ourselves
        )
    return _client


async def chat_completion_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str | None = None,
):
    """Yield streaming chunks from OpenRouter with retry on transient errors.

    Retries the entire request on connection/timeout errors.
    Stream-level errors (mid-response failures) are NOT retried here —
    they propagate to the caller (ReAct loop) which handles its own retry.
    """
    used_model = model or settings.OPENROUTER_MODEL
    max_retries = settings.LLM_MAX_RETRIES
    base_delay = settings.LLM_RETRY_BASE_DELAY

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

    for attempt in range(max_retries):
        try:
            logger.info(
                "[LLM] stream start  model=%s  msgs=%d  has_tools=%s  attempt=%d/%d",
                used_model, len(messages), bool(tools), attempt + 1, max_retries,
            )
            t0 = time.perf_counter()

            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                yield chunk

            elapsed = time.perf_counter() - t0
            logger.info("[LLM] stream done   model=%s  %.1fs", used_model, elapsed)
            return  # success

        except (asyncio.TimeoutError, TimeoutError) as e:
            logger.warning(
                "[LLM] Timeout on attempt %d/%d: %s", attempt + 1, max_retries, e,
            )
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info("[LLM] Retrying in %.1fs...", delay)
                await asyncio.sleep(delay)
            else:
                raise

        except Exception as e:
            err_str = str(e).lower()
            # Retry on transient/rate-limit errors
            is_transient = any(kw in err_str for kw in (
                "rate_limit", "429", "502", "503", "504",
                "connection", "timeout", "reset", "eof",
            ))
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "[LLM] Transient error on attempt %d/%d: %s. Retrying in %.1fs...",
                    attempt + 1, max_retries, e, delay,
                )
                await asyncio.sleep(delay)
            else:
                raise


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
) -> str:
    """Non-streaming completion with retry for classification tasks."""
    used_model = model or settings.OPENROUTER_MODEL
    max_retries = settings.LLM_MAX_RETRIES
    base_delay = settings.LLM_RETRY_BASE_DELAY
    client = get_client()

    for attempt in range(max_retries):
        try:
            logger.info(
                "[LLM] completion start  model=%s  msgs=%d  attempt=%d/%d",
                used_model, len(messages), attempt + 1, max_retries,
            )
            t0 = time.perf_counter()

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

        except (asyncio.TimeoutError, TimeoutError) as e:
            logger.warning(
                "[LLM] Timeout on attempt %d/%d: %s", attempt + 1, max_retries, e,
            )
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise

        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(kw in err_str for kw in (
                "rate_limit", "429", "502", "503", "504",
                "connection", "timeout", "reset", "eof",
            ))
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "[LLM] Transient error on attempt %d/%d: %s. Retrying in %.1fs...",
                    attempt + 1, max_retries, e, delay,
                )
                await asyncio.sleep(delay)
            else:
                raise

    # Should not reach here, but just in case
    return ""
