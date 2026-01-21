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
