"""
Brand management API routes.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ...database import get_db
from ...models.user import User
from ...models.brand import Brand, Competitor
from ...schemas.brand import (
    BrandCreate, BrandUpdate, BrandResponse, BrandListResponse,
    CompetitorCreate, CompetitorResponse
)
from ..deps import get_current_user

router = APIRouter()


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_in: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new brand to monitor."""
    # Create brand
    brand = Brand(
        user_id=current_user.id,
        name=brand_in.name,
        domain=brand_in.domain,
        description=brand_in.description,
        industry=brand_in.industry,
        keywords=brand_in.keywords,
        products=[p.model_dump() for p in brand_in.products]
    )
    db.add(brand)
    await db.flush()

    # Create competitors
    for comp_in in brand_in.competitors:
        competitor = Competitor(
            brand_id=brand.id,
            name=comp_in.name,
            domain=comp_in.domain
        )
        db.add(competitor)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Brand)
        .options(selectinload(Brand.competitors))
        .where(Brand.id == brand.id)
    )
    return result.scalar_one()


@router.get("", response_model=BrandListResponse)
async def list_brands(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all brands for the current user."""
    query = select(Brand).where(Brand.user_id == current_user.id)

    if search:
        query = query.where(Brand.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Get paginated results
    query = query.options(selectinload(Brand.competitors))
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Brand.created_at.desc())

    result = await db.execute(query)
    brands = result.scalars().all()

    return BrandListResponse(
        items=brands,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific brand by ID."""
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

    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: UUID,
    brand_in: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a brand."""
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

    # Update fields
    update_data = brand_in.model_dump(exclude_unset=True)
    if "products" in update_data:
        update_data["products"] = [p.model_dump() if hasattr(p, 'model_dump') else p for p in update_data["products"]]

    for field, value in update_data.items():
        setattr(brand, field, value)

    await db.commit()
    await db.refresh(brand)

    return brand


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a brand."""
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    brand = result.scalar_one_or_none()

    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    await db.delete(brand)
    await db.commit()


# Competitor endpoints
@router.post("/{brand_id}/competitors", response_model=CompetitorResponse, status_code=status.HTTP_201_CREATED)
async def add_competitor(
    brand_id: UUID,
    competitor_in: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a competitor to a brand."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    competitor = Competitor(
        brand_id=brand_id,
        name=competitor_in.name,
        domain=competitor_in.domain
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)

    return competitor


@router.delete("/{brand_id}/competitors/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_competitor(
    brand_id: UUID,
    competitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a competitor from a brand."""
    # Verify brand ownership
    result = await db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found"
        )

    result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.brand_id == brand_id
        )
    )
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competitor not found"
        )

    await db.delete(competitor)
    await db.commit()
