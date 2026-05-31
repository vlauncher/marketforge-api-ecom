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


@router.post("", response_model=CheckoutResponse, summary="Process checkout")
async def process_checkout(
    request: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CheckoutService = Depends(get_checkout_service),
) -> CheckoutResponse:
    """
    Process a checkout with inventory reservation and order creation.

    This endpoint is **idempotent** - submitting the same idempotency_key
    will return the original order without creating duplicates.

    - **cart_id**: The cart to checkout
    - **shipping_address**: Delivery address
    - **billing_address**: Optional billing address (defaults to shipping)
    - **payment_method**: Payment method identifier
    - **idempotency_key**: Unique key for idempotent checkout
    """
    return await service.process_checkout(request, current_user)


@router.post("/apply-coupon", response_model=CouponValidationResult, summary="Validate and apply coupon")
async def apply_coupon(
    coupon_data: CouponApplyRequest,
    service: CheckoutService = Depends(get_checkout_service),
) -> CouponValidationResult:
    """
    Validate a coupon code and get the discount amount.

    - **coupon_code**: The coupon code to validate
    - **subtotal**: Order subtotal for minimum order validation
    """
    return await service.validate_coupon(coupon_data.coupon_code, 0)


@router.get("/calculate-shipping", response_model=ShippingCalculationResult, summary="Calculate shipping")
async def calculate_shipping(
    cart_id: int = Query(...),
    country: str = Query("US"),
    service: CheckoutService = Depends(get_checkout_service),
) -> ShippingCalculationResult:
    """
    Calculate shipping options and costs for the given cart and destination.

    - **cart_id**: The cart to calculate shipping for
    - **country**: Destination country code
    """
    address = {"country": country}
    return await service.calculate_shipping(cart_id, address)


@router.get("/calculate-tax", response_model=TaxCalculationResult, summary="Calculate tax")
async def calculate_tax(
    cart_id: int = Query(...),
    country: str = Query("US"),
    service: CheckoutService = Depends(get_checkout_service),
) -> TaxCalculationResult:
    """
    Calculate estimated tax for the given cart and destination.

    - **cart_id**: The cart to calculate tax for
    - **country**: Destination country code
    """
    address = {"country": country}
    return await service.calculate_tax(cart_id, address)