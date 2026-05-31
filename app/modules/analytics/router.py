from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.analytics.schemas import (
    VendorAnalyticsResponse,
    PlatformAnalyticsResponse,
    PayoutResponse,
    PayoutListResponse,
    ProcessPayoutsResponse,
    SalesSummary,
    TopProduct,
)
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/vendors", tags=["Vendor Analytics"])
admin_router = APIRouter(prefix="/admin", tags=["Admin Analytics"])


async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/{vendor_id}/analytics", response_model=VendorAnalyticsResponse)
async def get_vendor_analytics(
    vendor_id: int,
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> VendorAnalyticsResponse:
    analytics = await service.get_vendor_analytics(vendor_id, period_start, period_end)
    return VendorAnalyticsResponse(
        vendor_id=analytics["vendor_id"],
        period_start=analytics["period_start"],
        period_end=analytics["period_end"],
        sales_summary=SalesSummary(**analytics["sales_summary"]),
        top_products=[TopProduct(**p) for p in analytics["top_products"]],
        payout_summary=analytics["payout_summary"],
    )


@router.get("/{vendor_id}/payouts", response_model=PayoutListResponse)
async def list_vendor_payouts(
    vendor_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> PayoutListResponse:
    payouts, total = await service.get_vendor_payouts(vendor_id, limit, offset)
    return PayoutListResponse(
        items=[PayoutResponse.model_validate(p) for p in payouts],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def get_platform_analytics(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> PlatformAnalyticsResponse:
    analytics = await service.get_platform_analytics(period_start, period_end)
    return PlatformAnalyticsResponse(
        period_start=analytics["period_start"],
        period_end=analytics["period_end"],
        total_revenue=analytics["total_revenue"],
        total_orders=analytics["total_orders"],
        total_vendors=analytics["total_vendors"],
        total_products=analytics["total_products"],
        total_customers=analytics["total_customers"],
        average_order_value=analytics["average_order_value"],
        revenue_by_day=analytics["revenue_by_day"],
        top_vendors=analytics["top_vendors"],
        top_products=[TopProduct(**p) for p in analytics["top_products"]],
    )


@admin_router.post("/payouts/process", response_model=ProcessPayoutsResponse)
async def process_payouts(
    vendor_ids: Optional[List[int]] = None,
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ProcessPayoutsResponse:
    payouts = await service.process_payouts(vendor_ids, period_start, period_end)
    total_amount = sum(p.amount for p in payouts)
    return ProcessPayoutsResponse(
        processed_count=len(payouts),
        total_amount=total_amount,
        payouts=[PayoutResponse.model_validate(p) for p in payouts],
    )