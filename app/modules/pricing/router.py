from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import UserRole
from app.modules.pricing.schemas import (
    CurrencyCreate,
    CurrencyUpdate,
    CurrencyResponse,
    ExchangeRateCreate,
    ExchangeRateResponse,
    PriceCreate,
    PriceUpdate,
    PriceResponse,
    PriceResolutionRequest,
    PriceResolutionResponse,
    PriceBreakdown,
)
from app.modules.pricing.service import PricingService

router = APIRouter(prefix="/pricing", tags=["Pricing"])
admin_router = APIRouter(prefix="/admin", tags=["Admin Pricing"])

storefront_service = None


async def get_pricing_service(db: AsyncSession = Depends(get_db)) -> PricingService:
    return PricingService(db)


@router.get("/{product_id}")
async def get_product_price(
    product_id: int,
    variant_id: Optional[int] = None,
    currency: str = Query("USD", max_length=3),
    quantity: int = Query(1, ge=1),
    service: PricingService = Depends(get_pricing_service),
) -> PriceResolutionResponse:
    addon_ids: List[int] = []
    subtotal, breakdown = await service.resolve_price(
        product_id=product_id,
        variant_id=variant_id,
        addon_ids=addon_ids,
        currency_code=currency,
        quantity=quantity,
    )

    return PriceResolutionResponse(
        product_id=product_id,
        variant_id=variant_id,
        currency=currency,
        quantity=quantity,
        breakdown=breakdown,
        unit_price=breakdown.total,
        line_total=breakdown.total * quantity,
    )


@router.get("/currencies", response_model=List[CurrencyResponse])
async def list_currencies(
    is_active: Optional[bool] = True,
    service: PricingService = Depends(get_pricing_service),
) -> List[CurrencyResponse]:
    currencies = await service.list_currencies(is_active)
    return [CurrencyResponse.model_validate(c) for c in currencies]


@admin_router.get("/exchange-rates", response_model=List[ExchangeRateResponse])
async def list_exchange_rates(
    from_currency: Optional[str] = None,
    to_currency: Optional[str] = None,
    service: PricingService = Depends(get_pricing_service),
) -> List[ExchangeRateResponse]:
    rates = await service.list_exchange_rates(from_currency, to_currency)
    return [ExchangeRateResponse.model_validate(r) for r in rates]


@admin_router.post("/currencies", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    currency_data: CurrencyCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> CurrencyResponse:
    if current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    currency = await service.create_currency(currency_data)
    return CurrencyResponse.model_validate(currency)


@admin_router.patch("/currencies/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: int,
    currency_data: CurrencyUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PricingService = Depends(get_pricing_service),
) -> CurrencyResponse:
    if current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    currency = await service.update_currency(currency_id, currency_data)
    return CurrencyResponse.model_validate(currency)


@admin_router.post("/exchange-rates/update", status_code=status.HTTP_200_OK)
async def update_exchange_rates(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    if current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    from app.modules.pricing.exchange_rates import exchange_rate_provider
    await exchange_rate_provider.fetch_rates("USD")
    return {"status": "Exchange rates updated"}