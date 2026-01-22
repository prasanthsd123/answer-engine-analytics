"""
Smart Question Generator - Generates realistic user questions based on deep website research.

This service creates questions that mimic how real users would search
for products/services in AI search engines like ChatGPT, Perplexity, etc.

Questions are generated based on actual website content:
- Real products and features
- Actual customer industries and personas
- Specific use cases and problems solved
- Customer testimonials and case studies
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..config import settings
from .brand_researcher import BrandResearch

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestion:
    """A generated question with metadata."""
    text: str
    category: str
    intent: str  # discovery, comparison, evaluation, feature, problem-solving
    priority: int  # 1-5, higher = more important


class SmartQuestionGenerator:
    """
    Generates realistic user questions based on deep brand research.

    Instead of simple templates, this uses comprehensive website research
    to generate questions that real users would actually type when
    searching for solutions in their specific situation.
    """

    # Question intent categories with descriptions
    INTENTS = {
        "discovery": "User discovering options in a category",
        "comparison": "User comparing specific products/brands",
        "evaluation": "User evaluating if a product is right for them",
        "feature": "User looking for specific capabilities",
        "problem_solving": "User trying to solve a specific problem",
        "review": "User looking for opinions and reviews",
        "pricing": "User researching costs and value",
        "industry_specific": "User searching within their specific industry",
        "persona_specific": "User searching based on their role/job"
    }

    def __init__(self):
        self.openai_client = None
        if settings.OPENAI_API_KEY:
            import openai
            self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_questions(
        self,
        brand_research: BrandResearch,
        competitors: List[str] = None,
        num_questions: int = 20,
        focus_intents: List[str] = None
    ) -> List[GeneratedQuestion]:
        """
        Generate realistic user questions based on comprehensive brand research.

        Args:
            brand_research: Deep research data about the brand from website crawling
            competitors: List of competitor names
            num_questions: Target number of questions to generate
            focus_intents: Specific intents to focus on (optional)

        Returns:
            List of GeneratedQuestion objects
        """
        competitors = competitors or brand_research.competitors_mentioned or []
        focus_intents = focus_intents or list(self.INTENTS.keys())

        if not self.openai_client:
            logger.warning("OpenAI client not available, using template fallback")
            return self._generate_template_questions(brand_research, competitors)

        try:
            questions = await self._generate_with_ai(
                brand_research, competitors, num_questions, focus_intents
            )
            return questions
        except Exception as e:
            logger.error(f"AI question generation failed: {e}")
            return self._generate_template_questions(brand_research, competitors)

    async def _generate_with_ai(
        self,
        research: BrandResearch,
        competitors: List[str],
        num_questions: int,
        focus_intents: List[str]
    ) -> List[GeneratedQuestion]:
        """Generate questions using AI based on comprehensive research."""

        # Build detailed context from research
        context = self._build_comprehensive_context(research, competitors)

        prompt = f"""You are an expert at understanding how real users search for products and services using AI assistants like ChatGPT, Perplexity, and Claude.

Based on DEEP RESEARCH of this company's website, generate {num_questions} realistic search questions that potential customers would actually type.

=== COMPANY RESEARCH DATA ===
{context}

=== QUESTION GENERATION RULES ===

1. **Use ACTUAL data from the research** - reference real:
   - Product names found on the website
   - Specific features mentioned
   - Industries their customers are in
   - Job roles/personas that use the product
   - Use cases and problems they solve
   - Pricing model information

2. **Question Types to Generate** (distribute across these):

   DISCOVERY (40%) - Generic category searches BEFORE knowing the brand:
   - "best [specific product category] for [specific industry found]"
   - "top [category] tools for [persona/role found]"
   - "[specific problem from use cases] solutions"
   - "what is the best [category] software"
   - "[category] recommendations for [company size]"
   - "top rated [category] tools"
   These are the MOST IMPORTANT - real users search generically first!

   COMPARISON (15%) - Comparing this brand with competitors:
   - "[brand] vs [competitor] for [specific use case]"
   - "compare [brand] and [competitor] [specific feature]"
   - "[competitor] alternative for [industry]"

   EVALUATION (12%) - Deciding if this product is right for them:
   - "is [brand] good for [specific industry found]"
   - "[brand] for [company size found - startup/SMB/enterprise]"
   - "should [persona] use [brand]"

   FEATURE-SPECIFIC (12%) - Searching for specific capabilities:
   - "does [brand] have [actual feature from website]"
   - "[brand] [specific feature] capabilities"
   - "best [feature] tool like [brand]"

   PROBLEM-SOLVING (8%) - User has a specific problem:
   - "how to [actual use case from website]"
   - "best way to [problem they solve]"
   - "[specific pain point] solution for [industry]"

   INDUSTRY-SPECIFIC (8%) - Industry-focused searches:
   - "[brand] for [specific industry from customer list]"
   - "best [category] for [industry] companies"
   - "[industry] [product category] recommendations"

   PRICING/VALUE (5%) - Cost-related questions:
   - "[brand] pricing for [company size]"
   - "is [brand] worth it for [persona]"
   - "[brand] [pricing tier] vs [tier] comparison"

3. **Make questions REALISTIC**:
   - Mix formal and casual language
   - Some short (3-5 words), some longer (10+ words)
   - Include occasional typos or informal phrasing
   - Questions a real person would type, not perfect grammar

4. **IMPORTANT - Be Specific**:
   - DON'T use generic placeholders
   - DO use actual product names, features, industries from the research
   - Reference real customer types and use cases found

=== OUTPUT FORMAT ===
Return a JSON array:
[
  {{
    "text": "exact question as user would type it",
    "category": "discovery|comparison|evaluation|feature|problem_solving|industry_specific|pricing",
    "intent": "brief description of what they're looking for",
    "priority": 1-5 (5 = most important for brand visibility)
  }}
]

Generate diverse, realistic questions using the ACTUAL research data provided. Return ONLY valid JSON."""

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,  # Higher for diversity
            max_tokens=4000
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up markdown formatting
        if result_text.startswith("```"):
            result_text = re.sub(r'^```json?\n?', '', result_text)
            result_text = re.sub(r'\n?```$', '', result_text)

        questions_data = json.loads(result_text)

        return [
            GeneratedQuestion(
                text=q["text"],
                category=q["category"],
                intent=q.get("intent", ""),
                priority=q.get("priority", 3)
            )
            for q in questions_data
        ]

    def _build_comprehensive_context(self, research: BrandResearch, competitors: List[str]) -> str:
        """Build detailed context from comprehensive brand research."""
        parts = []

        # Basic info
        parts.append(f"BRAND NAME: {research.brand_name}")
        if research.domain:
            parts.append(f"WEBSITE: {research.domain}")
        if research.industry:
            parts.append(f"INDUSTRY: {research.industry}")
        if research.tagline:
            parts.append(f"TAGLINE: {research.tagline}")
        if research.description:
            parts.append(f"DESCRIPTION: {research.description}")
        if research.value_proposition:
            parts.append(f"VALUE PROPOSITION: {research.value_proposition}")

        # Products (with details)
        if research.products:
            products_text = []
            for p in research.products[:10]:
                if isinstance(p, dict):
                    name = p.get("name", "Unknown")
                    desc = p.get("description", "")
                    products_text.append(f"  - {name}: {desc}" if desc else f"  - {name}")
                else:
                    products_text.append(f"  - {p}")
            parts.append(f"PRODUCTS/SERVICES:\n" + "\n".join(products_text))

        # Features
        if research.features:
            parts.append(f"KEY FEATURES: {', '.join(research.features[:15])}")

        # Integrations
        if research.integrations:
            parts.append(f"INTEGRATIONS: {', '.join(research.integrations[:10])}")

        # Customer information
        if research.target_audience:
            parts.append(f"TARGET AUDIENCE: {research.target_audience}")

        if research.customer_industries:
            parts.append(f"CUSTOMER INDUSTRIES: {', '.join(research.customer_industries[:10])}")

        if research.customer_company_sizes:
            parts.append(f"CUSTOMER COMPANY SIZES: {', '.join(research.customer_company_sizes)}")

        if research.customer_personas:
            parts.append(f"BUYER PERSONAS (Job Roles): {', '.join(research.customer_personas[:10])}")

        # Testimonials (actual customer quotes)
        if research.testimonials:
            testimonial_text = []
            for t in research.testimonials[:5]:
                quote_preview = t.quote[:150] + "..." if len(t.quote) > 150 else t.quote
                attribution = []
                if t.company:
                    attribution.append(t.company)
                if t.role:
                    attribution.append(t.role)
                if t.industry:
                    attribution.append(t.industry)
                attr_str = f" ({', '.join(attribution)})" if attribution else ""
                testimonial_text.append(f'  - "{quote_preview}"{attr_str}')
            parts.append(f"CUSTOMER TESTIMONIALS:\n" + "\n".join(testimonial_text))

        # Case studies
        if research.case_study_summaries:
            parts.append(f"CASE STUDIES:\n  - " + "\n  - ".join(research.case_study_summaries[:5]))

        # Use cases
        if research.use_cases:
            parts.append(f"USE CASES (Problems They Solve):\n  - " + "\n  - ".join(research.use_cases[:10]))

        # Differentiators
        if research.differentiators:
            parts.append(f"DIFFERENTIATORS:\n  - " + "\n  - ".join(research.differentiators[:5]))

        # Pricing
        if research.pricing_model:
            parts.append(f"PRICING MODEL: {research.pricing_model}")
        if research.pricing_tiers:
            parts.append(f"PRICING TIERS: {', '.join(research.pricing_tiers)}")

        # Competitors
        all_competitors = list(set(competitors + research.competitors_mentioned))
        if all_competitors:
            parts.append(f"COMPETITORS: {', '.join(all_competitors[:8])}")

        # === PERPLEXITY MARKET RESEARCH (NEW) ===
        if research.perplexity_research or research.market_landscape:
            parts.append("\n=== PERPLEXITY MARKET RESEARCH ===")

            if research.market_landscape:
                parts.append(f"MARKET LANDSCAPE: {research.market_landscape[:1500]}")

            if research.market_position:
                parts.append(f"MARKET POSITION: {research.market_position}")

            if research.customer_reviews_summary:
                parts.append(f"CUSTOMER REVIEWS SUMMARY: {research.customer_reviews_summary[:800]}")

            if research.customer_sentiment:
                parts.append(f"CUSTOMER SENTIMENT: {research.customer_sentiment}")

            if research.customer_pain_points:
                parts.append(f"CUSTOMER PAIN POINTS:\n  - " + "\n  - ".join(research.customer_pain_points[:10]))

            if research.industry_trends:
                parts.append(f"INDUSTRY TRENDS:\n  - " + "\n  - ".join(research.industry_trends[:8]))

            if research.perplexity_citations:
                parts.append(f"RESEARCH SOURCES: {len(research.perplexity_citations)} citations from G2, Capterra, industry reports")

        # Research quality
        if research.research_quality_score > 0:
            parts.append(f"\nRESEARCH QUALITY SCORE: {research.research_quality_score:.2f}")

        # Pages crawled (for context)
        if research.pages_crawled:
            parts.append(f"WEBSITE PAGES ANALYZED: {len(research.pages_crawled)}")

        if research.perplexity_queries_made > 0:
            parts.append(f"PERPLEXITY QUERIES: {research.perplexity_queries_made}")

        return "\n\n".join(parts)

    def _generate_template_questions(
        self,
        research: BrandResearch,
        competitors: List[str]
    ) -> List[GeneratedQuestion]:
        """Fallback template-based generation using research data.

        Distribution (matches AI prompt):
        - Discovery: 40% (8 questions)
        - Comparison: 15% (3 questions)
        - Evaluation: 12% (2-3 questions)
        - Feature: 12% (2-3 questions)
        - Problem-solving: 8% (1-2 questions)
        - Industry-specific: 8% (1-2 questions)
        - Pricing: 5% (1 question)
        """
        questions = []
        brand = research.brand_name
        industry = research.industry or "software"

        # Use actual data from research where available
        customer_industries = research.customer_industries or [industry]
        personas = research.customer_personas or ["teams", "businesses"]
        features = research.features or []
        use_cases = research.use_cases or []
        company_sizes = research.customer_company_sizes or ["small business", "enterprise"]

        # === DISCOVERY (40% = 8 questions) - Most important! ===
        # These are generic searches where the brand should naturally appear
        questions.append(GeneratedQuestion(
            f"best {industry} software", "discovery", "generic category search", 5
        ))
        questions.append(GeneratedQuestion(
            f"top {industry} tools 2024", "discovery", "yearly best list", 5
        ))
        questions.append(GeneratedQuestion(
            f"what is the best {industry} platform", "discovery", "platform search", 5
        ))

        for ind in customer_industries[:2]:
            questions.append(GeneratedQuestion(
                f"best {industry} for {ind}", "discovery", "industry-specific discovery", 5
            ))

        for persona in personas[:2]:
            questions.append(GeneratedQuestion(
                f"top {industry} tools for {persona}", "discovery", "persona discovery", 4
            ))

        for size in company_sizes[:1]:
            questions.append(GeneratedQuestion(
                f"{industry} recommendations for {size}", "discovery", "size-based discovery", 4
            ))

        # === COMPARISON (15% = 3 questions) ===
        for comp in competitors[:3]:
            questions.append(GeneratedQuestion(
                f"{brand} vs {comp}", "comparison", "direct comparison", 5
            ))

        # === EVALUATION (12% = 2-3 questions) ===
        questions.append(GeneratedQuestion(
            f"is {brand} good", "evaluation", "quality assessment", 4
        ))
        questions.append(GeneratedQuestion(
            f"{brand} reviews", "evaluation", "seeking reviews", 4
        ))
        if customer_industries:
            questions.append(GeneratedQuestion(
                f"is {brand} good for {customer_industries[0]}",
                "evaluation", "fit assessment", 4
            ))

        # === FEATURE-SPECIFIC (12% = 2-3 questions) ===
        for feature in features[:2]:
            questions.append(GeneratedQuestion(
                f"does {brand} have {feature}", "feature", "capability check", 3
            ))

        # === PROBLEM-SOLVING (8% = 1-2 questions) ===
        for use_case in use_cases[:2]:
            questions.append(GeneratedQuestion(
                f"best tool for {use_case}", "problem_solving", "solution search", 4
            ))

        # === INDUSTRY-SPECIFIC (8% = 1-2 questions) ===
        for ind in customer_industries[:2]:
            questions.append(GeneratedQuestion(
                f"best {industry} for {ind} companies",
                "industry_specific", "industry fit", 4
            ))

        # === PRICING (5% = 1 question) ===
        questions.append(GeneratedQuestion(
            f"{brand} pricing", "pricing", "cost research", 3
        ))

        return questions[:20]


@dataclass
class SmartGenerationResult:
    """Result of smart question generation including research data."""
    questions: List[GeneratedQuestion]
    research_summary: Dict[str, Any]


async def generate_smart_questions(
    brand_name: str,
    domain: Optional[str] = None,
    industry: Optional[str] = None,
    keywords: List[str] = None,
    products: List[Dict] = None,
    competitors: List[str] = None,
    num_questions: int = 20,
    return_research: bool = False,
    additional_urls: Optional[List[str]] = None
) -> List[GeneratedQuestion] | SmartGenerationResult:
    """
    Convenience function to research a brand deeply and generate questions.

    This is the main entry point for smart question generation.

    Smart Flow:
    1. Check sitemap.xml for actual pages
    2. Parse navigation/footer links from homepage
    3. Crawl discovered + user-provided URLs
    4. Use GPT to analyze website content
    5. Use Perplexity for market research (competitors, reviews, trends)
    6. Generate realistic user questions based on all research

    Args:
        brand_name: Name of the brand
        domain: Website domain
        industry: Industry/category
        keywords: Known keywords
        products: Known products
        competitors: Known competitors
        num_questions: Number of questions to generate
        return_research: If True, return SmartGenerationResult with research summary
        additional_urls: User-provided URLs to crawl (for small websites)

    Returns:
        List of GeneratedQuestion objects, or SmartGenerationResult if return_research=True
    """
    from .brand_researcher import BrandResearcher

    logger.info(f"Starting smart question generation for {brand_name}")

    # Deep research of the brand (now includes Perplexity)
    researcher = BrandResearcher()
    try:
        existing_info = {
            "industry": industry,
            "keywords": keywords or [],
            "products": products or [],
            "competitors": competitors or []
        }

        logger.info(f"Researching brand: {brand_name}, domain: {domain}")
        if additional_urls:
            logger.info(f"User provided {len(additional_urls)} additional URLs")
        research = await researcher.research_brand(
            brand_name=brand_name,
            domain=domain,
            existing_info=existing_info,
            include_perplexity=True,  # Enable Perplexity research
            additional_urls=additional_urls  # User-provided URLs for small sites
        )

        logger.info(f"Research complete: {len(research.pages_crawled)} pages crawled")
        logger.info(f"Found: {len(research.products)} products, {len(research.features)} features, "
                   f"{len(research.customer_industries)} industries, {len(research.testimonials)} testimonials")
        logger.info(f"Perplexity queries: {research.perplexity_queries_made}, "
                   f"Citations: {len(research.perplexity_citations)}")

        # Override with provided industry if research didn't find one
        if industry and not research.industry:
            research.industry = industry

    finally:
        await researcher.close()

    # Generate questions based on comprehensive research
    generator = SmartQuestionGenerator()
    questions = await generator.generate_questions(
        brand_research=research,
        competitors=competitors or [],
        num_questions=num_questions
    )

    logger.info(f"Generated {len(questions)} questions")

    if return_research:
        # Build comprehensive research summary
        research_summary = {
            # Website research
            "website_pages_crawled": len(research.pages_crawled),
            "products_found": len(research.products),
            "features_found": len(research.features),
            "testimonials_found": len(research.testimonials),

            # Perplexity research
            "perplexity_queries_made": research.perplexity_queries_made,
            "citations_found": len(research.perplexity_citations),
            "market_position": research.market_position,
            "customer_sentiment": research.customer_sentiment,

            # Combined insights
            "competitors_discovered": research.competitors_mentioned[:10],
            "customer_industries": research.customer_industries[:10],
            "customer_pain_points": research.customer_pain_points[:10],
            "industry_trends": research.industry_trends[:8],

            # Quality
            "research_quality_score": round(research.research_quality_score, 2),

            # Sources
            "sources": {
                "website": research.domain,
                "perplexity_citations": research.perplexity_citations[:10]
            }
        }
        return SmartGenerationResult(questions=questions, research_summary=research_summary)

    return questions
