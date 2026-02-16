from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk

from app.config import settings


class LLMClient:
    """OpenRouter LLM client using the OpenAI SDK."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            default_headers={
                "HTTP-Referer": "https://backendforge.app",
                "X-Title": "BackendForge",
            },
        )
        self.model = settings.openrouter_model

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ):
        """
        Stream a chat completion from OpenRouter.
        Yields ChatCompletionChunk objects.
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.1,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self.client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk

    async def close(self):
        await self.client.close()


llm_client = LLMClient()
