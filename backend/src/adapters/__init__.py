"""
AI Platform Adapters for Answer Engine Analytics.
"""

from .base import BaseAIAdapter, AIResponse, ParsedResponse, Citation, Mention
from .chatgpt import ChatGPTAdapter
from .claude import ClaudeAdapter
from .perplexity import PerplexityAdapter
from .gemini import GeminiAdapter

__all__ = [
    "BaseAIAdapter",
    "AIResponse",
    "ParsedResponse",
    "Citation",
    "Mention",
    "ChatGPTAdapter",
    "ClaudeAdapter",
    "PerplexityAdapter",
    "GeminiAdapter",
]


def get_adapter(platform: str) -> BaseAIAdapter:
    """Factory function to get the appropriate adapter for a platform."""
    adapters = {
        "chatgpt": ChatGPTAdapter,
        "claude": ClaudeAdapter,
        "perplexity": PerplexityAdapter,
        "gemini": GeminiAdapter,
    }

    if platform.lower() not in adapters:
        raise ValueError(f"Unknown platform: {platform}")

    return adapters[platform.lower()]()
