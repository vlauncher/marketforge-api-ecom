from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.modules.payments.models import PaymentStatus


class PaymentCreate(BaseModel):
    order_id: int
    amount: float = Field(..., gt=0)
    currency_code: str = "USD"
    payment_method: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    currency_code: str
    status: PaymentStatus
    payment_method: Optional[str]
    transaction_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentDetailResponse(PaymentResponse):
    refunds: List["RefundResponse"] = []

    model_config = {"from_attributes": True}


class RefundCreate(BaseModel):
    payment_id: int
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None


class RefundResponse(BaseModel):
    id: int
    payment_id: int
    amount: float
    reason: Optional[str]
    status: str
    transaction_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentWebhook(BaseModel):
    event_type: str
    payment_intent_id: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentListResponse(BaseModel):
    items: List[PaymentResponse]
    total: int
    limit: int
    offset: int