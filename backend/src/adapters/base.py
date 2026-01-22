"""
Base adapter class for AI platform integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
from urllib.parse import urlparse


@dataclass
class Citation:
    """Represents a citation/source from an AI response."""
    url: str
    domain: str
    title: Optional[str] = None
    snippet: Optional[str] = None


@dataclass
class Mention:
    """Represents a brand mention in an AI response."""
    text: str
    context: str
    position: Optional[int] = None  # Position in list if applicable
    sentiment: Optional[str] = None


@dataclass
class AIResponse:
    """Raw response from an AI platform."""
    platform: str
    model: str
    content: str
    raw_response: Dict[str, Any]
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ParsedResponse:
    """Parsed and structured AI response."""
    platform: str
    content: str
    citations: List[Citation] = field(default_factory=list)
    mentions: List[Mention] = field(default_factory=list)
    is_list_response: bool = False
    list_items: List[str] = field(default_factory=list)


class BaseAIAdapter(ABC):
    """Abstract base class for AI platform adapters."""

    name: str = "base"
    rate_limit_rpm: int = 60  # Requests per minute

    @abstractmethod
    async def execute_query(self, query: str) -> AIResponse:
        """
        Execute a query against the AI platform.

        Args:
            query: The question/prompt to send

        Returns:
            AIResponse with the raw response data
        """
        pass

    def parse_response(self, response: AIResponse) -> ParsedResponse:
        """
        Parse raw response into structured format.

        Args:
            response: Raw AI response

        Returns:
            ParsedResponse with extracted data
        """
        content = response.content

        # Extract citations from text content
        text_citations = self.extract_citations(content)

        # Extract platform-specific native citations (Perplexity, Gemini, etc.)
        native_citations = self.extract_native_citations(response.raw_response)

        # Extract markdown links with titles [text](url)
        md_citations = self._extract_markdown_links(content)

        # Merge all citations, preferring entries with more metadata
        all_citations = self._merge_citations(text_citations, native_citations, md_citations)

        # Check if response is a list
        is_list, items = self._detect_list_response(content)

        return ParsedResponse(
            platform=response.platform,
            content=content,
            citations=all_citations,
            is_list_response=is_list,
            list_items=items
        )

    def extract_native_citations(self, raw_response: Dict[str, Any]) -> List[Citation]:
        """
        Extract citations from platform-specific response format.
        Override in subclasses for platforms that return native citations.

        Args:
            raw_response: Raw response dict from the API

        Returns:
            List of Citation objects from native format
        """
        return []

    def _extract_markdown_links(self, content: str) -> List[Citation]:
        """
        Extract markdown links [title](url) with titles preserved.

        Args:
            content: Response text

        Returns:
            List of Citation objects with titles from markdown
        """
        pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        citations = []
        seen_urls = set()

        for match in re.finditer(pattern, content):
            title, url = match.groups()
            url = url.rstrip('.,;:')

            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                parsed = urlparse(url)
                citations.append(Citation(
                    url=url,
                    domain=parsed.netloc,
                    title=title.strip()
                ))
            except Exception:
                continue

        return citations

    def _merge_citations(self, *citation_lists: List[Citation]) -> List[Citation]:
        """
        Merge multiple citation lists, preferring entries with more metadata.

        Args:
            citation_lists: Variable number of citation lists to merge

        Returns:
            Merged list with duplicates removed, keeping best metadata
        """
        seen = {}

        for citations in citation_lists:
            for c in citations:
                if c.url not in seen:
                    seen[c.url] = c
                else:
                    # Prefer citation with title
                    existing = seen[c.url]
                    if c.title and not existing.title:
                        seen[c.url] = c
                    # Prefer citation with snippet
                    elif c.snippet and not existing.snippet:
                        seen[c.url] = Citation(
                            url=existing.url,
                            domain=existing.domain,
                            title=existing.title or c.title,
                            snippet=c.snippet
                        )

        return list(seen.values())

    def extract_citations(self, content: str) -> List[Citation]:
        """
        Extract citations/URLs from response content.

        Args:
            content: Response text

        Returns:
            List of Citation objects
        """
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\])(\']+'
        urls = re.findall(url_pattern, content)

        citations = []
        seen_urls = set()

        for url in urls:
            # Clean up URL
            url = url.rstrip('.,;:')

            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                citations.append(Citation(url=url, domain=domain))
            except Exception:
                continue

        return citations

    def extract_brand_mentions(
        self,
        content: str,
        brand_name: str,
        competitors: Optional[List[str]] = None
    ) -> List[Mention]:
        """
        Extract brand mentions from response content.

        Args:
            content: Response text
            brand_name: Primary brand to search for
            competitors: Optional list of competitor names

        Returns:
            List of Mention objects
        """
        mentions = []

        # Search for brand name (case-insensitive)
        pattern = re.compile(re.escape(brand_name), re.IGNORECASE)
        for match in pattern.finditer(content):
            # Get context around the mention (100 chars before and after)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]

            mentions.append(Mention(
                text=match.group(),
                context=context
            ))

        return mentions

    def _detect_list_response(self, content: str) -> tuple[bool, List[str]]:
        """
        Detect if response is a numbered/bulleted list.

        Args:
            content: Response text

        Returns:
            Tuple of (is_list, list_items)
        """
        # Pattern for numbered lists (1. item, 2. item, etc.)
        numbered_pattern = r'^\s*(\d+)\.\s+(.+)$'

        # Pattern for bullet lists (- item, * item, • item)
        bullet_pattern = r'^\s*[-*•]\s+(.+)$'

        lines = content.split('\n')
        numbered_items = []
        bullet_items = []

        for line in lines:
            num_match = re.match(numbered_pattern, line, re.MULTILINE)
            if num_match:
                numbered_items.append(num_match.group(2).strip())

            bullet_match = re.match(bullet_pattern, line, re.MULTILINE)
            if bullet_match:
                bullet_items.append(bullet_match.group(1).strip())

        # Use numbered list if present, otherwise bullet list
        if len(numbered_items) >= 3:
            return True, numbered_items
        elif len(bullet_items) >= 3:
            return True, bullet_items

        return False, []

    def find_brand_position(
        self,
        list_items: List[str],
        brand_name: str
    ) -> Optional[int]:
        """
        Find the position of a brand in a list of recommendations.

        Args:
            list_items: List of items from the response
            brand_name: Brand name to search for

        Returns:
            1-based position or None if not found
        """
        pattern = re.compile(re.escape(brand_name), re.IGNORECASE)

        for idx, item in enumerate(list_items, start=1):
            if pattern.search(item):
                return idx

        return None
