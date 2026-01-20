"""
ChatGPT (OpenAI) adapter for Answer Engine Analytics.
"""

import time
from typing import Optional

from openai import AsyncOpenAI

from .base import BaseAIAdapter, AIResponse
from ..config import settings


class ChatGPTAdapter(BaseAIAdapter):
    """Adapter for OpenAI's ChatGPT API."""

    name = "chatgpt"
    rate_limit_rpm = 60

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # or gpt-4-turbo for web browsing

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a query against ChatGPT."""
        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that provides accurate, "
                            "up-to-date information. When recommending products or services, "
                            "provide specific brand names and include sources where possible. "
                            "If you're creating a list of recommendations, number them clearly."
                        )
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            response_time = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            return AIResponse(
                platform=self.name,
                model=self.model,
                content=content,
                raw_response={
                    "id": response.id,
                    "model": response.model,
                    "usage": response.usage.model_dump() if response.usage else None,
                    "finish_reason": response.choices[0].finish_reason
                },
                tokens_used=tokens_used,
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return AIResponse(
                platform=self.name,
                model=self.model,
                content="",
                raw_response={"error": str(e)},
                response_time_ms=response_time
            )


class ChatGPTWebAdapter(BaseAIAdapter):
    """
    Adapter for ChatGPT with web browsing enabled.
    Note: This requires GPT-4 with browsing or using the Assistants API.
    """

    name = "chatgpt_web"
    rate_limit_rpm = 20  # Lower rate limit for web browsing

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-turbo"

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a query with web browsing context."""
        start_time = time.time()

        # Add instruction to search/cite sources
        enhanced_query = f"""
        {query}

        Please include relevant sources and citations in your response.
        If this is a product/service recommendation, include specific brand names
        and their official websites.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a knowledgeable assistant with access to current information. "
                            "Always cite your sources and include URLs when available. "
                            "For product recommendations, include official websites."
                        )
                    },
                    {
                        "role": "user",
                        "content": enhanced_query
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            response_time = int((time.time() - start_time) * 1000)

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            return AIResponse(
                platform=self.name,
                model=self.model,
                content=content,
                raw_response={
                    "id": response.id,
                    "model": response.model,
                    "usage": response.usage.model_dump() if response.usage else None,
                },
                tokens_used=tokens_used,
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return AIResponse(
                platform=self.name,
                model=self.model,
                content="",
                raw_response={"error": str(e)},
                response_time_ms=response_time
            )
