"""
Citation parsing service for extracting sources from AI responses.
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from urllib.parse import urlparse
import re


@dataclass
class Citation:
    """Parsed citation from AI response."""
    url: str
    domain: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    reference_number: Optional[int] = None


@dataclass
class CitationStats:
    """Statistics about citations in a response."""
    total_citations: int
    unique_domains: int
    domains: Dict[str, int]  # domain -> count
    citations: List[Citation]


class CitationParser:
    """
    Parser for extracting and analyzing citations from AI responses.

    Handles various citation formats:
    - Direct URLs
    - Markdown links [text](url)
    - Numbered references [1], [2]
    - Footnote-style citations
    """

    def __init__(self):
        # Common URL shorteners and redirectors to expand
        self.shorteners = {'bit.ly', 't.co', 'goo.gl', 'tinyurl.com', 'ow.ly'}

        # Domains to exclude (not actual citations)
        self.excluded_domains = {
            'example.com', 'localhost', 'placeholder.com',
            '127.0.0.1', 'test.com'
        }

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract all URLs from text.

        Args:
            text: Text to parse

        Returns:
            List of URL strings
        """
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\])(\']+'

        urls = re.findall(url_pattern, text)

        # Clean up URLs
        cleaned = []
        for url in urls:
            # Remove trailing punctuation
            url = url.rstrip('.,;:!?)')

            # Validate URL
            try:
                parsed = urlparse(url)
                if parsed.netloc and parsed.netloc not in self.excluded_domains:
                    cleaned.append(url)
            except Exception:
                continue

        return list(set(cleaned))  # Remove duplicates

    def extract_markdown_links(self, text: str) -> List[Citation]:
        """
        Extract Markdown-style links [text](url).

        Args:
            text: Text to parse

        Returns:
            List of Citation objects with titles
        """
        # Markdown link pattern
        pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'

        citations = []
        for match in re.finditer(pattern, text):
            title = match.group(1)
            url = match.group(2)

            try:
                parsed = urlparse(url)
                if parsed.netloc and parsed.netloc not in self.excluded_domains:
                    citations.append(Citation(
                        url=url,
                        domain=parsed.netloc,
                        title=title
                    ))
            except Exception:
                continue

        return citations

    def extract_numbered_references(self, text: str) -> Dict[int, str]:
        """
        Extract numbered references like [1] from text.

        Args:
            text: Text to parse

        Returns:
            Dict mapping reference number to context
        """
        pattern = r'\[(\d+)\]'
        references = {}

        for match in re.finditer(pattern, text):
            ref_num = int(match.group(1))
            # Get context around reference
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]
            references[ref_num] = context

        return references

    def parse_all_citations(self, text: str) -> CitationStats:
        """
        Parse all citations from text and return statistics.

        Args:
            text: Text to parse

        Returns:
            CitationStats with all citation information
        """
        citations = []
        seen_urls = set()

        # Extract markdown links first (they have titles)
        md_citations = self.extract_markdown_links(text)
        for c in md_citations:
            if c.url not in seen_urls:
                citations.append(c)
                seen_urls.add(c.url)

        # Extract plain URLs
        urls = self.extract_urls(text)
        for url in urls:
            if url not in seen_urls:
                try:
                    parsed = urlparse(url)
                    citations.append(Citation(
                        url=url,
                        domain=parsed.netloc
                    ))
                    seen_urls.add(url)
                except Exception:
                    continue

        # Count domains
        domain_counts = {}
        for c in citations:
            domain_counts[c.domain] = domain_counts.get(c.domain, 0) + 1

        return CitationStats(
            total_citations=len(citations),
            unique_domains=len(domain_counts),
            domains=domain_counts,
            citations=citations
        )

    def find_brand_citations(
        self,
        citations: List[Citation],
        brand_domain: Optional[str] = None,
        brand_name: Optional[str] = None
    ) -> List[Citation]:
        """
        Find citations that reference the brand.

        Args:
            citations: List of citations to search
            brand_domain: Brand's website domain
            brand_name: Brand name to search in URLs

        Returns:
            Citations that reference the brand
        """
        brand_citations = []

        for citation in citations:
            # Check if citation is from brand's domain
            if brand_domain and brand_domain.lower() in citation.domain.lower():
                brand_citations.append(citation)
                continue

            # Check if brand name is in URL or title
            if brand_name:
                brand_lower = brand_name.lower()
                if brand_lower in citation.url.lower():
                    brand_citations.append(citation)
                elif citation.title and brand_lower in citation.title.lower():
                    brand_citations.append(citation)

        return brand_citations

    def rank_citation_sources(
        self,
        citations: List[Citation]
    ) -> List[Dict[str, any]]:
        """
        Rank citation sources by frequency.

        Args:
            citations: List of citations

        Returns:
            List of dicts with domain and count, sorted by count
        """
        domain_counts = {}
        for c in citations:
            domain_counts[c.domain] = domain_counts.get(c.domain, 0) + 1

        ranked = [
            {"domain": domain, "count": count}
            for domain, count in domain_counts.items()
        ]

        return sorted(ranked, key=lambda x: x["count"], reverse=True)

    def extract_perplexity_citations(self, response_data: Dict) -> List[Citation]:
        """
        Extract citations from Perplexity API response format.

        Args:
            response_data: Raw Perplexity response

        Returns:
            List of citations
        """
        citations = []

        # Perplexity returns citations in response
        if "citations" in response_data:
            for idx, url in enumerate(response_data["citations"]):
                try:
                    parsed = urlparse(url)
                    citations.append(Citation(
                        url=url,
                        domain=parsed.netloc,
                        reference_number=idx + 1
                    ))
                except Exception:
                    continue

        return citations
