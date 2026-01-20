"""
Worker for analyzing AI responses and calculating metrics.
"""

from datetime import datetime, date
from typing import Dict, List, Optional
from uuid import UUID

from celery import shared_task


@shared_task(bind=True)
def analyze_response_task(
    self,
    execution_id: str,
    brand_name: str,
    competitors: List[str],
    response_content: str
) -> dict:
    """
    Analyze an AI response for brand mentions, sentiment, and citations.

    Args:
        execution_id: UUID of the query execution
        brand_name: Primary brand name
        competitors: List of competitor names
        response_content: The AI response text

    Returns:
        Dict with analysis results
    """
    from ..nlp.sentiment import SentimentAnalyzer
    from ..nlp.entity_extraction import EntityExtractor
    from ..nlp.citation_parser import CitationParser

    sentiment_analyzer = SentimentAnalyzer()
    entity_extractor = EntityExtractor()
    citation_parser = CitationParser()

    # Extract brand mentions
    brand_mention = entity_extractor.extract_brand_mentions(
        response_content, brand_name
    )

    # Analyze sentiment around brand mentions
    sentiment_results = sentiment_analyzer.analyze_multiple_mentions(
        response_content, brand_name
    )
    aggregated_sentiment = sentiment_analyzer.aggregate_sentiment(sentiment_results)

    # Extract competitor mentions
    competitor_analysis = {}
    for comp in competitors:
        comp_mention = entity_extractor.extract_brand_mentions(
            response_content, comp
        )
        if comp_mention.count > 0:
            comp_sentiment = sentiment_analyzer.analyze_multiple_mentions(
                response_content, comp
            )
            agg_comp_sentiment = sentiment_analyzer.aggregate_sentiment(comp_sentiment)
            competitor_analysis[comp] = {
                "count": comp_mention.count,
                "sentiment": agg_comp_sentiment.label,
                "sentiment_score": agg_comp_sentiment.score
            }

    # Extract citations
    citation_stats = citation_parser.parse_all_citations(response_content)

    # Find brand position in list
    position = entity_extractor.find_brand_in_list(response_content, brand_name)
    total_recommendations = entity_extractor.count_total_recommendations(response_content)

    return {
        "execution_id": execution_id,
        "brand_mentioned": brand_mention.count > 0,
        "mention_count": brand_mention.count,
        "mention_contexts": [
            {"text": ctx, "position": i}
            for i, ctx in enumerate(brand_mention.contexts)
        ],
        "sentiment": aggregated_sentiment.label,
        "sentiment_score": aggregated_sentiment.score,
        "sentiment_confidence": aggregated_sentiment.confidence,
        "position": position,
        "total_recommendations": total_recommendations,
        "citations": [
            {"url": c.url, "domain": c.domain, "title": c.title}
            for c in citation_stats.citations
        ],
        "citation_count": citation_stats.total_citations,
        "top_citation_domains": citation_stats.domains,
        "competitor_mentions": competitor_analysis,
        "analyzed_at": datetime.utcnow().isoformat()
    }


@shared_task(bind=True)
def calculate_daily_metrics_task(
    self,
    brand_id: str,
    target_date: Optional[str] = None
) -> dict:
    """
    Calculate daily aggregated metrics for a brand.

    Args:
        brand_id: UUID of the brand
        target_date: Date to calculate metrics for (YYYY-MM-DD)

    Returns:
        Dict with daily metrics
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from ..config import settings
    from ..models.brand import Brand
    from ..models.question import Question
    from ..models.execution import QueryExecution
    from ..models.analysis import AnalysisResult, DailyMetrics
    from ..nlp.metrics import MetricsCalculator

    if target_date:
        metrics_date = date.fromisoformat(target_date)
    else:
        metrics_date = date.today()

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    with Session(engine) as db:
        # Get brand with competitors
        brand = db.query(Brand).filter(Brand.id == UUID(brand_id)).first()
        if not brand:
            return {"error": "Brand not found"}

        competitors = [c.name for c in brand.competitors]

        # Get all executions for the day
        executions = db.query(QueryExecution).join(Question).filter(
            Question.brand_id == UUID(brand_id),
            QueryExecution.executed_at >= datetime.combine(metrics_date, datetime.min.time()),
            QueryExecution.executed_at < datetime.combine(metrics_date + timedelta(days=1), datetime.min.time())
        ).all()

        if not executions:
            return {
                "brand_id": brand_id,
                "date": str(metrics_date),
                "message": "No executions found for this date"
            }

        # Collect query results
        query_results = []
        platform_data = {}

        for execution in executions:
            result = {
                "platform": execution.platform,
                "status": execution.status,
                "brand_mentioned": False,
                "sentiment_score": None,
                "position": None,
                "total_citations": 0,
                "brand_citation_count": 0,
                "competitor_mentions": {}
            }

            if execution.analysis:
                analysis = execution.analysis
                result["brand_mentioned"] = analysis.brand_mentioned
                result["sentiment_score"] = analysis.sentiment_score
                result["position"] = analysis.position
                result["total_citations"] = analysis.citation_count
                result["competitor_mentions"] = analysis.competitor_mentions or {}

                # Count brand citations
                if analysis.citations and brand.domain:
                    for citation in analysis.citations:
                        if isinstance(citation, dict) and brand.domain in citation.get("domain", ""):
                            result["brand_citation_count"] += 1

            query_results.append(result)

            # Group by platform
            if execution.platform not in platform_data:
                platform_data[execution.platform] = []
            platform_data[execution.platform].append(result)

        # Calculate metrics
        calculator = MetricsCalculator()

        # Overall metrics
        daily_metrics = calculator.calculate_daily_metrics(
            query_results, brand.name, competitors
        )

        # Platform breakdown
        platform_metrics = calculator.aggregate_platform_metrics(platform_data)
        platform_breakdown = {
            platform: {
                "mentions": pm.mentions,
                "sentiment": pm.sentiment_avg,
                "position_avg": pm.position_avg,
                "visibility_score": pm.visibility_score,
                "total_queries": pm.total_queries,
                "successful_queries": pm.successful_queries
            }
            for platform, pm in platform_metrics.items()
        }

        # Calculate share of voice
        total_mentions = sum(r.get("brand_mentioned", False) for r in query_results)
        competitor_mentions = {}
        for comp in competitors:
            comp_count = sum(
                r.get("competitor_mentions", {}).get(comp, {}).get("count", 0)
                for r in query_results
            )
            competitor_mentions[comp] = comp_count

        sov_data = calculator.calculate_share_of_voice(total_mentions, competitor_mentions)

        # Top citations
        all_citations = {}
        for execution in executions:
            if execution.analysis and execution.analysis.citations:
                for citation in execution.analysis.citations:
                    if isinstance(citation, dict):
                        domain = citation.get("domain", "")
                        all_citations[domain] = all_citations.get(domain, 0) + 1

        top_citations = sorted(
            [{"domain": d, "count": c} for d, c in all_citations.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Save or update daily metrics
        existing = db.query(DailyMetrics).filter(
            DailyMetrics.brand_id == UUID(brand_id),
            DailyMetrics.date == metrics_date
        ).first()

        if existing:
            existing.visibility_score = daily_metrics.visibility_score
            existing.sentiment_avg = daily_metrics.sentiment_score
            existing.mention_count = total_mentions
            existing.share_of_voice = sov_data.get("brand", 0)
            existing.platform_breakdown = platform_breakdown
            existing.top_citations = top_citations
            existing.total_queries = len(executions)
            existing.successful_queries = sum(1 for e in executions if e.status == "completed")
        else:
            new_metrics = DailyMetrics(
                brand_id=UUID(brand_id),
                date=metrics_date,
                visibility_score=daily_metrics.visibility_score,
                sentiment_avg=daily_metrics.sentiment_score,
                mention_count=total_mentions,
                share_of_voice=sov_data.get("brand", 0),
                platform_breakdown=platform_breakdown,
                top_citations=top_citations,
                total_queries=len(executions),
                successful_queries=sum(1 for e in executions if e.status == "completed")
            )
            db.add(new_metrics)

        db.commit()

        return {
            "brand_id": brand_id,
            "date": str(metrics_date),
            "visibility_score": daily_metrics.visibility_score,
            "sentiment_avg": daily_metrics.sentiment_score,
            "mention_count": total_mentions,
            "share_of_voice": sov_data.get("brand", 0),
            "platform_breakdown": platform_breakdown,
            "total_queries": len(executions)
        }


@shared_task
def calculate_all_daily_metrics() -> dict:
    """
    Calculate daily metrics for all active brands.
    Scheduled to run daily.

    Returns:
        Dict with processing summary
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from ..config import settings
    from ..models.brand import Brand

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    processed = 0
    errors = []

    with Session(engine) as db:
        brands = db.query(Brand).all()

        for brand in brands:
            try:
                calculate_daily_metrics_task.delay(str(brand.id))
                processed += 1
            except Exception as e:
                errors.append({
                    "brand_id": str(brand.id),
                    "error": str(e)
                })

    return {
        "processed": processed,
        "errors": len(errors),
        "error_details": errors
    }


# Import timedelta at module level
from datetime import timedelta
