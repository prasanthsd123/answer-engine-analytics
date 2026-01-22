"""
Perplexity AI adapter for Answer Engine Analytics.
"""

import time
from typing import List

import httpx

from typing import Dict, Any
from urllib.parse import urlparse

from .base import BaseAIAdapter, AIResponse, Citation
from ..config import settings


class PerplexityAdapter(BaseAIAdapter):
    """Adapter for Perplexity AI API."""

    name = "perplexity"
    rate_limit_rpm = 20  # Perplexity has stricter rate limits

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        self.model = "llama-3.1-sonar-large-128k-online"  # Online model with citations

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a query against Perplexity AI."""
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that provides accurate, "
                        "well-researched information with citations. "
                        "When recommending products or services, include specific brand names "
                        "and cite your sources."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "return_citations": True,
            "return_images": False
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=settings.AI_REQUEST_TIMEOUT
                )
                response.raise_for_status()

            response_time = int((time.time() - start_time) * 1000)
            data = response.json()

            content = ""
            if "choices" in data and data["choices"]:
                content = data["choices"][0].get("message", {}).get("content", "")

            tokens_used = None
            if "usage" in data:
                tokens_used = data["usage"].get("total_tokens")

            return AIResponse(
                platform=self.name,
                model=self.model,
                content=content,
                raw_response=data,
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

    def extract_native_citations(self, raw_response: Dict[str, Any]) -> List[Citation]:
        """
        Extract citations from Perplexity's native response format.

        Perplexity returns a 'citations' array in the API response when
        return_citations=True is set. This method extracts those native
        citations which are more accurate than text-based URL extraction.

        Args:
            raw_response: Raw response dict from Perplexity API

        Returns:
            List of Citation objects from Perplexity's citations array
        """
        citations = []

        if not raw_response or "citations" not in raw_response:
            return citations

        for idx, url in enumerate(raw_response["citations"]):
            try:
                # Clean the URL
                url = url.strip()
                if not url:
                    continue

                parsed = urlparse(url)
                citations.append(Citation(
                    url=url,
                    domain=parsed.netloc,
                    title=f"[{idx + 1}]"  # Perplexity uses numbered references
                ))
            except Exception:
                continue

        return citations

    def extract_citations(self, content: str) -> List[Citation]:
        """
        Extract citations from Perplexity response text.

        This extracts URLs embedded in the text content. Native citations
        from the API response are handled separately by extract_native_citations().
        """
        return super().extract_citations(content)
