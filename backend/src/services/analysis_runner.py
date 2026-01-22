"""
Analysis runner service - orchestrates querying AI platforms and analyzing responses.
"""

import asyncio
import logging
import re
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import AsyncSessionLocal
from ..models.brand import Brand
from ..models.question import Question
from ..models.execution import QueryExecution
from ..models.analysis import AnalysisResult, DailyMetrics
from ..adapters.base import BaseAIAdapter, AIResponse
from ..adapters.chatgpt import ChatGPTAdapter
from ..adapters.claude import ClaudeAdapter
from ..adapters.perplexity import PerplexityAdapter
from ..adapters.gemini import GeminiAdapter
from ..nlp.sentiment import SentimentAnalyzer, AspectSentiment, DetailedSentimentResult
from ..nlp.citation_parser import CitationParser, Citation, EnhancedCitation, EnhancedCitationStats
from ..nlp.entity_extraction import EntityExtractor, ContextualMention, MentionType
from ..config import settings


class AnalysisRunner:
    """Orchestrates the analysis process for a brand."""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.citation_parser = CitationParser()
        self.entity_extractor = EntityExtractor()
        self.adapters: Dict[str, BaseAIAdapter] = {}
        self._init_adapters()

    def _init_adapters(self):
        """Initialize available AI adapters based on configured API keys."""
        # Use print for immediate output to logs
        import os
        print(f"[AnalysisRunner] Initializing AI adapters...")
        print(f"[AnalysisRunner] OPENAI_API_KEY from settings: {bool(settings.OPENAI_API_KEY)}")
        print(f"[AnalysisRunner] OPENAI_API_KEY from env: {bool(os.environ.get('OPENAI_API_KEY'))}")
        print(f"[AnalysisRunner] PERPLEXITY_API_KEY from settings: {bool(settings.PERPLEXITY_API_KEY)}")
        print(f"[AnalysisRunner] PERPLEXITY_API_KEY from env: {bool(os.environ.get('PERPLEXITY_API_KEY'))}")

        if settings.OPENAI_API_KEY:
            self.adapters["chatgpt"] = ChatGPTAdapter()
            print("[AnalysisRunner] ChatGPT adapter initialized")
        if settings.ANTHROPIC_API_KEY:
            self.adapters["claude"] = ClaudeAdapter()
            print("[AnalysisRunner] Claude adapter initialized")
        if settings.PERPLEXITY_API_KEY:
            self.adapters["perplexity"] = PerplexityAdapter()
            print("[AnalysisRunner] Perplexity adapter initialized")
        if settings.GOOGLE_AI_API_KEY:
            self.adapters["gemini"] = GeminiAdapter()
            print("[AnalysisRunner] Gemini adapter initialized")

        print(f"[AnalysisRunner] Available adapters: {list(self.adapters.keys())}")

    async def run_analysis(
        self,
        brand_id: UUID,
        platforms: Optional[List[str]] = None,
        max_questions: int = 10
    ) -> Dict[str, Any]:
        """
        Run analysis for a brand.

        Args:
            brand_id: Brand to analyze
            platforms: Specific platforms to query (defaults to all available)
            max_questions: Maximum questions to process

        Returns:
            Summary of analysis results
        """
        async with AsyncSessionLocal() as db:
            # Get brand with questions and competitors
            result = await db.execute(
                select(Brand)
                .options(
                    selectinload(Brand.questions),
                    selectinload(Brand.competitors)
                )
                .where(Brand.id == brand_id)
            )
            brand = result.scalar_one_or_none()

            if not brand:
                return {"error": "Brand not found"}

            # Get active questions
            questions = [q for q in brand.questions if q.is_active][:max_questions]

            if not questions:
                return {"error": "No active questions for this brand"}

            # Determine platforms to use
            if platforms:
                selected_platforms = [p for p in platforms if p in self.adapters]
            else:
                selected_platforms = list(self.adapters.keys())

            if not selected_platforms:
                print(f"[AnalysisRunner] No AI platforms configured. Available adapters: {list(self.adapters.keys())}")
                print(f"[AnalysisRunner] Requested platforms: {platforms}")
                return {"error": "No AI platforms configured. Please add API keys."}

            logger.info(f"Starting analysis with platforms: {selected_platforms}")

            results = {
                "brand_id": str(brand_id),
                "brand_name": brand.name,
                "questions_processed": 0,
                "executions": [],
                "platforms": selected_platforms
            }

            # Process each question
            for question in questions:
                logger.info(f"Processing question: {question.question_text[:50]}...")
                for platform in selected_platforms:
                    try:
                        logger.info(f"Querying {platform} for question {question.id}")
                        execution_result = await self._process_question(
                            db, brand, question, platform
                        )
                        results["executions"].append(execution_result)
                        logger.info(f"Completed {platform} query: mentioned={execution_result.get('brand_mentioned')}")
                    except Exception as e:
                        logger.error(f"Error processing {platform} for question {question.id}: {str(e)}", exc_info=True)
                        results["executions"].append({
                            "question_id": str(question.id),
                            "platform": platform,
                            "error": str(e)
                        })

                results["questions_processed"] += 1

            # Update daily metrics
            await self._update_daily_metrics(db, brand_id)

            await db.commit()
            return results

    async def _process_question(
        self,
        db: AsyncSession,
        brand: Brand,
        question: Question,
        platform: str
    ) -> Dict[str, Any]:
        """Process a single question against a platform."""
        adapter = self.adapters[platform]

        # Execute query
        response = await adapter.execute_query(question.question_text)

        # Create execution record
        # Store tokens in response_metadata since tokens_used is not a column
        metadata = response.raw_response or {}
        if response.tokens_used:
            metadata["tokens_used"] = response.tokens_used

        execution = QueryExecution(
            question_id=question.id,
            platform=platform,
            raw_response=response.content,
            response_metadata=metadata,
            status="completed" if response.content else "failed",
            response_time_ms=response.response_time_ms
        )
        db.add(execution)
        await db.flush()  # Get execution ID

        # Analyze response
        analysis = await self._analyze_response(
            db, execution.id, brand, response.content
        )

        return {
            "question_id": str(question.id),
            "question": question.question_text,
            "platform": platform,
            "execution_id": str(execution.id),
            "brand_mentioned": analysis.brand_mentioned if analysis else False,
            "mention_count": analysis.mention_count if analysis else 0,
            "sentiment": analysis.sentiment if analysis else None,
            "sentiment_score": analysis.sentiment_score if analysis else 0,
            "position": analysis.position if analysis else None,
            "total_in_list": analysis.total_recommendations if analysis else None,
            "citation_count": analysis.citation_count if analysis else 0,
            "competitor_mentions": analysis.competitor_mentions if analysis else {}
        }

    async def _analyze_response(
        self,
        db: AsyncSession,
        execution_id: UUID,
        brand: Brand,
        content: str
    ) -> Optional[AnalysisResult]:
        """Analyze AI response for brand mentions, competitors, citations, and sentiment."""
        if not content:
            return None

        # Extract brand mentions with context
        brand_mention_data = self.entity_extractor.extract_brand_mentions(
            content, brand.name, context_window=100
        )
        brand_mentioned = brand_mention_data.count > 0
        mention_count = brand_mention_data.count

        # Store mention contexts (up to 5)
        mention_contexts = [
            {"text": ctx, "position": pos}
            for ctx, pos in zip(brand_mention_data.contexts[:5], brand_mention_data.positions[:5])
        ]

        # Analyze sentiment around brand mentions
        sentiment = "neutral"
        sentiment_score = 0.0
        sentiment_confidence = 0.0

        if brand_mentioned:
            sentiment_result = self.sentiment_analyzer.analyze_mention(
                content, brand.name
            )
            sentiment = sentiment_result.label
            sentiment_score = sentiment_result.score
            sentiment_confidence = getattr(sentiment_result, 'confidence', 0.0)

        # Find position in lists (if applicable)
        position = self._find_brand_position(content, brand.name)

        # Count total recommendations in list
        total_recommendations = self.entity_extractor.count_total_recommendations(content)

        # Basic citation analysis
        citation_stats = self.citation_parser.parse_all_citations(content)
        citations = [
            {"url": c.url, "domain": c.domain, "title": c.title}
            for c in citation_stats.citations
        ]
        citation_count = citation_stats.total_citations

        # Get competitor names for analysis
        competitor_names = []
        if hasattr(brand, 'competitors') and brand.competitors:
            competitor_names = [c.name for c in brand.competitors]

        # Extract competitor mentions
        competitor_mentions = {}
        if competitor_names:
            comp_mention_data = self.entity_extractor.extract_competitor_mentions(
                content, competitor_names, context_window=100
            )
            for comp_name, mention_info in comp_mention_data.items():
                competitor_mentions[comp_name] = {
                    "count": mention_info.count,
                    "contexts": mention_info.contexts[:3]  # Store up to 3 contexts
                }

        # === ENHANCED ANALYSIS (Phases 2-4) ===

        # Phase 2: Enhanced citation analysis with source attribution
        enhanced_citation_stats = self.citation_parser.get_enhanced_citation_stats(
            content, citation_stats.citations, brand.name
        )
        brand_attributed_citations = enhanced_citation_stats.brand_attributed_count
        citation_quality = {
            "avg_authority": enhanced_citation_stats.avg_authority_score,
            "source_types": enhanced_citation_stats.source_type_breakdown
        }

        # Phase 3: Contextual mention analysis
        contextual_mentions = self.entity_extractor.extract_contextual_mentions(
            content, brand.name, competitor_names
        )
        mention_summary = self.entity_extractor.get_mention_type_summary(contextual_mentions)
        mention_type_breakdown = mention_summary.get("by_type", {})
        comparison_stats = mention_summary.get("comparison_stats", {})

        # Phase 4: Aspect-based sentiment analysis
        detailed_sentiment = self.sentiment_analyzer.analyze_with_aspects(
            content, brand.name
        )
        aspect_sentiments = [
            {
                "aspect": asp.aspect,
                "label": asp.label,
                "score": asp.score,
                "evidence": asp.evidence[:2],  # Store top 2 evidence snippets
                "mention_count": asp.mention_count
            }
            for asp in detailed_sentiment.aspects
        ]
        dominant_aspect = detailed_sentiment.dominant_aspect

        # Create analysis result with enhanced data
        analysis = AnalysisResult(
            execution_id=execution_id,
            brand_mentioned=brand_mentioned,
            mention_count=mention_count,
            mention_contexts=mention_contexts,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            sentiment_confidence=sentiment_confidence,
            position=position,
            total_recommendations=total_recommendations,
            citations=citations,
            citation_count=citation_count,
            competitor_mentions=competitor_mentions,
            # Enhanced fields
            brand_attributed_citations=brand_attributed_citations,
            citation_quality=citation_quality,
            mention_type_breakdown=mention_type_breakdown,
            comparison_stats=comparison_stats,
            aspect_sentiments=aspect_sentiments,
            dominant_aspect=dominant_aspect
        )
        db.add(analysis)

        return analysis

    def _find_brand_position(self, content: str, brand_name: str) -> Optional[int]:
        """Find brand's position in numbered lists."""
        # Look for numbered list patterns
        # Match patterns like "1. Brand", "1) Brand", "#1: Brand"
        list_patterns = [
            r'(\d+)\.\s+' + re.escape(brand_name),
            r'(\d+)\)\s+' + re.escape(brand_name),
            r'#(\d+)[:\s]+' + re.escape(brand_name),
            r'(\d+)\s*[-–]\s*' + re.escape(brand_name),
        ]

        for pattern in list_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    async def _update_daily_metrics(
        self,
        db: AsyncSession,
        brand_id: UUID
    ):
        """Update or create daily metrics for the brand with competitor analysis."""
        today = date.today()

        # Get today's executions and analyses
        result = await db.execute(
            select(QueryExecution)
            .join(Question)
            .options(selectinload(QueryExecution.analysis))
            .where(
                Question.brand_id == brand_id,
                QueryExecution.executed_at >= datetime.combine(today, datetime.min.time())
            )
        )
        executions = result.scalars().all()

        if not executions:
            return

        # Calculate metrics
        total_mentions = 0
        sentiment_scores = []
        platform_data = {}
        all_citations = []
        competitor_totals = {}
        positions = []

        for execution in executions:
            if execution.analysis:
                if execution.analysis.brand_mentioned:
                    total_mentions += execution.analysis.mention_count or 0
                if execution.analysis.sentiment_score is not None:
                    sentiment_scores.append(execution.analysis.sentiment_score)
                if execution.analysis.position is not None:
                    positions.append(execution.analysis.position)

                # Aggregate competitor mentions for Share of Voice
                if execution.analysis.competitor_mentions:
                    for comp_name, data in execution.analysis.competitor_mentions.items():
                        if isinstance(data, dict):
                            count = data.get("count", 0)
                        else:
                            count = 0
                        competitor_totals[comp_name] = competitor_totals.get(comp_name, 0) + count

                # Collect all citations for ranking
                if execution.analysis.citations:
                    for citation in execution.analysis.citations:
                        if isinstance(citation, dict):
                            all_citations.append(Citation(
                                url=citation.get("url", ""),
                                domain=citation.get("domain", ""),
                                title=citation.get("title")
                            ))

                # Track per platform
                platform = execution.platform
                if platform not in platform_data:
                    platform_data[platform] = {
                        "mentions": 0,
                        "queries": 0,
                        "sentiment_scores": [],
                        "positions": []
                    }
                platform_data[platform]["queries"] += 1
                if execution.analysis.brand_mentioned:
                    platform_data[platform]["mentions"] += execution.analysis.mention_count or 0
                if execution.analysis.sentiment_score is not None:
                    platform_data[platform]["sentiment_scores"].append(
                        execution.analysis.sentiment_score
                    )
                if execution.analysis.position is not None:
                    platform_data[platform]["positions"].append(execution.analysis.position)

        # Calculate visibility score (0-100)
        total_queries = len(executions)
        mention_rate = total_mentions / total_queries if total_queries > 0 else 0
        sentiment_avg = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        position_avg = sum(positions) / len(positions) if positions else None

        # Visibility = mention_rate * 50 + sentiment_bonus * 50
        visibility_score = min(100, mention_rate * 50 + (sentiment_avg + 1) * 25)

        # Calculate Share of Voice (brand mentions vs competitor mentions)
        total_competitor_mentions = sum(competitor_totals.values())
        total_all_mentions = total_mentions + total_competitor_mentions
        share_of_voice = (total_mentions / total_all_mentions * 100) if total_all_mentions > 0 else 0

        # Rank top citation sources
        top_citations = self.citation_parser.rank_citation_sources(all_citations)[:10]

        # Calculate platform breakdown with position averages
        platform_breakdown = {}
        for platform, data in platform_data.items():
            p_mention_rate = data["mentions"] / data["queries"] if data["queries"] > 0 else 0
            p_sentiment = sum(data["sentiment_scores"]) / len(data["sentiment_scores"]) if data["sentiment_scores"] else 0
            p_position = sum(data["positions"]) / len(data["positions"]) if data["positions"] else None
            platform_breakdown[platform] = {
                "mentions": data["mentions"],
                "queries": data["queries"],
                "visibility_score": min(100, p_mention_rate * 50 + (p_sentiment + 1) * 25),
                "sentiment_avg": p_sentiment,
                "position_avg": p_position
            }

        # Update or create daily metrics
        result = await db.execute(
            select(DailyMetrics).where(
                DailyMetrics.brand_id == brand_id,
                DailyMetrics.date == today
            )
        )
        daily_metrics = result.scalar_one_or_none()

        if daily_metrics:
            daily_metrics.visibility_score = visibility_score
            daily_metrics.sentiment_avg = sentiment_avg
            daily_metrics.mention_count = total_mentions
            daily_metrics.share_of_voice = share_of_voice
            daily_metrics.platform_breakdown = platform_breakdown
            daily_metrics.top_citations = top_citations
            daily_metrics.total_queries = total_queries
            daily_metrics.successful_queries = sum(1 for e in executions if e.status == "completed")
        else:
            daily_metrics = DailyMetrics(
                brand_id=brand_id,
                date=today,
                visibility_score=visibility_score,
                sentiment_avg=sentiment_avg,
                mention_count=total_mentions,
                share_of_voice=share_of_voice,
                platform_breakdown=platform_breakdown,
                top_citations=top_citations,
                total_queries=total_queries,
                successful_queries=sum(1 for e in executions if e.status == "completed")
            )
            db.add(daily_metrics)
