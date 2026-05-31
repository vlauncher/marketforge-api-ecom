from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.modules.orders.models import OrderStatus


class CheckoutItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., ge=1)
    selected_addons: Optional[Dict[str, Any]] = None


class ShippingAddress(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"


class CheckoutRequest(BaseModel):
    cart_id: int
    shipping_address: ShippingAddress
    billing_address: Optional[ShippingAddress] = None
    payment_method: str = "stripe"
    coupon_code: Optional[str] = None
    idempotency_key: str = Field(..., description="Unique key to prevent duplicate orders")


class CouponApplyRequest(BaseModel):
    coupon_code: str
    subtotal: float


class ShippingRate(BaseModel):
    carrier: str
    service: str
    price: float
    estimated_days: int


class CheckoutResponse(BaseModel):
    order_id: int
    order_number: str
    payment_intent_id: Optional[str]
    total: float
    currency: str
    status: OrderStatus


class CouponValidationResult(BaseModel):
    valid: bool
    coupon_code: Optional[str]
    discount_type: Optional[str]
    discount_value: Optional[float]
    discount_amount: float
    message: str


class ShippingCalculationResult(BaseModel):
    rates: List[ShippingRate]
    currency: str


class TaxCalculationResult(BaseModel):
    tax_amount: float
    tax_rate: float
    taxable_amount: float
    currency: str