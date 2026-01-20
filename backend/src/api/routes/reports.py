"""
Report generation API routes.
"""

from datetime import date, timedelta
from typing import Optional
from uuid import UUID
import io

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.user import User
from ...models.brand import Brand
from ...models.analysis import DailyMetrics
from ..deps import get_current_user

router = APIRouter()


@router.get("/brand/{brand_id}/summary")
async def get_report_summary(
    brand_id: UUID,
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a summary report for a brand."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get metrics for the period
    result = await db.execute(
        select(DailyMetrics)
        .where(
            DailyMetrics.brand_id == brand_id,
            DailyMetrics.date >= start_date
        )
        .order_by(DailyMetrics.date.desc())
    )
    metrics = result.scalars().all()

    if not metrics:
        return {
            "brand_name": brand.name,
            "period_start": str(start_date),
            "period_end": str(date.today()),
            "summary": {
                "avg_visibility_score": 0,
                "avg_sentiment": 0,
                "total_mentions": 0,
                "avg_share_of_voice": 0,
            },
            "highlights": [],
            "recommendations": [
                "Start by generating questions for your brand",
                "Run analysis across AI platforms to gather data"
            ]
        }

    # Calculate averages
    visibility_scores = [m.visibility_score for m in metrics if m.visibility_score]
    sentiment_scores = [m.sentiment_avg for m in metrics if m.sentiment_avg is not None]
    sov_scores = [m.share_of_voice for m in metrics if m.share_of_voice]

    avg_visibility = sum(visibility_scores) / len(visibility_scores) if visibility_scores else 0
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    total_mentions = sum(m.mention_count or 0 for m in metrics)
    avg_sov = sum(sov_scores) / len(sov_scores) if sov_scores else 0

    # Generate highlights
    highlights = []
    if avg_visibility > 70:
        highlights.append("Strong AI visibility across platforms")
    elif avg_visibility < 30:
        highlights.append("Low visibility in AI search results - optimization needed")

    if avg_sentiment > 0.3:
        highlights.append("Positive sentiment in AI responses")
    elif avg_sentiment < -0.3:
        highlights.append("Negative sentiment detected - review brand perception")

    # Generate recommendations
    recommendations = []
    if avg_visibility < 50:
        recommendations.append("Improve website content for better AI citations")
        recommendations.append("Create authoritative content that AI models can reference")

    if avg_sentiment < 0:
        recommendations.append("Address negative feedback and improve product/service quality")
        recommendations.append("Monitor competitor mentions for comparison insights")

    if total_mentions < 10:
        recommendations.append("Increase brand awareness through content marketing")

    return {
        "brand_name": brand.name,
        "period_start": str(start_date),
        "period_end": str(date.today()),
        "days_analyzed": days,
        "summary": {
            "avg_visibility_score": round(avg_visibility, 2),
            "avg_sentiment": round(avg_sentiment, 3),
            "total_mentions": total_mentions,
            "avg_share_of_voice": round(avg_sov, 2),
        },
        "competitors_tracked": len(brand.competitors),
        "highlights": highlights,
        "recommendations": recommendations
    }


@router.get("/brand/{brand_id}/export/csv")
async def export_report_csv(
    brand_id: UUID,
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export brand metrics as CSV."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get metrics
    result = await db.execute(
        select(DailyMetrics)
        .where(
            DailyMetrics.brand_id == brand_id,
            DailyMetrics.date >= start_date
        )
        .order_by(DailyMetrics.date.asc())
    )
    metrics = result.scalars().all()

    # Generate CSV
    csv_content = io.StringIO()
    csv_content.write("Date,Visibility Score,Sentiment,Mentions,Share of Voice,Total Queries,Successful Queries\n")

    for m in metrics:
        csv_content.write(
            f"{m.date},{m.visibility_score or ''},{m.sentiment_avg or ''},{m.mention_count or 0},"
            f"{m.share_of_voice or ''},{m.total_queries or 0},{m.successful_queries or 0}\n"
        )

    csv_content.seek(0)

    return StreamingResponse(
        iter([csv_content.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={brand.name.replace(' ', '_')}_report_{date.today()}.csv"
        }
    )


@router.get("/brand/{brand_id}/export/json")
async def export_report_json(
    brand_id: UUID,
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export brand metrics as JSON."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    start_date = date.today() - timedelta(days=days)

    # Get metrics
    result = await db.execute(
        select(DailyMetrics)
        .where(
            DailyMetrics.brand_id == brand_id,
            DailyMetrics.date >= start_date
        )
        .order_by(DailyMetrics.date.asc())
    )
    metrics = result.scalars().all()

    return {
        "brand": {
            "id": str(brand.id),
            "name": brand.name,
            "domain": brand.domain,
            "industry": brand.industry,
            "keywords": brand.keywords,
            "competitors": [
                {"name": c.name, "domain": c.domain}
                for c in brand.competitors
            ]
        },
        "period": {
            "start": str(start_date),
            "end": str(date.today()),
            "days": days
        },
        "metrics": [
            {
                "date": str(m.date),
                "visibility_score": m.visibility_score,
                "sentiment_avg": m.sentiment_avg,
                "mention_count": m.mention_count,
                "share_of_voice": m.share_of_voice,
                "platform_breakdown": m.platform_breakdown,
                "top_citations": m.top_citations,
                "total_queries": m.total_queries,
                "successful_queries": m.successful_queries
            }
            for m in metrics
        ]
    }
