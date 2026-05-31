from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.modules.promotions.models import DiscountType


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    discount_type: DiscountType
    discount_value: float = Field(..., gt=0)
    min_order_amount: float = 0.0
    max_discount_amount: Optional[float] = None
    max_uses: Optional[int] = None
    per_user_limit: int = 1
    valid_from: datetime
    valid_until: Optional[datetime] = None


class CouponUpdate(BaseModel):
    discount_value: Optional[float] = Field(None, gt=0)
    min_order_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    max_uses: Optional[int] = None
    per_user_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    id: int
    store_id: int
    code: str
    discount_type: DiscountType
    discount_value: float
    min_order_amount: float
    max_discount_amount: Optional[float]
    max_uses: Optional[int]
    uses_count: int
    per_user_limit: int
    valid_from: datetime
    valid_until: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class CouponValidationRequest(BaseModel):
    code: str
    order_subtotal: float


class CouponValidationResponse(BaseModel):
    valid: bool
    coupon: Optional[CouponResponse] = None
    discount_amount: float = 0.0
    message: str


class PromotionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float = Field(..., gt=0)
    max_discount_amount: Optional[float] = None
    applies_to: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    priority: int = 0
    valid_from: datetime
    valid_until: Optional[datetime] = None


class PromotionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    max_discount_amount: Optional[float] = None
    applies_to: Optional[Dict[str, Any]] = None
    conditions: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class PromotionResponse(BaseModel):
    id: int
    store_id: int
    name: str
    description: Optional[str]
    discount_type: DiscountType
    discount_value: float
    max_discount_amount: Optional[float]
    applies_to: Optional[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]]
    priority: int
    is_active: bool
    valid_from: datetime
    valid_until: Optional[datetime]

    model_config = {"from_attributes": True}


class GiftCardCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    initial_balance: float = Field(..., gt=0)
    currency_code: str = "USD"
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    message: Optional[str] = None
    expires_at: Optional[datetime] = None


class GiftCardUpdate(BaseModel):
    current_balance: Optional[float] = None
    is_active: Optional[bool] = None


class GiftCardResponse(BaseModel):
    id: int
    store_id: int
    code: str
    initial_balance: float
    current_balance: float
    currency_code: str
    recipient_email: Optional[str]
    recipient_name: Optional[str]
    message: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]

    model_config = {"from_attributes": True}


class GiftCardValidationResponse(BaseModel):
    valid: bool
    gift_card: Optional[GiftCardResponse] = None
    balance: float = 0.0
    message: str


class ApplyGiftCardRequest(BaseModel):
    code: str
    amount: float