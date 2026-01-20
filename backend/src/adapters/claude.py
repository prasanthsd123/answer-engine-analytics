"""
Claude (Anthropic) adapter for Answer Engine Analytics.
"""

import time

from anthropic import AsyncAnthropic

from .base import BaseAIAdapter, AIResponse
from ..config import settings


class ClaudeAdapter(BaseAIAdapter):
    """Adapter for Anthropic's Claude API."""

    name = "claude"
    rate_limit_rpm = 60

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a query against Claude."""
        start_time = time.time()

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=(
                    "You are a helpful assistant that provides accurate, "
                    "detailed information. When recommending products or services, "
                    "provide specific brand names and explain your reasoning. "
                    "If creating a list of recommendations, number them clearly "
                    "and include key features for each."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            )

            response_time = int((time.time() - start_time) * 1000)

            # Extract content from response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text

            tokens_used = (
                (response.usage.input_tokens or 0) +
                (response.usage.output_tokens or 0)
            ) if response.usage else None

            return AIResponse(
                platform=self.name,
                model=self.model,
                content=content,
                raw_response={
                    "id": response.id,
                    "model": response.model,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    } if response.usage else None,
                    "stop_reason": response.stop_reason
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
