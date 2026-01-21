"""
Brand Research Service - Analyzes brand websites and extracts key information.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class BrandResearch:
    """Research results for a brand."""
    brand_name: str
    domain: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    products: List[Dict[str, str]] = None
    features: List[str] = None
    target_audience: Optional[str] = None
    pricing_model: Optional[str] = None
    use_cases: List[str] = None
    differentiators: List[str] = None
    industry: Optional[str] = None
    competitors_mentioned: List[str] = None
    raw_content: Optional[str] = None

    def __post_init__(self):
        self.products = self.products or []
        self.features = self.features or []
        self.use_cases = self.use_cases or []
        self.differentiators = self.differentiators or []
        self.competitors_mentioned = self.competitors_mentioned or []


class BrandResearcher:
    """Researches brands by analyzing their websites and using AI."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AnswerEngineBot/1.0)"
            }
        )

    async def research_brand(
        self,
        brand_name: str,
        domain: Optional[str] = None,
        existing_info: Optional[Dict[str, Any]] = None
    ) -> BrandResearch:
        """
        Research a brand by crawling their website and analyzing with AI.

        Args:
            brand_name: Name of the brand
            domain: Website domain (e.g., "example.com")
            existing_info: Any existing brand information

        Returns:
            BrandResearch object with extracted information
        """
        research = BrandResearch(brand_name=brand_name, domain=domain or "")

        # Step 1: Crawl website if domain provided
        if domain:
            website_content = await self._crawl_website(domain)
            if website_content:
                research.raw_content = website_content
                # Extract basic info from HTML
                basic_info = self._extract_basic_info(website_content)
                research.tagline = basic_info.get("tagline")
                research.description = basic_info.get("description")

        # Step 2: Use AI to analyze and extract detailed information
        if settings.OPENAI_API_KEY:
            ai_analysis = await self._analyze_with_ai(research, existing_info)
            if ai_analysis:
                research.products = ai_analysis.get("products", [])
                research.features = ai_analysis.get("features", [])
                research.target_audience = ai_analysis.get("target_audience")
                research.pricing_model = ai_analysis.get("pricing_model")
                research.use_cases = ai_analysis.get("use_cases", [])
                research.differentiators = ai_analysis.get("differentiators", [])
                research.industry = ai_analysis.get("industry")
                research.competitors_mentioned = ai_analysis.get("competitors", [])

        return research

    async def _crawl_website(self, domain: str) -> Optional[str]:
        """Crawl the main pages of a website."""
        urls_to_try = [
            f"https://{domain}",
            f"https://www.{domain}",
            f"https://{domain}/about",
            f"https://{domain}/features",
            f"https://{domain}/pricing",
        ]

        combined_content = []

        for url in urls_to_try[:3]:  # Limit to first 3 URLs
            try:
                response = await self.http_client.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Remove script and style elements
                    for script in soup(["script", "style", "nav", "footer", "header"]):
                        script.decompose()

                    # Get text content
                    text = soup.get_text(separator=' ', strip=True)
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text)
                    combined_content.append(text[:5000])  # Limit per page

            except Exception as e:
                logger.debug(f"Failed to crawl {url}: {e}")
                continue

        return "\n\n".join(combined_content) if combined_content else None

    def _extract_basic_info(self, html_content: str) -> Dict[str, str]:
        """Extract basic info from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser') if '<' in html_content else None
        info = {}

        if soup:
            # Try to find meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                info["description"] = meta_desc["content"]

            # Try to find tagline (often in h1 or hero section)
            h1 = soup.find("h1")
            if h1:
                info["tagline"] = h1.get_text(strip=True)

        return info

    async def _analyze_with_ai(
        self,
        research: BrandResearch,
        existing_info: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Use AI to analyze brand information."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # Build context from available info
            context_parts = [f"Brand Name: {research.brand_name}"]
            if research.domain:
                context_parts.append(f"Website: {research.domain}")
            if research.description:
                context_parts.append(f"Description: {research.description}")
            if research.raw_content:
                context_parts.append(f"Website Content (excerpt): {research.raw_content[:3000]}")
            if existing_info:
                if existing_info.get("industry"):
                    context_parts.append(f"Industry: {existing_info['industry']}")
                if existing_info.get("keywords"):
                    context_parts.append(f"Keywords: {', '.join(existing_info['keywords'])}")
                if existing_info.get("products"):
                    context_parts.append(f"Products: {existing_info['products']}")

            context = "\n".join(context_parts)

            prompt = f"""Analyze this brand and extract key information. Return a JSON object.

{context}

Extract and return this JSON structure:
{{
    "products": ["list of main products/services offered"],
    "features": ["key features or capabilities"],
    "target_audience": "who is the ideal customer (e.g., 'Small businesses', 'Enterprise', 'Developers')",
    "pricing_model": "how they charge (e.g., 'Freemium', 'Subscription', 'Usage-based')",
    "use_cases": ["main problems they solve or use cases"],
    "differentiators": ["what makes them unique vs competitors"],
    "industry": "primary industry/category",
    "competitors": ["likely competitors in this space"]
}}

Be concise. If information is not available, use empty lists or null.
Return ONLY valid JSON, no markdown or explanation."""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )

            result_text = response.choices[0].message.content.strip()
            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                result_text = re.sub(r'^```json?\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)

            import json
            return json.loads(result_text)

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
