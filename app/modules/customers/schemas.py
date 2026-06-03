from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.modules.customers.models import LoyaltyTier


class WishlistItemResponse(BaseModel):
    id: int
    product_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WishlistResponse(BaseModel):
    items: List[WishlistItemResponse]
    total: int


class LoyaltyAccountResponse(BaseModel):
    id: int
    user_id: int
    points: int
    tier: LoyaltyTier
    lifetime_points: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PointsTransactionResponse(BaseModel):
    id: int
    user_id: int
    points: int
    transaction_type: str
    description: Optional[str]
    created_at: datetime


class RedeemPointsRequest(BaseModel):
    points: int
    reward_id: Optional[str] = None


class LoyaltyTierInfo(BaseModel):
    tier: LoyaltyTier
    min_points: int
    max_points: Optional[int]
    multiplier: float
    benefits: List[str]