"""
Worker for executing queries across AI platforms.
"""

import asyncio
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from celery import shared_task

from ..adapters import get_adapter
from ..config import settings


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    rate_limit="10/m"
)
def execute_query_task(
    self,
    question_id: str,
    question_text: str,
    platform: str,
    brand_name: str
) -> dict:
    """
    Execute a single query on a specific AI platform.

    Args:
        question_id: UUID of the question
        question_text: The query to execute
        platform: AI platform to query (chatgpt, claude, perplexity, gemini)
        brand_name: Brand name for mention extraction

    Returns:
        Dict with execution results
    """
    try:
        adapter = get_adapter(platform)

        # Run async query in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            response = loop.run_until_complete(adapter.execute_query(question_text))
        finally:
            loop.close()

        # Parse response
        parsed = adapter.parse_response(response)

        # Extract brand mentions
        mentions = adapter.extract_brand_mentions(response.content, brand_name)

        # Find position if list response
        position = None
        total_recommendations = None
        if parsed.is_list_response:
            position = adapter.find_brand_position(parsed.list_items, brand_name)
            total_recommendations = len(parsed.list_items)

        return {
            "question_id": question_id,
            "platform": platform,
            "status": "completed",
            "content": response.content,
            "model_used": response.model,
            "tokens_used": response.tokens_used,
            "response_time_ms": response.response_time_ms,
            "brand_mentioned": len(mentions) > 0,
            "mention_count": len(mentions),
            "mention_contexts": [m.context for m in mentions],
            "citations": [{"url": c.url, "domain": c.domain} for c in parsed.citations],
            "citation_count": len(parsed.citations),
            "is_list_response": parsed.is_list_response,
            "position": position,
            "total_recommendations": total_recommendations,
            "executed_at": datetime.utcnow().isoformat(),
            "raw_response": response.raw_response
        }

    except Exception as e:
        return {
            "question_id": question_id,
            "platform": platform,
            "status": "failed",
            "error_message": str(e),
            "executed_at": datetime.utcnow().isoformat()
        }


@shared_task(bind=True)
def execute_queries_task(
    self,
    brand_id: str,
    question_ids: List[str],
    platforms: Optional[List[str]] = None
) -> dict:
    """
    Execute multiple queries across platforms for a brand.

    Args:
        brand_id: UUID of the brand
        question_ids: List of question UUIDs to execute
        platforms: Optional list of platforms (defaults to all)

    Returns:
        Dict with execution summary
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from ..config import settings
    from ..models.brand import Brand
    from ..models.question import Question

    if platforms is None:
        platforms = ["chatgpt", "claude", "perplexity", "gemini"]

    # Create sync database session
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    results = []
    errors = []

    with Session(engine) as db:
        # Get brand
        brand = db.query(Brand).filter(Brand.id == UUID(brand_id)).first()
        if not brand:
            return {"error": "Brand not found", "brand_id": brand_id}

        # Get questions
        questions = db.query(Question).filter(
            Question.id.in_([UUID(qid) for qid in question_ids])
        ).all()

        total_queries = len(questions) * len(platforms)
        completed = 0

        for question in questions:
            for platform in platforms:
                try:
                    # Execute query task
                    result = execute_query_task.delay(
                        str(question.id),
                        question.question_text,
                        platform,
                        brand.name
                    )
                    results.append({
                        "question_id": str(question.id),
                        "platform": platform,
                        "task_id": result.id
                    })
                    completed += 1

                except Exception as e:
                    errors.append({
                        "question_id": str(question.id),
                        "platform": platform,
                        "error": str(e)
                    })

                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": completed,
                        "total": total_queries,
                        "percent": int((completed / total_queries) * 100)
                    }
                )

    return {
        "brand_id": brand_id,
        "total_queries": total_queries,
        "submitted": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    }


@shared_task
def execute_brand_analysis(brand_id: str) -> dict:
    """
    Execute full analysis for a brand - queries all active questions.

    Args:
        brand_id: UUID of the brand

    Returns:
        Dict with analysis job summary
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from ..config import settings
    from ..models.brand import Brand
    from ..models.question import Question

    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    with Session(engine) as db:
        # Get brand
        brand = db.query(Brand).filter(Brand.id == UUID(brand_id)).first()
        if not brand:
            return {"error": "Brand not found"}

        # Get active questions
        questions = db.query(Question).filter(
            Question.brand_id == UUID(brand_id),
            Question.is_active == True
        ).all()

        if not questions:
            return {"error": "No active questions found for brand"}

        question_ids = [str(q.id) for q in questions]

    # Trigger batch query execution
    result = execute_queries_task.delay(
        brand_id,
        question_ids,
        ["chatgpt", "claude", "perplexity", "gemini"]
    )

    return {
        "brand_id": brand_id,
        "questions_count": len(question_ids),
        "task_id": result.id,
        "status": "submitted"
    }
