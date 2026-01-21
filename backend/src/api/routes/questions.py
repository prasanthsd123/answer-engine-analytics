"""
Question management and generation API routes.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...database import get_db
from ...models.user import User
from ...models.brand import Brand
from ...models.question import Question
from ...schemas.question import (
    QuestionCreate, QuestionResponse, QuestionListResponse,
    QuestionUpdate, QuestionBulkCreate, QuestionGenerateRequest,
    SmartQuestionGenerateRequest, SmartGenerateResponse
)
from ..deps import get_current_user

router = APIRouter()


# Question templates for generation
QUESTION_TEMPLATES = {
    "product_recommendations": [
        "What is the best {product_category} in 2025?",
        "Top 10 {product_category} tools",
        "Compare {brand} vs {competitor}",
        "{brand} alternatives",
        "Best alternatives to {brand}",
    ],
    "brand_perception": [
        "Is {brand} any good?",
        "What do people think about {brand}?",
        "{brand} pros and cons",
        "Is {brand} reliable?",
        "{brand} reputation",
    ],
    "purchase_intent": [
        "Should I use {brand}?",
        "Is {brand} worth it?",
        "{brand} reviews",
        "{brand} pricing",
        "Is {brand} expensive?",
    ],
    "feature_queries": [
        "Does {brand} have {feature}?",
        "Best {feature} tools like {brand}",
        "{brand} features",
        "What can {brand} do?",
    ],
    "comparison": [
        "{brand} vs {competitor}",
        "{brand} or {competitor} which is better?",
        "Difference between {brand} and {competitor}",
        "{brand} compared to {competitor}",
    ],
}


async def verify_brand_ownership(
    brand_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> Brand:
    """Verify the user owns the brand."""
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == user_id)
    )
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )
    return brand


@router.get("/brand/{brand_id}", response_model=QuestionListResponse)
async def list_questions(
    brand_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all questions for a brand."""
    await verify_brand_ownership(brand_id, current_user.id, db)

    query = select(Question).where(Question.brand_id == brand_id)

    if category:
        query = query.where(Question.category == category)
    if is_active is not None:
        query = query.where(Question.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Question.created_at.desc())

    result = await db.execute(query)
    questions = result.scalars().all()

    return QuestionListResponse(
        items=questions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/brand/{brand_id}", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    brand_id: UUID,
    question_in: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new question for a brand."""
    await verify_brand_ownership(brand_id, current_user.id, db)

    question = Question(
        brand_id=brand_id,
        question_text=question_in.question_text,
        category=question_in.category
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    return question


@router.post("/brand/{brand_id}/bulk", response_model=List[QuestionResponse], status_code=status.HTTP_201_CREATED)
async def create_questions_bulk(
    brand_id: UUID,
    questions_in: QuestionBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple questions for a brand."""
    await verify_brand_ownership(brand_id, current_user.id, db)

    questions = []
    for q_in in questions_in.questions:
        question = Question(
            brand_id=brand_id,
            question_text=q_in.question_text,
            category=q_in.category
        )
        db.add(question)
        questions.append(question)

    await db.commit()

    for q in questions:
        await db.refresh(q)

    return questions


@router.post("/brand/{brand_id}/generate", response_model=List[QuestionResponse], status_code=status.HTTP_201_CREATED)
async def generate_questions(
    brand_id: UUID,
    request: QuestionGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Automatically generate questions for a brand based on templates."""
    from sqlalchemy.orm import selectinload

    # Get brand with competitors
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Determine which categories to use
    categories = request.categories or list(QUESTION_TEMPLATES.keys())

    generated_questions = []

    for category in categories:
        if category not in QUESTION_TEMPLATES:
            continue

        templates = QUESTION_TEMPLATES[category]
        count = 0

        for template in templates:
            if count >= request.max_questions_per_category:
                break

            # Generate questions from template
            if "{brand}" in template:
                question_text = template.replace("{brand}", brand.name)

                # Handle competitor placeholder
                if "{competitor}" in question_text and request.include_competitors:
                    for competitor in brand.competitors[:3]:  # Limit to 3 competitors
                        comp_question = question_text.replace("{competitor}", competitor.name)
                        generated_questions.append((comp_question, category))
                        count += 1
                        if count >= request.max_questions_per_category:
                            break
                elif "{competitor}" not in question_text:
                    # Handle product category placeholder
                    if "{product_category}" in question_text and brand.products:
                        for product in brand.products[:2]:
                            if isinstance(product, dict) and "category" in product:
                                prod_question = question_text.replace("{product_category}", product["category"])
                                generated_questions.append((prod_question, category))
                                count += 1
                    elif "{feature}" in question_text:
                        # Skip feature queries if no features defined
                        continue
                    else:
                        generated_questions.append((question_text, category))
                        count += 1

    # Create questions in database
    questions = []
    for question_text, category in generated_questions:
        # Check for duplicates
        existing = await db.execute(
            select(Question).where(
                Question.brand_id == brand_id,
                Question.question_text == question_text
            )
        )
        if existing.scalar_one_or_none():
            continue

        question = Question(
            brand_id=brand_id,
            question_text=question_text,
            category=category
        )
        db.add(question)
        questions.append(question)

    await db.commit()

    for q in questions:
        await db.refresh(q)

    return questions


@router.post("/brand/{brand_id}/generate-smart", response_model=SmartGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_smart_questions(
    brand_id: UUID,
    request: SmartQuestionGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate smart questions using AI based on comprehensive brand research.

    This endpoint performs a 4-step research process:
    1. Deep crawl the brand's website (20+ pages)
    2. Use GPT to analyze website content
    3. Use Perplexity for market research (competitors, reviews, trends)
    4. Generate realistic user questions based on all research

    The generated questions reflect actual user search behavior with specific
    industry, competitor, and pain point references from the research.
    """
    from sqlalchemy.orm import selectinload
    from ...services.smart_question_generator import generate_smart_questions as gen_questions

    # Get brand with competitors
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    # Get competitor names
    competitor_names = [c.name for c in brand.competitors]

    # Generate smart questions with full research summary
    generation_result = await gen_questions(
        brand_name=brand.name,
        domain=brand.domain,
        industry=brand.industry,
        keywords=brand.keywords or [],
        products=brand.products or [],
        competitors=competitor_names,
        num_questions=request.num_questions,
        return_research=True  # Get research summary
    )

    # Extract questions and research from result
    generated_questions = generation_result.questions
    research_data = generation_result.research_summary

    # Save questions to database
    questions = []
    for gen_q in generated_questions:
        # Check for duplicates
        existing = await db.execute(
            select(Question).where(
                Question.brand_id == brand_id,
                Question.question_text == gen_q.text
            )
        )
        if existing.scalar_one_or_none():
            continue

        question = Question(
            brand_id=brand_id,
            question_text=gen_q.text,
            category=gen_q.category
        )
        db.add(question)
        questions.append(question)

    await db.commit()

    for q in questions:
        await db.refresh(q)

    # Build comprehensive research summary
    research_summary = {
        # Brand info
        "brand_analyzed": brand.name,
        "website_domain": brand.domain,

        # Website research metrics
        "website_pages_crawled": research_data.get("website_pages_crawled", 0),
        "products_found": research_data.get("products_found", 0),
        "features_found": research_data.get("features_found", 0),
        "testimonials_found": research_data.get("testimonials_found", 0),

        # Perplexity market research metrics
        "perplexity_queries_made": research_data.get("perplexity_queries_made", 0),
        "citations_found": research_data.get("citations_found", 0),
        "market_position": research_data.get("market_position"),
        "customer_sentiment": research_data.get("customer_sentiment"),

        # Discovered insights
        "competitors_discovered": research_data.get("competitors_discovered", []),
        "customer_industries": research_data.get("customer_industries", []),
        "customer_pain_points": research_data.get("customer_pain_points", []),
        "industry_trends": research_data.get("industry_trends", []),

        # Question generation
        "question_categories": list(set(q.category for q in questions)),
        "research_quality_score": research_data.get("research_quality_score", 0),
    }

    return SmartGenerateResponse(
        questions_generated=len(questions),
        questions=questions,
        research_summary=research_summary
    )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific question."""
    result = await db.execute(
        select(Question)
        .join(Brand)
        .where(Question.id == question_id, Brand.user_id == current_user.id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    return question


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: UUID,
    question_in: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a question."""
    result = await db.execute(
        select(Question)
        .join(Brand)
        .where(Question.id == question_id, Brand.user_id == current_user.id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    update_data = question_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(question, field, value)

    await db.commit()
    await db.refresh(question)

    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a question."""
    result = await db.execute(
        select(Question)
        .join(Brand)
        .where(Question.id == question_id, Brand.user_id == current_user.id)
    )
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    await db.delete(question)
    await db.commit()
