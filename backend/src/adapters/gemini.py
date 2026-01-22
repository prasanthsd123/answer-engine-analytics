"""
Google Gemini adapter for Answer Engine Analytics.
"""

import time

import google.generativeai as genai

from typing import Dict, Any, List
from urllib.parse import urlparse

from .base import BaseAIAdapter, AIResponse, Citation
from ..config import settings


class GeminiAdapter(BaseAIAdapter):
    """Adapter for Google's Gemini API."""

    name = "gemini"
    rate_limit_rpm = 60

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        self.model_name = "gemini-1.5-pro"
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=(
                "You are a helpful assistant that provides accurate, "
                "detailed information. When recommending products or services, "
                "provide specific brand names, explain your reasoning, and include "
                "relevant sources where possible. If creating a list of recommendations, "
                "number them clearly."
            )
        )

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a query against Google Gemini."""
        start_time = time.time()

        try:
            # Note: google-generativeai uses synchronous API
            # For async, we'd need to run in executor or use different approach
            response = self.model.generate_content(
                query,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )

            response_time = int((time.time() - start_time) * 1000)

            content = ""
            if response.text:
                content = response.text

            # Extract token usage if available
            tokens_used = None
            raw_response = {
                "model": self.model_name,
            }

            if hasattr(response, 'usage_metadata'):
                raw_response["usage"] = {
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "candidates_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                }
                tokens_used = (
                    raw_response["usage"]["prompt_tokens"] +
                    raw_response["usage"]["candidates_tokens"]
                )

            return AIResponse(
                platform=self.name,
                model=self.model_name,
                content=content,
                raw_response=raw_response,
                tokens_used=tokens_used,
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return AIResponse(
                platform=self.name,
                model=self.model_name,
                content="",
                raw_response={"error": str(e)},
                response_time_ms=response_time
            )


class GeminiGroundedAdapter(BaseAIAdapter):
    """
    Adapter for Google Gemini with grounding (search).
    Uses Google Search grounding for more accurate, cited responses.
    """

    name = "gemini_grounded"
    rate_limit_rpm = 30

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        self.model_name = "gemini-1.5-pro"

        # Configure with Google Search grounding
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=(
                "You are a helpful assistant with access to current information. "
                "Always cite your sources and include relevant URLs when available. "
                "For product recommendations, include official websites and key features."
            ),
            tools=[genai.protos.Tool(
                google_search_retrieval=genai.protos.GoogleSearchRetrieval()
            )]
        )

    async def execute_query(self, query: str) -> AIResponse:
        """Execute a grounded query against Google Gemini."""
        start_time = time.time()

        try:
            response = self.model.generate_content(
                query,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )

            response_time = int((time.time() - start_time) * 1000)

            content = ""
            if response.text:
                content = response.text

            raw_response = {
                "model": self.model_name,
                "grounded": True
            }

            # Extract grounding metadata if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata'):
                    grounding = candidate.grounding_metadata
                    raw_response["grounding_chunks"] = []
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks:
                            if hasattr(chunk, 'web'):
                                raw_response["grounding_chunks"].append({
                                    "uri": chunk.web.uri,
                                    "title": chunk.web.title
                                })

            tokens_used = None
            if hasattr(response, 'usage_metadata'):
                tokens_used = (
                    getattr(response.usage_metadata, 'prompt_token_count', 0) +
                    getattr(response.usage_metadata, 'candidates_token_count', 0)
                )

            return AIResponse(
                platform=self.name,
                model=self.model_name,
                content=content,
                raw_response=raw_response,
                tokens_used=tokens_used,
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            return AIResponse(
                platform=self.name,
                model=self.model_name,
                content="",
                raw_response={"error": str(e)},
                response_time_ms=response_time
            )

    def extract_native_citations(self, raw_response: Dict[str, Any]) -> List[Citation]:
        """
        Extract citations from Gemini's grounding chunks.

        When using Google Search grounding, Gemini returns grounding_chunks
        containing URIs and titles of sources used to generate the response.

        Args:
            raw_response: Raw response dict from Gemini API

        Returns:
            List of Citation objects from grounding chunks
        """
        citations = []

        if not raw_response or "grounding_chunks" not in raw_response:
            return citations

        for chunk in raw_response["grounding_chunks"]:
            try:
                uri = chunk.get("uri", "")
                if not uri:
                    continue

                parsed = urlparse(uri)
                citations.append(Citation(
                    url=uri,
                    domain=parsed.netloc,
                    title=chunk.get("title")
                ))
            except Exception:
                continue

        return citations
