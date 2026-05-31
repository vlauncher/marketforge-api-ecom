from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.modules.orders.models import OrderStatus


class AddressSchema(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"


class OrderItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., ge=1)
    unit_price: float
    addons: Optional[Dict[str, Any]] = None
    name: str
    sku: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    product_id: int
    variant_id: Optional[int]
    name: str
    sku: Optional[str]
    quantity: int
    unit_price: float
    addons: Optional[Dict[str, Any]]
    total_price: float

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    store_id: int
    items: List[OrderItemCreate]
    shipping_address: AddressSchema
    billing_address: Optional[AddressSchema] = None
    currency_code: str = "USD"
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    user_id: Optional[int]
    store_id: int
    order_number: str
    status: OrderStatus
    subtotal: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total: float
    currency_code: str
    shipping_address: Optional[Dict[str, Any]]
    billing_address: Optional[Dict[str, Any]]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class ShipmentCreate(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None


class ShipmentUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    carrier: Optional[str]
    tracking_number: Optional[str]
    status: str
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    limit: int
    offset: int