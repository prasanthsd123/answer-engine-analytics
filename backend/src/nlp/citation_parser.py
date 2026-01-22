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
class EnhancedCitation:
    """Citation with source attribution and quality metrics."""
    url: str
    domain: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    reference_number: Optional[int] = None
    mentions_brand: bool = False
    brand_context: Optional[str] = None  # Text context where brand appears near this citation
    source_type: str = "other"  # review_site, news, blog, community, official, other
    authority_score: float = 0.5  # 0-1 based on domain reputation


@dataclass
class CitationStats:
    """Statistics about citations in a response."""
    total_citations: int
    unique_domains: int
    domains: Dict[str, int]  # domain -> count
    citations: List[Citation]


@dataclass
class EnhancedCitationStats:
    """Enhanced statistics with source attribution."""
    total_citations: int
    unique_domains: int
    domains: Dict[str, int]
    citations: List[EnhancedCitation]
    brand_attributed_count: int  # Citations that mention the brand
    source_type_breakdown: Dict[str, int]  # source_type -> count
    avg_authority_score: float


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

    def classify_source_type(self, domain: str) -> str:
        """
        Classify the type of source based on domain.

        Args:
            domain: Website domain

        Returns:
            Source type: review_site, news, blog, community, official, other
        """
        domain_lower = domain.lower()

        # Review sites - high value for brand tracking
        review_sites = {
            'g2.com', 'capterra.com', 'trustpilot.com', 'trustradius.com',
            'getapp.com', 'softwareadvice.com', 'yelp.com', 'tripadvisor.com',
            'glassdoor.com', 'gartner.com', 'forrester.com', 'cnet.com',
            'pcmag.com', 'tomsguide.com', 'techradar.com', 'wirecutter.com'
        }

        # News sites - authoritative coverage
        news_sites = {
            'techcrunch.com', 'wired.com', 'theverge.com', 'forbes.com',
            'bloomberg.com', 'reuters.com', 'wsj.com', 'nytimes.com',
            'bbc.com', 'cnn.com', 'venturebeat.com', 'zdnet.com',
            'arstechnica.com', 'engadget.com', 'mashable.com', 'businessinsider.com'
        }

        # Community/Social - user discussions
        community_sites = {
            'reddit.com', 'quora.com', 'stackoverflow.com', 'stackexchange.com',
            'twitter.com', 'x.com', 'linkedin.com', 'facebook.com', 'medium.com',
            'dev.to', 'hackernews.com', 'news.ycombinator.com'
        }

        # Check against known site types
        for site in review_sites:
            if site in domain_lower:
                return "review_site"

        for site in news_sites:
            if site in domain_lower:
                return "news"

        for site in community_sites:
            if site in domain_lower:
                return "community"

        # Check for blog patterns
        if 'blog' in domain_lower:
            return "blog"

        # Check for official documentation/government/education
        if '.gov' in domain_lower:
            return "official"
        if '.edu' in domain_lower:
            return "official"

        return "other"

    def calculate_authority_score(self, domain: str, source_type: str) -> float:
        """
        Calculate an authority score for a domain.

        Args:
            domain: Website domain
            source_type: Already classified source type

        Returns:
            Authority score from 0.0 to 1.0
        """
        domain_lower = domain.lower()

        # High authority domains with specific scores
        high_authority = {
            # Review sites
            'g2.com': 0.95,
            'capterra.com': 0.90,
            'gartner.com': 0.95,
            'forrester.com': 0.95,
            'trustpilot.com': 0.85,
            'trustradius.com': 0.85,
            # News
            'techcrunch.com': 0.90,
            'forbes.com': 0.90,
            'bloomberg.com': 0.95,
            'reuters.com': 0.95,
            'wired.com': 0.85,
            'theverge.com': 0.85,
            # Reference
            'wikipedia.org': 0.80,
        }

        # Check for exact domain match
        for auth_domain, score in high_authority.items():
            if auth_domain in domain_lower:
                return score

        # Default scores by source type
        type_scores = {
            "review_site": 0.80,
            "news": 0.75,
            "official": 0.85,
            "community": 0.50,
            "blog": 0.45,
            "other": 0.40
        }

        return type_scores.get(source_type, 0.40)

    def attribute_citations_to_mentions(
        self,
        content: str,
        citations: List[Citation],
        brand_name: str
    ) -> List[EnhancedCitation]:
        """
        Determine which citations are associated with brand mentions.

        Strategy:
        1. Find all brand mention positions in the text
        2. Find all citation reference positions ([1], [2]) in the text
        3. Associate citations with nearby brand mentions (within proximity threshold)
        4. Classify source types and calculate authority scores

        Args:
            content: Full response text
            citations: List of Citation objects
            brand_name: Brand name to search for

        Returns:
            List of EnhancedCitation objects with attribution data
        """
        enhanced = []

        if not content or not brand_name:
            # Return basic enhanced citations without attribution
            for idx, c in enumerate(citations):
                source_type = self.classify_source_type(c.domain)
                enhanced.append(EnhancedCitation(
                    url=c.url,
                    domain=c.domain,
                    title=c.title,
                    snippet=c.snippet,
                    reference_number=c.reference_number or (idx + 1),
                    mentions_brand=False,
                    source_type=source_type,
                    authority_score=self.calculate_authority_score(c.domain, source_type)
                ))
            return enhanced

        # Find brand mention positions (case-insensitive)
        brand_pattern = re.compile(re.escape(brand_name), re.IGNORECASE)
        brand_positions = [m.start() for m in brand_pattern.finditer(content)]

        # Find citation reference positions [1], [2], etc.
        ref_pattern = r'\[(\d+)\]'
        ref_positions = {}  # ref_number -> list of positions
        for match in re.finditer(ref_pattern, content):
            ref_num = int(match.group(1))
            if ref_num not in ref_positions:
                ref_positions[ref_num] = []
            ref_positions[ref_num].append(match.start())

        # Process each citation
        proximity_threshold = 300  # Characters

        for idx, c in enumerate(citations):
            ref_num = c.reference_number or (idx + 1)
            source_type = self.classify_source_type(c.domain)
            authority = self.calculate_authority_score(c.domain, source_type)

            mentions_brand = False
            brand_context = None

            # Check if this citation's reference is near a brand mention
            if ref_num in ref_positions:
                for ref_pos in ref_positions[ref_num]:
                    for brand_pos in brand_positions:
                        distance = abs(ref_pos - brand_pos)
                        if distance < proximity_threshold:
                            mentions_brand = True
                            # Extract context around both positions
                            start = max(0, min(ref_pos, brand_pos) - 75)
                            end = min(len(content), max(ref_pos, brand_pos) + 75)
                            brand_context = content[start:end].strip()
                            break
                    if mentions_brand:
                        break

            # Also check if the citation URL or title mentions the brand
            if not mentions_brand:
                if brand_name.lower() in c.url.lower():
                    mentions_brand = True
                    brand_context = f"Brand mentioned in URL: {c.url}"
                elif c.title and brand_name.lower() in c.title.lower():
                    mentions_brand = True
                    brand_context = f"Brand mentioned in title: {c.title}"

            enhanced.append(EnhancedCitation(
                url=c.url,
                domain=c.domain,
                title=c.title,
                snippet=c.snippet,
                reference_number=ref_num,
                mentions_brand=mentions_brand,
                brand_context=brand_context,
                source_type=source_type,
                authority_score=authority
            ))

        return enhanced

    def get_enhanced_citation_stats(
        self,
        content: str,
        citations: List[Citation],
        brand_name: str
    ) -> EnhancedCitationStats:
        """
        Get comprehensive citation statistics with source attribution.

        Args:
            content: Full response text
            citations: List of Citation objects
            brand_name: Brand name for attribution

        Returns:
            EnhancedCitationStats with full analysis
        """
        enhanced = self.attribute_citations_to_mentions(content, citations, brand_name)

        # Calculate domain counts
        domain_counts = {}
        for c in enhanced:
            domain_counts[c.domain] = domain_counts.get(c.domain, 0) + 1

        # Calculate source type breakdown
        type_breakdown = {}
        for c in enhanced:
            type_breakdown[c.source_type] = type_breakdown.get(c.source_type, 0) + 1

        # Calculate average authority
        avg_authority = 0.0
        if enhanced:
            avg_authority = sum(c.authority_score for c in enhanced) / len(enhanced)

        # Count brand-attributed citations
        brand_count = sum(1 for c in enhanced if c.mentions_brand)

        return EnhancedCitationStats(
            total_citations=len(enhanced),
            unique_domains=len(domain_counts),
            domains=domain_counts,
            citations=enhanced,
            brand_attributed_count=brand_count,
            source_type_breakdown=type_breakdown,
            avg_authority_score=round(avg_authority, 3)
        )
