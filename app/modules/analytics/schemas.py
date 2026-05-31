from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.modules.analytics.models import PayoutStatus


class SalesSummary(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    period_start: datetime
    period_end: datetime


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    units_sold: int
    revenue: float


class VendorAnalyticsResponse(BaseModel):
    vendor_id: int
    period_start: datetime
    period_end: datetime
    sales_summary: SalesSummary
    top_products: List[TopProduct]
    payout_summary: dict


class PlatformAnalyticsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_revenue: float
    total_orders: int
    total_vendors: int
    total_products: int
    total_customers: int
    average_order_value: float
    revenue_by_day: List[dict]
    top_vendors: List[dict]
    top_products: List[TopProduct]


class PayoutResponse(BaseModel):
    id: int
    vendor_id: int
    amount: float
    currency_code: str
    status: PayoutStatus
    period_start: datetime
    period_end: datetime
    total_sales: float
    total_orders: int
    commission_amount: float
    processed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PayoutListResponse(BaseModel):
    items: List[PayoutResponse]
    total: int
    limit: int
    offset: int


class PayoutCreateRequest(BaseModel):
    vendor_id: int
    period_start: datetime
    period_end: datetime


class ProcessPayoutsResponse(BaseModel):
    processed_count: int
    total_amount: float
    payouts: List[PayoutResponse]