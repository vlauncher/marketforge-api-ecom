from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.modules.reviews.models import Review as ReviewModel
from app.modules.reviews.models import Rating as RatingModel


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: int
    title: Optional[str]
    comment: Optional[str]
    is_approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RatingResponse(BaseModel):
    id: int
    product_id: int
    average_rating: float
    total_reviews: int

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    average_rating: float
    limit: int
    offset: int