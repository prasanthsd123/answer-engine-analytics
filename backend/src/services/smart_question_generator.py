"""
Smart Question Generator - Generates realistic user questions using AI.

This service creates questions that mimic how real users would search
for products/services in AI search engines like ChatGPT, Perplexity, etc.
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
    Generates realistic user questions based on brand research.

    Instead of simple templates, this uses AI to generate questions
    that real users would type when searching for solutions.
    """

    # Question intent categories
    INTENTS = {
        "discovery": "User discovering options in a category",
        "comparison": "User comparing specific products/brands",
        "evaluation": "User evaluating if a product is right for them",
        "feature": "User looking for specific capabilities",
        "problem_solving": "User trying to solve a specific problem",
        "review": "User looking for opinions and reviews",
        "pricing": "User researching costs and value"
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
        Generate realistic user questions based on brand research.

        Args:
            brand_research: Research data about the brand
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
        """Generate questions using AI."""

        # Build comprehensive context
        context = self._build_context(research, competitors)

        prompt = f"""You are a search behavior expert. Generate {num_questions} realistic questions that users would type into AI assistants (ChatGPT, Perplexity, Claude) when researching products in this space.

BRAND CONTEXT:
{context}

COMPETITORS: {', '.join(competitors) if competitors else 'Unknown'}

IMPORTANT GUIDELINES:
1. Questions should sound NATURAL - like real people searching
2. Include typos or casual language occasionally (e.g., "whats the best..." not "What is the best...")
3. Mix question types:
   - Generic category questions (don't always mention the brand)
   - Direct brand questions
   - Comparison questions
   - Problem-based questions ("how do I...", "best way to...")
4. Vary question length - some short, some detailed
5. Include questions a potential customer would ask BEFORE knowing about this brand

QUESTION CATEGORIES TO INCLUDE:
- discovery: Finding options in the category (30%)
- comparison: Comparing brands/products (20%)
- evaluation: Deciding if something is right for them (15%)
- feature: Looking for specific capabilities (15%)
- problem_solving: Solving specific problems (10%)
- review: Seeking opinions (5%)
- pricing: Understanding costs (5%)

Return a JSON array with this structure:
[
  {{
    "text": "the question text exactly as a user would type it",
    "category": "one of: discovery, comparison, evaluation, feature, problem_solving, review, pricing",
    "intent": "brief description of what the user wants",
    "priority": 1-5 (5 = most important for brand visibility)
  }}
]

Generate diverse, realistic questions. Return ONLY the JSON array."""

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # Higher temperature for diversity
            max_tokens=3000
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

    def _build_context(self, research: BrandResearch, competitors: List[str]) -> str:
        """Build context string for AI prompt."""
        parts = []

        parts.append(f"Brand: {research.brand_name}")

        if research.domain:
            parts.append(f"Website: {research.domain}")

        if research.industry:
            parts.append(f"Industry: {research.industry}")

        if research.description:
            parts.append(f"Description: {research.description}")

        if research.products:
            products_str = ", ".join(
                p["name"] if isinstance(p, dict) else str(p)
                for p in research.products[:5]
            )
            parts.append(f"Products/Services: {products_str}")

        if research.features:
            parts.append(f"Key Features: {', '.join(research.features[:10])}")

        if research.target_audience:
            parts.append(f"Target Audience: {research.target_audience}")

        if research.use_cases:
            parts.append(f"Use Cases: {', '.join(research.use_cases[:5])}")

        if research.differentiators:
            parts.append(f"Differentiators: {', '.join(research.differentiators[:5])}")

        if research.pricing_model:
            parts.append(f"Pricing Model: {research.pricing_model}")

        return "\n".join(parts)

    def _generate_template_questions(
        self,
        research: BrandResearch,
        competitors: List[str]
    ) -> List[GeneratedQuestion]:
        """Fallback template-based generation."""
        questions = []
        brand = research.brand_name
        industry = research.industry or "software"

        # Discovery questions
        discovery_templates = [
            f"what is the best {industry} tool",
            f"top {industry} solutions 2025",
            f"best {industry} for small business",
            f"recommended {industry} platforms",
        ]

        # Comparison questions
        comparison_templates = [
            f"{brand} vs competitors",
            f"is {brand} better than alternatives",
            f"{brand} compared to other options",
        ]
        if competitors:
            for comp in competitors[:3]:
                comparison_templates.append(f"{brand} vs {comp}")
                comparison_templates.append(f"{comp} or {brand} which is better")

        # Evaluation questions
        evaluation_templates = [
            f"is {brand} worth it",
            f"should I use {brand}",
            f"{brand} pros and cons",
            f"is {brand} good for beginners",
            f"{brand} honest review",
        ]

        # Feature questions
        feature_templates = [
            f"what does {brand} do",
            f"{brand} features",
            f"can {brand} do automation",
        ]
        if research.features:
            for feature in research.features[:3]:
                feature_templates.append(f"does {brand} have {feature}")

        # Problem-solving questions
        problem_templates = []
        if research.use_cases:
            for use_case in research.use_cases[:3]:
                problem_templates.append(f"best tool for {use_case}")
                problem_templates.append(f"how to {use_case}")

        # Add all questions
        for q in discovery_templates:
            questions.append(GeneratedQuestion(q, "discovery", "finding options", 4))
        for q in comparison_templates:
            questions.append(GeneratedQuestion(q, "comparison", "comparing options", 5))
        for q in evaluation_templates:
            questions.append(GeneratedQuestion(q, "evaluation", "deciding", 4))
        for q in feature_templates:
            questions.append(GeneratedQuestion(q, "feature", "capability check", 3))
        for q in problem_templates:
            questions.append(GeneratedQuestion(q, "problem_solving", "solving problem", 4))

        return questions[:20]  # Limit to 20


async def generate_smart_questions(
    brand_name: str,
    domain: Optional[str] = None,
    industry: Optional[str] = None,
    keywords: List[str] = None,
    products: List[Dict] = None,
    competitors: List[str] = None,
    num_questions: int = 20
) -> List[GeneratedQuestion]:
    """
    Convenience function to research a brand and generate questions.

    This is the main entry point for smart question generation.
    """
    from .brand_researcher import BrandResearcher

    # Research the brand
    researcher = BrandResearcher()
    try:
        existing_info = {
            "industry": industry,
            "keywords": keywords or [],
            "products": products or []
        }

        research = await researcher.research_brand(
            brand_name=brand_name,
            domain=domain,
            existing_info=existing_info
        )

        # Override with provided industry if research didn't find one
        if industry and not research.industry:
            research.industry = industry

    finally:
        await researcher.close()

    # Generate questions
    generator = SmartQuestionGenerator()
    questions = await generator.generate_questions(
        brand_research=research,
        competitors=competitors or [],
        num_questions=num_questions
    )

    return questions
