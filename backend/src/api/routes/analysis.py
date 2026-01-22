"""
Analysis and metrics API routes.
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from ...database import get_db
from ...models.user import User
from ...models.brand import Brand
from ...models.question import Question
from ...models.execution import QueryExecution
from ...models.analysis import AnalysisResult, DailyMetrics
from ...schemas.analysis import (
    AnalysisResponse, DailyMetricsResponse, VisibilityOverview,
    TrendResponse, TrendDataPoint, CompetitorAnalysisResponse, CompetitorComparison,
    PlatformMetrics
)
from ..deps import get_current_user

router = APIRouter()


@router.get("/brand/{brand_id}/overview", response_model=VisibilityOverview)
async def get_visibility_overview(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get high-level visibility overview for a brand."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Get latest daily metrics
    result = await db.execute(
        select(DailyMetrics)
        .where(DailyMetrics.brand_id == brand_id)
        .order_by(DailyMetrics.date.desc())
        .limit(2)
    )
    metrics = result.scalars().all()

    if not metrics:
        # Return default values if no metrics yet
        return VisibilityOverview(
            brand_id=brand_id,
            brand_name=brand.name,
            visibility_score=0,
            visibility_change=0,
            sentiment_score=0,
            sentiment_label="neutral",
            share_of_voice=0,
            total_mentions=0,
            platform_scores={}
        )

    current_metrics = metrics[0]
    previous_metrics = metrics[1] if len(metrics) > 1 else None

    # Calculate change
    visibility_change = 0
    if previous_metrics and previous_metrics.visibility_score:
        visibility_change = (current_metrics.visibility_score or 0) - previous_metrics.visibility_score

    # Determine sentiment label
    sentiment_score = current_metrics.sentiment_avg or 0
    if sentiment_score > 0.2:
        sentiment_label = "positive"
    elif sentiment_score < -0.2:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"

    # Extract platform scores
    platform_scores = {}
    if current_metrics.platform_breakdown:
        for platform, data in current_metrics.platform_breakdown.items():
            if isinstance(data, dict) and "visibility_score" in data:
                platform_scores[platform] = data["visibility_score"]

    return VisibilityOverview(
        brand_id=brand_id,
        brand_name=brand.name,
        visibility_score=current_metrics.visibility_score or 0,
        visibility_change=visibility_change,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        share_of_voice=current_metrics.share_of_voice or 0,
        total_mentions=current_metrics.mention_count or 0,
        platform_scores=platform_scores
    )


@router.get("/brand/{brand_id}/trends", response_model=TrendResponse)
async def get_metric_trends(
    brand_id: UUID,
    metric: str = Query(..., description="Metric to trend: visibility, sentiment, mentions, share_of_voice"),
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trend data for a specific metric over time."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(DailyMetrics)
        .where(
            DailyMetrics.brand_id == brand_id,
            DailyMetrics.date >= start_date
        )
        .order_by(DailyMetrics.date.asc())
    )
    metrics = result.scalars().all()

    # Map metric name to field
    metric_map = {
        "visibility": "visibility_score",
        "sentiment": "sentiment_avg",
        "mentions": "mention_count",
        "share_of_voice": "share_of_voice"
    }

    if metric not in metric_map:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    field_name = metric_map[metric]

    data_points = [
        TrendDataPoint(
            date=m.date,
            value=getattr(m, field_name) or 0
        )
        for m in metrics
    ]

    return TrendResponse(
        metric_name=metric,
        data_points=data_points,
        period_start=start_date,
        period_end=date.today()
    )


@router.get("/brand/{brand_id}/platform/{platform}", response_model=PlatformMetrics)
async def get_platform_metrics(
    brand_id: UUID,
    platform: str,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed metrics for a specific AI platform."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get executions for this platform
    result = await db.execute(
        select(QueryExecution)
        .join(Question)
        .options(selectinload(QueryExecution.analysis))
        .where(
            Question.brand_id == brand_id,
            QueryExecution.platform == platform,
            QueryExecution.executed_at >= start_date
        )
    )
    executions = result.scalars().all()

    total_queries = len(executions)
    successful_queries = sum(1 for e in executions if e.status == "completed")

    mentions = 0
    sentiment_scores = []
    positions = []

    for execution in executions:
        if execution.analysis:
            if execution.analysis.brand_mentioned:
                mentions += execution.analysis.mention_count or 0
            if execution.analysis.sentiment_score is not None:
                sentiment_scores.append(execution.analysis.sentiment_score)
            if execution.analysis.position is not None:
                positions.append(execution.analysis.position)

    sentiment_avg = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
    position_avg = sum(positions) / len(positions) if positions else None

    # Calculate visibility score (simplified)
    visibility_score = None
    if total_queries > 0:
        mention_rate = mentions / total_queries if total_queries else 0
        visibility_score = min(100, mention_rate * 50 + (sentiment_avg + 1) * 25 if sentiment_avg else mention_rate * 50)

    return PlatformMetrics(
        platform=platform,
        mentions=mentions,
        sentiment_avg=sentiment_avg,
        position_avg=position_avg,
        visibility_score=visibility_score,
        total_queries=total_queries,
        successful_queries=successful_queries
    )


@router.get("/brand/{brand_id}/competitors", response_model=CompetitorAnalysisResponse)
async def get_competitor_analysis(
    brand_id: UUID,
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get competitor comparison analysis."""
    # Get brand with competitors
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get latest metrics for brand
    result = await db.execute(
        select(DailyMetrics)
        .where(DailyMetrics.brand_id == brand_id)
        .order_by(DailyMetrics.date.desc())
        .limit(1)
    )
    brand_metrics = result.scalar_one_or_none()

    brand_comparison = CompetitorComparison(
        name=brand.name,
        visibility_score=brand_metrics.visibility_score if brand_metrics else 0,
        sentiment_score=brand_metrics.sentiment_avg if brand_metrics else 0,
        mention_count=brand_metrics.mention_count if brand_metrics else 0,
        share_of_voice=brand_metrics.share_of_voice if brand_metrics else 0
    )

    # For competitors, we'd need to track them separately or extract from analysis results
    # This is a simplified version
    competitors = []
    for comp in brand.competitors:
        competitors.append(CompetitorComparison(
            name=comp.name,
            visibility_score=0,  # Would need separate tracking
            sentiment_score=0,
            mention_count=0,
            share_of_voice=0
        ))

    return CompetitorAnalysisResponse(
        brand=brand_comparison,
        competitors=competitors,
        period_start=start_date,
        period_end=date.today()
    )


@router.get("/execution/{execution_id}", response_model=AnalysisResponse)
async def get_execution_analysis(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis results for a specific query execution."""
    result = await db.execute(
        select(AnalysisResult)
        .join(QueryExecution)
        .join(Question)
        .join(Brand)
        .where(
            AnalysisResult.execution_id == execution_id,
            Brand.user_id == current_user.id
        )
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis


@router.post("/brand/{brand_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(
    brand_id: UUID,
    background_tasks: BackgroundTasks,
    platforms: Optional[List[str]] = Query(None, description="Platforms to query"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger analysis for a brand (runs queries across AI platforms)."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    # Handle comma-separated platforms (in case frontend sends "chatgpt,perplexity" as single string)
    parsed_platforms = None
    if platforms:
        parsed_platforms = []
        for p in platforms:
            if ',' in p:
                parsed_platforms.extend([x.strip() for x in p.split(',')])
            else:
                parsed_platforms.append(p)
        logger.info(f"Parsed platforms: {parsed_platforms}")

    from ...services.analysis_runner import AnalysisRunner

    # Run analysis in background using asyncio.create_task
    async def run_analysis_task():
        try:
            logger.info(f"Starting analysis for brand {brand_id} on platforms {parsed_platforms}")
            runner = AnalysisRunner()
            results = await runner.run_analysis(brand_id, parsed_platforms)
            logger.info(f"Analysis completed for brand {brand_id}: {results}")
        except Exception as e:
            logger.error(f"Analysis failed for brand {brand_id}: {str(e)}", exc_info=True)

    # Use asyncio.create_task for proper async execution
    asyncio.create_task(run_analysis_task())

    return {
        "message": "Analysis started",
        "brand_id": str(brand_id),
        "platforms": platforms or ["chatgpt", "claude", "perplexity", "gemini"],
        "status": "running"
    }


@router.post("/brand/{brand_id}/run-sync")
async def run_analysis_sync(
    brand_id: UUID,
    platforms: Optional[List[str]] = Query(None, description="Platforms to query"),
    max_questions: int = Query(5, ge=1, le=20, description="Max questions to process"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run analysis synchronously and return results (for testing/debugging)."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Brand not found")

    from ...services.analysis_runner import AnalysisRunner

    runner = AnalysisRunner()
    results = await runner.run_analysis(brand_id, platforms, max_questions)

    return results


@router.get("/brand/{brand_id}/detailed")
async def get_detailed_analysis(
    brand_id: UUID,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed per-question analysis with competitor mentions and citations.

    Returns breakdown by question showing:
    - Platform results (ChatGPT, Perplexity, etc.)
    - Mention counts and positions
    - Competitor mentions
    - Citation sources
    """
    # Get brand with competitors
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get all executions with analysis for this brand
    result = await db.execute(
        select(QueryExecution)
        .join(Question)
        .options(
            selectinload(QueryExecution.analysis),
            selectinload(QueryExecution.question)
        )
        .where(
            Question.brand_id == brand_id,
            QueryExecution.executed_at >= start_date
        )
        .order_by(QueryExecution.executed_at.desc())
    )
    executions = result.scalars().all()

    # Group by question
    questions_data = {}
    all_citations = []
    competitor_totals = {}
    total_brand_mentions = 0
    sentiment_scores = []
    positions = []

    for execution in executions:
        question = execution.question
        analysis = execution.analysis

        if not question:
            continue

        question_id = str(question.id)
        if question_id not in questions_data:
            questions_data[question_id] = {
                "question_id": question_id,
                "question_text": question.question_text,
                "category": question.category,
                "platforms": {}
            }

        if analysis:
            # Track platform data for this question
            questions_data[question_id]["platforms"][execution.platform] = {
                "brand_mentioned": analysis.brand_mentioned,
                "mention_count": analysis.mention_count or 0,
                "position": analysis.position,
                "total_in_list": analysis.total_recommendations,
                "sentiment": analysis.sentiment,
                "sentiment_score": analysis.sentiment_score,
                "competitor_mentions": analysis.competitor_mentions or {},
                "citations": analysis.citations or [],
                # Enhanced analysis fields
                "brand_attributed_citations": analysis.brand_attributed_citations or 0,
                "citation_quality": analysis.citation_quality or {},
                "mention_type_breakdown": analysis.mention_type_breakdown or {},
                "comparison_stats": analysis.comparison_stats or {},
                "aspect_sentiments": analysis.aspect_sentiments or [],
                "dominant_aspect": analysis.dominant_aspect
            }

            # Aggregate overall stats
            if analysis.brand_mentioned:
                total_brand_mentions += analysis.mention_count or 0
            if analysis.sentiment_score is not None:
                sentiment_scores.append(analysis.sentiment_score)
            if analysis.position is not None:
                positions.append(analysis.position)

            # Aggregate competitor mentions
            if analysis.competitor_mentions:
                for comp_name, data in analysis.competitor_mentions.items():
                    count = data.get("count", 0) if isinstance(data, dict) else 0
                    competitor_totals[comp_name] = competitor_totals.get(comp_name, 0) + count

            # Collect citations
            if analysis.citations:
                all_citations.extend(analysis.citations)

    # Calculate citation source ranking
    citation_domains = {}
    for citation in all_citations:
        domain = citation.get("domain", "") if isinstance(citation, dict) else ""
        if domain:
            citation_domains[domain] = citation_domains.get(domain, 0) + 1

    total_citations = sum(citation_domains.values())
    citation_sources = [
        {
            "domain": domain,
            "count": count,
            "percentage": round(count / total_citations * 100, 1) if total_citations > 0 else 0
        }
        for domain, count in sorted(citation_domains.items(), key=lambda x: x[1], reverse=True)
    ][:15]  # Top 15 sources

    # Calculate competitor summary with share of voice
    total_all_mentions = total_brand_mentions + sum(competitor_totals.values())
    competitor_summary = {}
    for comp_name, mentions in competitor_totals.items():
        competitor_summary[comp_name] = {
            "total_mentions": mentions,
            "share_of_voice": round(mentions / total_all_mentions * 100, 1) if total_all_mentions > 0 else 0
        }

    # Calculate overall summary
    total_executions = len(executions)
    mention_rate = total_brand_mentions / total_executions if total_executions > 0 else 0
    overall_sentiment = "neutral"
    if sentiment_scores:
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        if avg_sentiment > 0.2:
            overall_sentiment = "positive"
        elif avg_sentiment < -0.2:
            overall_sentiment = "negative"

    return {
        "brand_id": str(brand_id),
        "brand_name": brand.name,
        "summary": {
            "total_questions_analyzed": len(questions_data),
            "total_executions": total_executions,
            "overall_mention_rate": round(mention_rate, 2),
            "overall_sentiment": overall_sentiment,
            "overall_position_avg": round(sum(positions) / len(positions), 1) if positions else None,
            "brand_share_of_voice": round(total_brand_mentions / total_all_mentions * 100, 1) if total_all_mentions > 0 else 0
        },
        "by_question": list(questions_data.values()),
        "citation_sources": citation_sources,
        "competitor_summary": competitor_summary
    }


@router.get("/execution/{execution_id}/response")
async def get_execution_response(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get raw AI response with highlighted brand and competitor mentions.

    Returns the full response text with metadata about where the brand
    and competitors are mentioned.
    """
    import re

    # Get execution with analysis and related data
    result = await db.execute(
        select(QueryExecution)
        .options(
            selectinload(QueryExecution.analysis),
            selectinload(QueryExecution.question)
        )
        .join(Question)
        .join(Brand)
        .where(
            QueryExecution.id == execution_id,
            Brand.user_id == current_user.id
        )
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    # Get brand info for highlighting
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .join(Question)
        .where(Question.id == execution.question_id)
    )
    brand = result.scalar_one_or_none()

    response_text = execution.raw_response or ""
    brand_highlights = []
    competitor_highlights = []

    # Find brand mentions with positions
    if brand:
        brand_pattern = re.compile(re.escape(brand.name), re.IGNORECASE)
        for match in brand_pattern.finditer(response_text):
            context_start = max(0, match.start() - 50)
            context_end = min(len(response_text), match.end() + 50)
            brand_highlights.append({
                "start": match.start(),
                "end": match.end(),
                "text": match.group(),
                "context": response_text[context_start:context_end]
            })

        # Find competitor mentions
        if brand.competitors:
            for competitor in brand.competitors:
                comp_pattern = re.compile(re.escape(competitor.name), re.IGNORECASE)
                for match in comp_pattern.finditer(response_text):
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(response_text), match.end() + 50)
                    competitor_highlights.append({
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(),
                        "competitor_name": competitor.name,
                        "context": response_text[context_start:context_end]
                    })

    return {
        "execution_id": str(execution_id),
        "platform": execution.platform,
        "question": execution.question.question_text if execution.question else None,
        "executed_at": execution.executed_at.isoformat() if execution.executed_at else None,
        "response_text": response_text,
        "response_length": len(response_text),
        "brand_highlights": brand_highlights,
        "competitor_highlights": competitor_highlights,
        "citations_found": execution.analysis.citations if execution.analysis else [],
        "analysis_summary": {
            "brand_mentioned": execution.analysis.brand_mentioned if execution.analysis else False,
            "mention_count": execution.analysis.mention_count if execution.analysis else 0,
            "sentiment": execution.analysis.sentiment if execution.analysis else None,
            "position": execution.analysis.position if execution.analysis else None
        } if execution.analysis else None
    }
