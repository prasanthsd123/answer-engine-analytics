"""
Analysis runner service - orchestrates querying AI platforms and analyzing responses.
"""

import asyncio
import re
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

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
from ..nlp.sentiment import SentimentAnalyzer
from ..nlp.citation_parser import CitationParser
from ..config import settings


class AnalysisRunner:
    """Orchestrates the analysis process for a brand."""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.citation_parser = CitationParser()
        self.adapters: Dict[str, BaseAIAdapter] = {}
        self._init_adapters()

    def _init_adapters(self):
        """Initialize available AI adapters based on configured API keys."""
        if settings.OPENAI_API_KEY:
            self.adapters["chatgpt"] = ChatGPTAdapter()
        if settings.ANTHROPIC_API_KEY:
            self.adapters["claude"] = ClaudeAdapter()
        if settings.PERPLEXITY_API_KEY:
            self.adapters["perplexity"] = PerplexityAdapter()
        if settings.GOOGLE_AI_API_KEY:
            self.adapters["gemini"] = GeminiAdapter()

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
            # Get brand with questions
            result = await db.execute(
                select(Brand)
                .options(selectinload(Brand.questions))
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
                return {"error": "No AI platforms configured. Please add API keys."}

            results = {
                "brand_id": str(brand_id),
                "brand_name": brand.name,
                "questions_processed": 0,
                "executions": [],
                "platforms": selected_platforms
            }

            # Process each question
            for question in questions:
                for platform in selected_platforms:
                    try:
                        execution_result = await self._process_question(
                            db, brand, question, platform
                        )
                        results["executions"].append(execution_result)
                    except Exception as e:
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
        execution = QueryExecution(
            question_id=question.id,
            platform=platform,
            raw_response=response.content,
            response_metadata=response.raw_response,
            status="completed" if response.content else "failed",
            tokens_used=response.tokens_used,
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
            "sentiment": analysis.sentiment if analysis else None,
            "position": analysis.position if analysis else None
        }

    async def _analyze_response(
        self,
        db: AsyncSession,
        execution_id: UUID,
        brand: Brand,
        content: str
    ) -> Optional[AnalysisResult]:
        """Analyze AI response for brand mentions and sentiment."""
        if not content:
            return None

        # Check for brand mention
        brand_pattern = re.compile(re.escape(brand.name), re.IGNORECASE)
        mentions = brand_pattern.findall(content)
        brand_mentioned = len(mentions) > 0
        mention_count = len(mentions)

        # Analyze sentiment around brand mentions
        sentiment = "neutral"
        sentiment_score = 0.0

        if brand_mentioned:
            sentiment_result = self.sentiment_analyzer.analyze_mention(
                content, brand.name
            )
            sentiment = sentiment_result.label
            sentiment_score = sentiment_result.score

        # Find position in lists (if applicable)
        position = self._find_brand_position(content, brand.name)

        # Extract citations
        citations = self.citation_parser.extract_urls(content)

        # Create analysis result
        analysis = AnalysisResult(
            execution_id=execution_id,
            brand_mentioned=brand_mentioned,
            mention_count=mention_count,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            position=position,
            citations=citations
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
        """Update or create daily metrics for the brand."""
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

        for execution in executions:
            if execution.analysis:
                if execution.analysis.brand_mentioned:
                    total_mentions += execution.analysis.mention_count or 0
                if execution.analysis.sentiment_score is not None:
                    sentiment_scores.append(execution.analysis.sentiment_score)

                # Track per platform
                platform = execution.platform
                if platform not in platform_data:
                    platform_data[platform] = {
                        "mentions": 0,
                        "queries": 0,
                        "sentiment_scores": []
                    }
                platform_data[platform]["queries"] += 1
                if execution.analysis.brand_mentioned:
                    platform_data[platform]["mentions"] += execution.analysis.mention_count or 0
                if execution.analysis.sentiment_score is not None:
                    platform_data[platform]["sentiment_scores"].append(
                        execution.analysis.sentiment_score
                    )

        # Calculate visibility score (0-100)
        total_queries = len(executions)
        mention_rate = total_mentions / total_queries if total_queries > 0 else 0
        sentiment_avg = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        # Visibility = mention_rate * 50 + sentiment_bonus * 50
        visibility_score = min(100, mention_rate * 50 + (sentiment_avg + 1) * 25)

        # Calculate platform breakdown
        platform_breakdown = {}
        for platform, data in platform_data.items():
            p_mention_rate = data["mentions"] / data["queries"] if data["queries"] > 0 else 0
            p_sentiment = sum(data["sentiment_scores"]) / len(data["sentiment_scores"]) if data["sentiment_scores"] else 0
            platform_breakdown[platform] = {
                "mentions": data["mentions"],
                "queries": data["queries"],
                "visibility_score": min(100, p_mention_rate * 50 + (p_sentiment + 1) * 25),
                "sentiment_avg": p_sentiment
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
            daily_metrics.platform_breakdown = platform_breakdown
        else:
            daily_metrics = DailyMetrics(
                brand_id=brand_id,
                date=today,
                visibility_score=visibility_score,
                sentiment_avg=sentiment_avg,
                mention_count=total_mentions,
                share_of_voice=0,  # Would need competitor data
                platform_breakdown=platform_breakdown
            )
            db.add(daily_metrics)
