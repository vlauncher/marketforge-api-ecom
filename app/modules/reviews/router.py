from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import UserRole
from app.modules.reviews.schemas import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    RatingResponse,
    ReviewListResponse,
)
from app.modules.reviews.service import ReviewsService

router = APIRouter(prefix="/products", tags=["Reviews"])
admin_router = APIRouter(prefix="/admin/reviews", tags=["Admin Reviews"])


async def get_reviews_service(db: AsyncSession = Depends(get_db)) -> ReviewsService:
    return ReviewsService(db)


@router.post("/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: int,
    review_data: ReviewCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ReviewsService = Depends(get_reviews_service),
) -> ReviewResponse:
    review = await service.create_review(
        product_id=product_id,
        user_id=current_user["user_id"],
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
    )
    return ReviewResponse.model_validate(review)


@router.get("/{product_id}/reviews", response_model=ReviewListResponse)
async def list_product_reviews(
    product_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ReviewsService = Depends(get_reviews_service),
) -> ReviewListResponse:
    reviews, total, avg_rating = await service.list_product_reviews(
        product_id=product_id,
        approved_only=True,
        limit=limit,
        offset=offset,
    )
    return ReviewListResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        average_rating=avg_rating,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}/rating", response_model=RatingResponse)
async def get_product_rating(
    product_id: int,
    service: ReviewsService = Depends(get_reviews_service),
) -> RatingResponse:
    rating = await service.get_product_rating(product_id)
    if not rating:
        return RatingResponse(
            id=0,
            product_id=product_id,
            average_rating=0.0,
            total_reviews=0,
        )
    return RatingResponse.model_validate(rating)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ReviewsService = Depends(get_reviews_service),
) -> ReviewResponse:
    review = await service.update_review(
        review_id=review_id,
        user_id=current_user["user_id"],
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
    )
    return ReviewResponse.model_validate(review)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ReviewsService = Depends(get_reviews_service),
) -> None:
    is_admin = current_user["role"] == UserRole.ADMIN
    await service.delete_review(review_id, current_user["user_id"], is_admin)


@admin_router.post("/{review_id}/approve", response_model=ReviewResponse)
async def approve_review(
    review_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: ReviewsService = Depends(get_reviews_service),
) -> ReviewResponse:
    if current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    review = await service.approve_review(review_id)
    return ReviewResponse.model_validate(review)