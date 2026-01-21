"""
Perplexity Researcher Service - Deep market research using Perplexity AI.

This service queries Perplexity to gather comprehensive market intelligence:
- Market position and competitors
- Customer reviews from G2, Capterra, TrustPilot
- Feature and pricing comparisons
- Customer pain points and use cases
- Industry trends
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..adapters.perplexity import PerplexityAdapter
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class MarketResearch:
    """Results from Perplexity market research."""
    brand_name: str
    industry: str

    # Market position
    market_landscape: str = ""
    market_position: str = ""  # leader, challenger, niche, emerging

    # Competitors discovered
    competitors: List[Dict[str, str]] = field(default_factory=list)
    competitor_comparison: Dict[str, Any] = field(default_factory=dict)

    # Customer insights
    customer_reviews_summary: str = ""
    customer_sentiment: str = ""  # positive, mixed, negative
    customer_pain_points: List[str] = field(default_factory=list)

    # Product/pricing analysis
    pricing_analysis: Dict[str, Any] = field(default_factory=dict)
    key_features: List[str] = field(default_factory=list)

    # Industry trends
    industry_trends: List[str] = field(default_factory=list)

    # Research metadata
    citations: List[str] = field(default_factory=list)
    queries_made: int = 0
    quality_score: float = 0.0


class PerplexityResearcher:
    """
    Uses Perplexity AI for comprehensive market research.

    Perplexity provides real-time web search and returns results with citations,
    making it ideal for gathering up-to-date market intelligence.
    """

    # Research queries to execute (5 balanced queries per plan)
    RESEARCH_QUERIES = [
        # Query 1: Market Position & Competitors
        "market_position",
        # Query 2: Customer Reviews & Sentiment
        "customer_reviews",
        # Query 3: Competitive Feature Analysis
        "competitive_analysis",
        # Query 4: Customer Pain Points & Use Cases
        "pain_points",
        # Query 5: Industry Trends
        "industry_trends",
    ]

    def __init__(self):
        self.adapter = PerplexityAdapter()

    async def research_market(
        self,
        brand_name: str,
        industry: str,
        domain: Optional[str] = None,
        website_data: Optional[Dict[str, Any]] = None,
        known_competitors: Optional[List[str]] = None
    ) -> MarketResearch:
        """
        Conduct comprehensive market research using Perplexity.

        Args:
            brand_name: Name of the brand to research
            industry: Industry/category the brand operates in
            domain: Website domain (optional)
            website_data: Data already scraped from website (optional)
            known_competitors: List of known competitors (optional)

        Returns:
            MarketResearch object with comprehensive findings
        """
        logger.info(f"Starting Perplexity research for {brand_name} in {industry}")

        research = MarketResearch(
            brand_name=brand_name,
            industry=industry
        )

        all_citations = []

        # Execute each research query
        for query_type in self.RESEARCH_QUERIES:
            try:
                query = self._build_query(
                    query_type, brand_name, industry, domain,
                    known_competitors, website_data  # Pass scraped website data!
                )
                logger.info(f"Executing Perplexity query: {query_type}")

                response = await self.adapter.execute_query(query)
                research.queries_made += 1

                if response.content:
                    # Parse the response based on query type
                    self._parse_response(query_type, response, research)

                    # Extract citations
                    if response.raw_response and "citations" in response.raw_response:
                        all_citations.extend(response.raw_response["citations"])

            except Exception as e:
                logger.error(f"Error in Perplexity query {query_type}: {e}")
                continue

        # Deduplicate citations
        research.citations = list(set(all_citations))

        # Calculate quality score
        research.quality_score = self._calculate_quality_score(research)

        logger.info(f"Perplexity research complete: {research.queries_made} queries, "
                   f"{len(research.citations)} citations, quality: {research.quality_score:.2f}")

        return research

    def _build_query(
        self,
        query_type: str,
        brand_name: str,
        industry: str,
        domain: Optional[str],
        known_competitors: Optional[List[str]],
        website_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a specific research query with website context."""

        competitors_str = ", ".join(known_competitors[:3]) if known_competitors else ""

        # Build website context from scraped data
        website_context = ""
        if website_data:
            context_parts = []

            # Basic info
            if website_data.get("tagline"):
                context_parts.append(f"Tagline: {website_data['tagline']}")
            if website_data.get("description"):
                context_parts.append(f"Description: {website_data['description'][:300]}")
            if website_data.get("value_proposition"):
                context_parts.append(f"Value Proposition: {website_data['value_proposition'][:200]}")

            # Products
            if website_data.get("products"):
                products = website_data["products"][:5]
                if products:
                    if isinstance(products[0], dict):
                        product_names = [p.get("name", str(p)) for p in products]
                    else:
                        product_names = [str(p) for p in products]
                    context_parts.append(f"Products/Services: {', '.join(product_names)}")

            # Features
            if website_data.get("features"):
                features = website_data["features"][:10]
                context_parts.append(f"Key Features: {', '.join(features)}")

            # Use cases
            if website_data.get("use_cases"):
                use_cases = website_data["use_cases"][:5]
                context_parts.append(f"Use Cases: {', '.join(use_cases)}")

            # Customer info
            if website_data.get("industries"):
                industries = website_data["industries"][:5]
                context_parts.append(f"Customer Industries: {', '.join(industries)}")
            if website_data.get("personas"):
                personas = website_data["personas"][:5]
                context_parts.append(f"Target Personas: {', '.join(personas)}")

            # Testimonials summary
            if website_data.get("testimonials"):
                testimonials = website_data["testimonials"]
                context_parts.append(f"Customer Testimonials: {len(testimonials)} found")
                # Add a sample testimonial
                if testimonials and hasattr(testimonials[0], 'quote'):
                    sample = testimonials[0]
                    quote_preview = sample.quote[:150] if len(sample.quote) > 150 else sample.quote
                    context_parts.append(f'Sample Review: "{quote_preview}..."')

            # Pricing
            if website_data.get("pricing_model"):
                context_parts.append(f"Pricing Model: {website_data['pricing_model']}")

            # Integrations
            if website_data.get("integrations"):
                integrations = website_data["integrations"][:8]
                context_parts.append(f"Integrations: {', '.join(integrations)}")

            if context_parts:
                website_context = "\n\n=== WEBSITE DATA (scraped from their site) ===\n" + "\n".join(context_parts)

        queries = {
            "market_position": f"""
What is {brand_name}'s market position in the {industry} industry?
{f'Website: {domain}' if domain else ''}
{website_context}

Based on the above website data and your research, provide:
- Their main value proposition
- Who are their top 5 competitors
- How they differentiate from competitors
- Their approximate market share or position (leader, challenger, niche player)

Provide specific competitor names and cite your sources.
""",

            "customer_reviews": f"""
What do customers say about {brand_name}?
{f'Website: {domain}' if domain else ''}
{website_context}

Search for reviews on:
- G2.com
- Capterra
- TrustPilot
- Product Hunt

Summarize:
- Overall customer sentiment (positive/mixed/negative)
- Common praise points (especially about the features listed above)
- Common complaints or issues
- Average rating if available

Be specific and cite review sources.
""",

            "competitive_analysis": f"""
Compare {brand_name} with its main competitors in {industry}.
{f'Website: {domain}' if domain else ''}
{f'Known competitors: {competitors_str}' if competitors_str else ''}
{website_context}

Based on the products and features above, compare:
- Key features and capabilities vs competitors
- Pricing (specific tiers if available)
- Target customer segments
- Unique differentiators

Create a detailed comparison of {brand_name} vs top 3 competitors.
Include specific pricing and feature information where available.
""",

            "pain_points": f"""
What problems do {industry} customers commonly face that products like {brand_name} solve?
{f'Website: {domain}' if domain else ''}
{website_context}

Based on the products, features, and use cases above, research:
- Common pain points in {industry} that {brand_name} addresses
- Specific problems each feature/product solves
- Typical use cases and workflows
- Customer success stories or case studies

Be specific about real customer problems and how {brand_name}'s features solve them.
""",

            "industry_trends": f"""
What are the latest trends and developments in {industry} that affect companies like {brand_name}?
{f'Website: {domain}' if domain else ''}
{website_context}

Based on the features and products above, include:
- Emerging technologies and features in this space
- Market growth trends
- Changes in customer expectations
- New competitors or market entrants
- How {brand_name}'s features align with these trends

Focus on 2024-2025 trends and cite industry reports.
"""
        }

        return queries.get(query_type, "")

    def _parse_response(
        self,
        query_type: str,
        response: Any,
        research: MarketResearch
    ) -> None:
        """Parse Perplexity response and update research object."""

        content = response.content

        if query_type == "market_position":
            research.market_landscape = content

            # Try to extract market position
            position_keywords = {
                "leader": ["market leader", "leading", "#1", "dominant", "top provider"],
                "challenger": ["challenger", "growing", "emerging leader", "gaining market share"],
                "niche": ["niche", "specialized", "focused on", "specific segment"],
                "emerging": ["new", "startup", "emerging", "recently launched"]
            }

            content_lower = content.lower()
            for position, keywords in position_keywords.items():
                if any(kw in content_lower for kw in keywords):
                    research.market_position = position
                    break

            # Extract competitor names
            research.competitors = self._extract_competitors(content)

        elif query_type == "customer_reviews":
            research.customer_reviews_summary = content

            # Determine sentiment
            positive_words = ["excellent", "great", "love", "best", "amazing", "fantastic", "highly recommend"]
            negative_words = ["poor", "terrible", "worst", "avoid", "disappointed", "frustrating", "issues"]

            content_lower = content.lower()
            positive_count = sum(1 for w in positive_words if w in content_lower)
            negative_count = sum(1 for w in negative_words if w in content_lower)

            if positive_count > negative_count * 2:
                research.customer_sentiment = "positive"
            elif negative_count > positive_count * 2:
                research.customer_sentiment = "negative"
            else:
                research.customer_sentiment = "mixed"

        elif query_type == "competitive_analysis":
            research.competitor_comparison = {
                "raw_analysis": content,
                "parsed": self._parse_competitive_analysis(content)
            }

            # Extract additional competitors
            additional_competitors = self._extract_competitors(content)
            existing_names = [c.get("name", "").lower() for c in research.competitors]
            for comp in additional_competitors:
                if comp.get("name", "").lower() not in existing_names:
                    research.competitors.append(comp)

            # Extract features mentioned
            research.key_features = self._extract_features(content)

        elif query_type == "pain_points":
            research.customer_pain_points = self._extract_pain_points(content)

        elif query_type == "industry_trends":
            research.industry_trends = self._extract_trends(content)

    def _extract_competitors(self, content: str) -> List[Dict[str, str]]:
        """Extract competitor names from content."""
        competitors = []

        # Common patterns for competitor mentions
        patterns = [
            r'competitors?\s+(?:include|are|like)\s+([A-Z][a-zA-Z]+(?:,?\s+(?:and\s+)?[A-Z][a-zA-Z]+)*)',
            r'(?:vs|versus|compared to)\s+([A-Z][a-zA-Z]+)',
            r'alternatives?\s+(?:include|like|such as)\s+([A-Z][a-zA-Z]+(?:,?\s+(?:and\s+)?[A-Z][a-zA-Z]+)*)',
        ]

        found_names = set()
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Split by comma or "and"
                names = re.split(r',\s*|\s+and\s+', match)
                for name in names:
                    name = name.strip()
                    if name and len(name) > 2 and name[0].isupper():
                        found_names.add(name)

        for name in list(found_names)[:10]:  # Limit to 10 competitors
            competitors.append({
                "name": name,
                "source": "perplexity_research"
            })

        return competitors

    def _extract_pain_points(self, content: str) -> List[str]:
        """Extract customer pain points from content."""
        pain_points = []

        # Look for pain point patterns
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            # Bullet points or numbered items often contain pain points
            if line.startswith(('-', '•', '*', '1', '2', '3', '4', '5')):
                # Clean up the line
                clean_line = re.sub(r'^[-•*\d.)\s]+', '', line).strip()
                if clean_line and len(clean_line) > 10:
                    pain_points.append(clean_line)

        return pain_points[:15]  # Limit to 15

    def _extract_trends(self, content: str) -> List[str]:
        """Extract industry trends from content."""
        trends = []

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '•', '*', '1', '2', '3', '4', '5')):
                clean_line = re.sub(r'^[-•*\d.)\s]+', '', line).strip()
                if clean_line and len(clean_line) > 10:
                    trends.append(clean_line)

        return trends[:10]  # Limit to 10

    def _extract_features(self, content: str) -> List[str]:
        """Extract feature mentions from content."""
        features = []

        # Common feature-related phrases
        feature_patterns = [
            r'features?\s+(?:include|like|such as)\s+([^.]+)',
            r'capabilities?\s+(?:include|like)\s+([^.]+)',
            r'offers?\s+([^.]+)',
        ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Split by comma
                items = match.split(',')
                for item in items[:5]:
                    item = item.strip()
                    if item and len(item) > 3:
                        features.append(item)

        return list(set(features))[:15]  # Dedupe and limit

    def _parse_competitive_analysis(self, content: str) -> Dict[str, Any]:
        """Parse structured competitive analysis from content."""
        return {
            "raw_text": content[:2000],  # Store first 2000 chars
            "has_pricing_info": "pricing" in content.lower() or "$" in content,
            "has_feature_comparison": "feature" in content.lower() or "comparison" in content.lower(),
        }

    def _calculate_quality_score(self, research: MarketResearch) -> float:
        """Calculate a quality score for the research."""
        score = 0.0

        # Points for having market landscape
        if research.market_landscape and len(research.market_landscape) > 100:
            score += 0.2

        # Points for competitors discovered
        if research.competitors:
            score += min(0.2, len(research.competitors) * 0.04)

        # Points for customer reviews
        if research.customer_reviews_summary and len(research.customer_reviews_summary) > 100:
            score += 0.15

        # Points for pain points
        if research.customer_pain_points:
            score += min(0.15, len(research.customer_pain_points) * 0.02)

        # Points for trends
        if research.industry_trends:
            score += min(0.15, len(research.industry_trends) * 0.03)

        # Points for citations
        if research.citations:
            score += min(0.15, len(research.citations) * 0.01)

        return min(1.0, score)
