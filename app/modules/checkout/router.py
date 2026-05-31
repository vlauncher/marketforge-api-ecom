from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.checkout.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    CouponApplyRequest,
    CouponValidationResult,
    ShippingCalculationResult,
    ShippingAddress,
    TaxCalculationResult,
)
from app.modules.checkout.service import CheckoutService

router = APIRouter(prefix="/checkout", tags=["Checkout"])


async def get_checkout_service(db: AsyncSession = Depends(get_db)) -> CheckoutService:
    return CheckoutService(db)


@router.post("", response_model=CheckoutResponse)
async def process_checkout(
    request: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CheckoutService = Depends(get_checkout_service),
) -> CheckoutResponse:
    return await service.process_checkout(request, current_user)


@router.post("/apply-coupon", response_model=CouponValidationResult)
async def apply_coupon(
    coupon_data: CouponApplyRequest,
    service: CheckoutService = Depends(get_checkout_service),
) -> CouponValidationResult:
    return await service.validate_coupon(coupon_data.coupon_code, 0)


@router.get("/calculate-shipping", response_model=ShippingCalculationResult)
async def calculate_shipping(
    cart_id: int = Query(...),
    country: str = Query("US"),
    service: CheckoutService = Depends(get_checkout_service),
) -> ShippingCalculationResult:
    address = {"country": country}
    return await service.calculate_shipping(cart_id, address)


@router.get("/calculate-tax", response_model=TaxCalculationResult)
async def calculate_tax(
    cart_id: int = Query(...),
    country: str = Query("US"),
    service: CheckoutService = Depends(get_checkout_service),
) -> TaxCalculationResult:
    address = {"country": country}
    return await service.calculate_tax(cart_id, address)