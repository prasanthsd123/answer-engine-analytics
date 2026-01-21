"""
Brand Research Service - Deep website analysis + Perplexity market research.

This service performs comprehensive brand research in two phases:
1. Website Crawling: Scrape brand website for products, features, testimonials
2. Perplexity Research: Deep market research for competitors, reviews, trends

The combined research is used to generate realistic user questions.
"""

import asyncio
import logging
import re
import json
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CustomerTestimonial:
    """A customer testimonial from the website."""
    quote: str
    customer_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    industry: Optional[str] = None


@dataclass
class BrandResearch:
    """Comprehensive research results for a brand."""
    brand_name: str
    domain: str

    # Basic info
    tagline: Optional[str] = None
    description: Optional[str] = None
    value_proposition: Optional[str] = None

    # Products & Services
    products: List[Dict[str, str]] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=list)

    # Customer information
    target_audience: Optional[str] = None
    customer_industries: List[str] = field(default_factory=list)
    customer_company_sizes: List[str] = field(default_factory=list)
    customer_personas: List[str] = field(default_factory=list)
    testimonials: List[CustomerTestimonial] = field(default_factory=list)
    case_study_summaries: List[str] = field(default_factory=list)

    # Business model
    pricing_model: Optional[str] = None
    pricing_tiers: List[str] = field(default_factory=list)

    # Competitive landscape
    use_cases: List[str] = field(default_factory=list)
    differentiators: List[str] = field(default_factory=list)
    industry: Optional[str] = None
    competitors_mentioned: List[str] = field(default_factory=list)

    # Raw data for AI analysis
    raw_content: Dict[str, str] = field(default_factory=dict)
    pages_crawled: List[str] = field(default_factory=list)

    # Perplexity market research (NEW)
    perplexity_research: Optional[Dict[str, Any]] = None
    perplexity_citations: List[str] = field(default_factory=list)
    market_landscape: Optional[str] = None
    market_position: Optional[str] = None
    customer_reviews_summary: Optional[str] = None
    customer_sentiment: Optional[str] = None
    customer_pain_points: List[str] = field(default_factory=list)
    industry_trends: List[str] = field(default_factory=list)

    # Research quality
    research_quality_score: float = 0.0
    perplexity_queries_made: int = 0


class BrandResearcher:
    """
    Deep website researcher that extracts comprehensive brand information.

    Crawls multiple pages including:
    - Homepage
    - About/Company pages
    - Products/Features/Solutions pages
    - Pricing page
    - Customers/Case Studies pages
    - Use Cases pages
    """

    # Pages to crawl for comprehensive research
    PAGES_TO_CRAWL = [
        "",  # Homepage
        "about", "about-us", "company",
        "products", "product", "features", "solutions", "platform",
        "pricing", "plans",
        "customers", "case-studies", "case-study", "success-stories", "testimonials",
        "use-cases", "usecases", "industries", "who-we-serve",
        "why-us", "why", "compare", "vs",
        "integrations", "apps", "marketplace",
    ]

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        self.visited_urls: Set[str] = set()

    async def research_brand(
        self,
        brand_name: str,
        domain: Optional[str] = None,
        existing_info: Optional[Dict[str, Any]] = None,
        include_perplexity: bool = True
    ) -> BrandResearch:
        """
        Perform comprehensive research on a brand.

        Flow:
        1. Deep crawl website for products, features, testimonials
        2. Use GPT to analyze website content
        3. Use Perplexity for market research (competitors, reviews, trends)
        4. Combine all research data

        Args:
            brand_name: Name of the brand
            domain: Website domain (e.g., "example.com")
            existing_info: Any existing brand information
            include_perplexity: Whether to include Perplexity market research

        Returns:
            BrandResearch object with comprehensive extracted information
        """
        research = BrandResearch(brand_name=brand_name, domain=domain or "")
        self.visited_urls.clear()

        # Step 1: Deep crawl website if domain provided
        if domain:
            logger.info(f"Starting deep crawl of {domain}")
            await self._deep_crawl_website(domain, research)
            logger.info(f"Crawled {len(research.pages_crawled)} pages from {domain}")

        # Step 2: Extract testimonials from raw content
        self._extract_testimonials(research)

        # Step 3: Use GPT to analyze website content
        if settings.OPENAI_API_KEY and research.raw_content:
            logger.info("Analyzing website content with GPT...")
            ai_analysis = await self._analyze_with_ai(research, existing_info)
            if ai_analysis:
                self._apply_ai_analysis(research, ai_analysis)

        # Step 4: Use Perplexity for market research (NEW - Critical Flow)
        if include_perplexity and settings.PERPLEXITY_API_KEY:
            logger.info("Starting Perplexity market research...")
            await self._conduct_perplexity_research(research, existing_info)

        # Calculate overall research quality score
        research.research_quality_score = self._calculate_quality_score(research)

        return research

    async def _conduct_perplexity_research(
        self,
        research: BrandResearch,
        existing_info: Optional[Dict[str, Any]]
    ) -> None:
        """Conduct deep market research using Perplexity."""
        try:
            from .perplexity_researcher import PerplexityResearcher

            perplexity = PerplexityResearcher()

            # Get industry from existing info or research
            industry = research.industry
            if not industry and existing_info:
                industry = existing_info.get("industry", "")
            if not industry:
                industry = "technology"  # Default fallback

            # Get known competitors
            known_competitors = research.competitors_mentioned or []
            if existing_info and existing_info.get("competitors"):
                known_competitors.extend(existing_info["competitors"])

            # Conduct Perplexity research with ALL scraped website data
            market_research = await perplexity.research_market(
                brand_name=research.brand_name,
                industry=industry,
                domain=research.domain,
                website_data={
                    # Core product info from website scraping
                    "products": research.products,
                    "features": research.features,
                    "use_cases": research.use_cases,
                    # Customer info
                    "testimonials": research.testimonials,
                    "industries": research.customer_industries,
                    "personas": research.customer_personas,
                    # Additional context
                    "tagline": research.tagline,
                    "description": research.description,
                    "value_proposition": research.value_proposition,
                    "pricing_model": research.pricing_model,
                    "integrations": research.integrations,
                },
                known_competitors=known_competitors
            )

            # Apply Perplexity research to main research object
            research.perplexity_research = {
                "market_landscape": market_research.market_landscape,
                "market_position": market_research.market_position,
                "competitors": market_research.competitors,
                "competitor_comparison": market_research.competitor_comparison,
                "customer_reviews_summary": market_research.customer_reviews_summary,
                "customer_sentiment": market_research.customer_sentiment,
                "customer_pain_points": market_research.customer_pain_points,
                "industry_trends": market_research.industry_trends,
                "pricing_analysis": market_research.pricing_analysis,
                "key_features": market_research.key_features,
            }
            research.perplexity_citations = market_research.citations
            research.perplexity_queries_made = market_research.queries_made

            # Merge key data into main research
            research.market_landscape = market_research.market_landscape
            research.market_position = market_research.market_position
            research.customer_reviews_summary = market_research.customer_reviews_summary
            research.customer_sentiment = market_research.customer_sentiment

            # Merge pain points (dedupe)
            existing_pain_points = set(research.customer_pain_points)
            for pp in market_research.customer_pain_points:
                if pp not in existing_pain_points:
                    research.customer_pain_points.append(pp)

            # Merge industry trends
            research.industry_trends.extend(market_research.industry_trends)

            # Merge competitors (dedupe by name)
            existing_competitors = set(c.lower() for c in research.competitors_mentioned)
            for comp in market_research.competitors:
                comp_name = comp.get("name", "")
                if comp_name.lower() not in existing_competitors:
                    research.competitors_mentioned.append(comp_name)

            # Update industry if not set
            if not research.industry and industry:
                research.industry = industry

            logger.info(f"Perplexity research complete: {market_research.queries_made} queries, "
                       f"{len(market_research.citations)} citations")

        except Exception as e:
            logger.error(f"Perplexity research failed: {e}")
            # Don't fail the whole research if Perplexity fails

    def _calculate_quality_score(self, research: BrandResearch) -> float:
        """Calculate overall research quality score (0-1)."""
        score = 0.0

        # Website data (40%)
        if research.pages_crawled:
            score += min(0.15, len(research.pages_crawled) * 0.01)
        if research.products:
            score += min(0.1, len(research.products) * 0.02)
        if research.features:
            score += min(0.1, len(research.features) * 0.01)
        if research.testimonials:
            score += min(0.05, len(research.testimonials) * 0.01)

        # Perplexity data (40%)
        if research.perplexity_research:
            if research.market_landscape:
                score += 0.1
            if research.competitors_mentioned:
                score += min(0.1, len(research.competitors_mentioned) * 0.02)
            if research.customer_pain_points:
                score += min(0.1, len(research.customer_pain_points) * 0.02)
            if research.industry_trends:
                score += min(0.1, len(research.industry_trends) * 0.02)

        # Citations (20%)
        if research.perplexity_citations:
            score += min(0.2, len(research.perplexity_citations) * 0.01)

        return min(1.0, score)

    async def _deep_crawl_website(self, domain: str, research: BrandResearch) -> None:
        """Crawl multiple pages of the website for comprehensive data."""
        base_urls = [f"https://{domain}", f"https://www.{domain}"]

        # Find working base URL
        base_url = None
        for url in base_urls:
            try:
                response = await self.http_client.get(url)
                if response.status_code == 200:
                    base_url = str(response.url).rstrip('/')
                    break
            except Exception:
                continue

        if not base_url:
            logger.warning(f"Could not connect to {domain}")
            return

        # Crawl all target pages concurrently
        tasks = []
        for page_path in self.PAGES_TO_CRAWL:
            url = f"{base_url}/{page_path}" if page_path else base_url
            tasks.append(self._crawl_page(url, research))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _crawl_page(self, url: str, research: BrandResearch) -> None:
        """Crawl a single page and extract content."""
        # Normalize URL
        normalized_url = url.rstrip('/')
        if normalized_url in self.visited_urls:
            return
        self.visited_urls.add(normalized_url)

        try:
            response = await self.http_client.get(url)
            if response.status_code != 200:
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get page type from URL
            path = urlparse(str(response.url)).path.strip('/')
            page_type = path.split('/')[0] if path else 'homepage'

            # Extract different content based on page type
            content = self._extract_page_content(soup, page_type)

            if content and len(content) > 100:  # Only save meaningful content
                research.raw_content[page_type] = content
                research.pages_crawled.append(str(response.url))

            # Extract meta information from homepage
            if page_type == 'homepage':
                self._extract_meta_info(soup, research)

            # Look for additional relevant links to crawl
            await self._find_and_crawl_links(soup, str(response.url), research)

        except Exception as e:
            logger.debug(f"Failed to crawl {url}: {e}")

    def _extract_page_content(self, soup: BeautifulSoup, page_type: str) -> str:
        """Extract relevant content from a page based on its type."""
        # Remove non-content elements
        for element in soup(["script", "style", "nav", "footer", "noscript", "iframe"]):
            element.decompose()

        content_parts = []

        # Extract headings - they often contain key information
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text = heading.get_text(strip=True)
            if text and len(text) > 3:
                content_parts.append(f"[HEADING] {text}")

        # For customer/testimonial pages, focus on quotes and testimonials
        if page_type in ['customers', 'testimonials', 'case-studies', 'success-stories']:
            # Look for blockquotes
            for quote in soup.find_all('blockquote'):
                text = quote.get_text(strip=True)
                if text:
                    content_parts.append(f"[TESTIMONIAL] {text}")

            # Look for elements that might contain testimonials
            for elem in soup.find_all(class_=re.compile(r'testimonial|quote|review|customer-story', re.I)):
                text = elem.get_text(separator=' ', strip=True)
                if text and len(text) > 50:
                    content_parts.append(f"[CUSTOMER_QUOTE] {text[:1000]}")

        # For pricing pages, extract pricing information
        if page_type in ['pricing', 'plans']:
            for elem in soup.find_all(class_=re.compile(r'price|plan|tier|package', re.I)):
                text = elem.get_text(separator=' ', strip=True)
                if text:
                    content_parts.append(f"[PRICING] {text[:500]}")

        # For features/products pages, extract feature lists
        if page_type in ['features', 'products', 'solutions', 'platform']:
            for elem in soup.find_all(['ul', 'ol']):
                items = [li.get_text(strip=True) for li in elem.find_all('li')]
                if items and len(items) >= 3:
                    content_parts.append(f"[FEATURES] " + " | ".join(items[:15]))

        # Extract main content areas
        main_content = soup.find('main') or soup.find('article') or soup.find(role='main')
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            content_parts.append(f"[MAIN_CONTENT] {text[:8000]}")
        else:
            # Fall back to body content
            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)
                content_parts.append(f"[BODY_CONTENT] {text[:6000]}")

        return "\n".join(content_parts)

    def _extract_meta_info(self, soup: BeautifulSoup, research: BrandResearch) -> None:
        """Extract meta information from the page."""
        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            research.description = meta_desc["content"]

        # OG description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content") and not research.description:
            research.description = og_desc["content"]

        # Tagline from H1
        h1 = soup.find("h1")
        if h1:
            research.tagline = h1.get_text(strip=True)

        # Look for value proposition
        for elem in soup.find_all(class_=re.compile(r'hero|headline|tagline|value-prop', re.I)):
            text = elem.get_text(strip=True)
            if text and 10 < len(text) < 200:
                research.value_proposition = text
                break

    async def _find_and_crawl_links(self, soup: BeautifulSoup, current_url: str, research: BrandResearch) -> None:
        """Find and crawl additional relevant links on the page."""
        relevant_patterns = [
            r'/customers?/', r'/case-stud', r'/testimonial', r'/success',
            r'/use-case', r'/industr', r'/solution', r'/who-we-serve'
        ]

        base_domain = urlparse(current_url).netloc

        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(current_url, href)

            # Only follow links on same domain
            if urlparse(full_url).netloc != base_domain:
                continue

            # Check if link matches relevant patterns
            if any(re.search(pattern, full_url, re.I) for pattern in relevant_patterns):
                if full_url not in self.visited_urls and len(self.visited_urls) < 20:
                    await self._crawl_page(full_url, research)

    def _extract_testimonials(self, research: BrandResearch) -> None:
        """Extract customer testimonials from raw content."""
        testimonial_pattern = re.compile(
            r'\[(?:TESTIMONIAL|CUSTOMER_QUOTE)\]\s*(.+?)(?=\[|$)',
            re.DOTALL
        )

        for page_type, content in research.raw_content.items():
            for match in testimonial_pattern.finditer(content):
                quote_text = match.group(1).strip()
                if quote_text and len(quote_text) > 30:
                    testimonial = CustomerTestimonial(quote=quote_text[:500])
                    research.testimonials.append(testimonial)

    async def _analyze_with_ai(
        self,
        research: BrandResearch,
        existing_info: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Use AI to analyze all collected website content."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            # Build comprehensive context from all crawled pages
            context_parts = [
                f"Brand Name: {research.brand_name}",
                f"Website: {research.domain}",
                f"Pages Crawled: {len(research.pages_crawled)}",
            ]

            if research.description:
                context_parts.append(f"Meta Description: {research.description}")
            if research.tagline:
                context_parts.append(f"Tagline: {research.tagline}")

            # Add existing info
            if existing_info:
                if existing_info.get("industry"):
                    context_parts.append(f"Known Industry: {existing_info['industry']}")
                if existing_info.get("keywords"):
                    context_parts.append(f"Keywords: {', '.join(existing_info['keywords'])}")

            # Add raw content from each page (prioritize customer-focused pages)
            priority_pages = ['customers', 'case-studies', 'testimonials', 'success-stories',
                           'use-cases', 'pricing', 'features', 'solutions', 'homepage']

            content_budget = 12000  # tokens budget for content
            current_length = 0

            for page_type in priority_pages:
                if page_type in research.raw_content and current_length < content_budget:
                    content = research.raw_content[page_type]
                    allowed_length = min(len(content), content_budget - current_length, 4000)
                    context_parts.append(f"\n--- {page_type.upper()} PAGE ---\n{content[:allowed_length]}")
                    current_length += allowed_length

            # Add any remaining pages
            for page_type, content in research.raw_content.items():
                if page_type not in priority_pages and current_length < content_budget:
                    allowed_length = min(len(content), content_budget - current_length, 2000)
                    context_parts.append(f"\n--- {page_type.upper()} PAGE ---\n{content[:allowed_length]}")
                    current_length += allowed_length

            context = "\n".join(context_parts)

            prompt = f"""You are a business analyst. Analyze this company's website content in detail and extract comprehensive information.

{context}

Based on the website content, extract the following. Be SPECIFIC and use actual information from the content, not generic descriptions:

{{
    "products": [
        {{"name": "actual product name", "description": "what it does", "category": "category"}}
    ],
    "features": ["list of specific features mentioned on the website"],
    "integrations": ["specific tools/platforms they integrate with"],

    "target_audience": "who is the primary customer (be specific based on website content)",
    "customer_industries": ["specific industries their customers are in, from case studies/testimonials"],
    "customer_company_sizes": ["startup", "SMB", "mid-market", "enterprise" - based on actual customers],
    "customer_personas": ["specific job titles/roles that would use this product"],

    "testimonials": [
        {{"quote": "actual quote if found", "company": "company name", "role": "person's role", "industry": "their industry"}}
    ],
    "case_study_summaries": ["brief summary of each case study found"],

    "pricing_model": "how they charge (freemium, subscription, usage-based, etc.)",
    "pricing_tiers": ["names of pricing tiers if found"],

    "use_cases": ["specific problems they solve or use cases from the website"],
    "differentiators": ["what makes them unique - from their own messaging"],
    "industry": "primary industry/category",
    "competitors": ["competitors mentioned or implied from comparison pages"]
}}

IMPORTANT:
- Only include information you can actually find in the content
- Be specific - use actual product names, customer names, and quotes
- For testimonials, include the actual quote text if available
- Empty arrays [] are fine if information isn't available
- Return ONLY valid JSON, no markdown formatting"""

            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3000
            )

            result_text = response.choices[0].message.content.strip()

            # Clean up markdown formatting
            if result_text.startswith("```"):
                result_text = re.sub(r'^```json?\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)

            return json.loads(result_text)

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None

    def _apply_ai_analysis(self, research: BrandResearch, analysis: Dict[str, Any]) -> None:
        """Apply AI analysis results to the research object."""
        research.products = analysis.get("products", [])
        research.features = analysis.get("features", [])
        research.integrations = analysis.get("integrations", [])

        research.target_audience = analysis.get("target_audience")
        research.customer_industries = analysis.get("customer_industries", [])
        research.customer_company_sizes = analysis.get("customer_company_sizes", [])
        research.customer_personas = analysis.get("customer_personas", [])

        # Add AI-extracted testimonials
        for t in analysis.get("testimonials", []):
            if t.get("quote"):
                testimonial = CustomerTestimonial(
                    quote=t["quote"],
                    company=t.get("company"),
                    role=t.get("role"),
                    industry=t.get("industry")
                )
                research.testimonials.append(testimonial)

        research.case_study_summaries = analysis.get("case_study_summaries", [])
        research.pricing_model = analysis.get("pricing_model")
        research.pricing_tiers = analysis.get("pricing_tiers", [])
        research.use_cases = analysis.get("use_cases", [])
        research.differentiators = analysis.get("differentiators", [])
        research.industry = analysis.get("industry")
        research.competitors_mentioned = analysis.get("competitors", [])

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
