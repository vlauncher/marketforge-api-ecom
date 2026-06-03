from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.modules.identity.dependencies import get_current_user
from app.modules.vendors.service import VendorService
from app.modules.promotions.schemas import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponValidationRequest,
    CouponValidationResponse,
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    GiftCardCreate,
    GiftCardResponse,
    GiftCardValidationResponse,
    ApplyGiftCardRequest,
)
from app.modules.promotions.service import PromotionsService

router = APIRouter(tags=["Promotions"])
vendor_router = APIRouter(prefix="/vendor", tags=["Vendor Promotions"])


async def get_promotions_service(db: AsyncSession = Depends(get_db)) -> PromotionsService:
    return PromotionsService(db)


async def get_current_vendor_store_id(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    if not vendor.stores:
        raise ValidationError("Vendor has no stores")
    return vendor.stores[0].id


@router.post("/validate-coupon", response_model=CouponValidationResponse)
async def validate_coupon(
    request: CouponValidationRequest,
    current_user: Optional[Dict[str, Any]] = None,
    service: PromotionsService = Depends(get_promotions_service),
) -> CouponValidationResponse:
    valid, coupon, discount_amount, message = await service.validate_coupon(
        code=request.code,
        order_subtotal=request.order_subtotal,
        user_id=current_user["user_id"] if current_user else None,
    )
    return CouponValidationResponse(
        valid=valid,
        coupon=CouponResponse.model_validate(coupon) if coupon else None,
        discount_amount=discount_amount,
        message=message,
    )


@router.post("/validate-gift-card", response_model=GiftCardValidationResponse)
async def validate_gift_card(
    code: str = Query(...),
    service: PromotionsService = Depends(get_promotions_service),
) -> GiftCardValidationResponse:
    valid, gift_card, balance, message = await service.validate_gift_card(code)
    return GiftCardValidationResponse(
        valid=valid,
        gift_card=GiftCardResponse.model_validate(gift_card) if gift_card else None,
        balance=balance,
        message=message,
    )


@vendor_router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    coupon_data: CouponCreate,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> CouponResponse:
    coupon = await service.create_coupon(store_id, coupon_data)
    return CouponResponse.model_validate(coupon)


@vendor_router.get("/coupons", response_model=List[CouponResponse])
async def list_coupons(
    is_active: Optional[bool] = True,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> List[CouponResponse]:
    coupons = await service.list_store_coupons(store_id, is_active)
    return [CouponResponse.model_validate(c) for c in coupons]


@vendor_router.patch("/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    coupon_data: CouponUpdate,
    service: PromotionsService = Depends(get_promotions_service),
) -> CouponResponse:
    coupon = await service.update_coupon(coupon_id, coupon_data)
    return CouponResponse.model_validate(coupon)


@vendor_router.post("/promotions", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    promotion_data: PromotionCreate,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> PromotionResponse:
    promotion = await service.create_promotion(store_id, promotion_data)
    return PromotionResponse.model_validate(promotion)


@vendor_router.get("/promotions", response_model=List[PromotionResponse])
async def list_promotions(
    is_active: Optional[bool] = True,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> List[PromotionResponse]:
    promotions = await service.list_store_promotions(store_id, is_active)
    return [PromotionResponse.model_validate(p) for p in promotions]


@vendor_router.patch("/promotions/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_id: int,
    promotion_data: PromotionUpdate,
    service: PromotionsService = Depends(get_promotions_service),
) -> PromotionResponse:
    promotion = await service.update_promotion(promotion_id, promotion_data)
    return PromotionResponse.model_validate(promotion)


@vendor_router.post("/gift-cards", response_model=GiftCardResponse, status_code=status.HTTP_201_CREATED)
async def create_gift_card(
    gift_card_data: GiftCardCreate,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> GiftCardResponse:
    gift_card = await service.create_gift_card(store_id, gift_card_data)
    return GiftCardResponse.model_validate(gift_card)


@vendor_router.get("/gift-cards", response_model=List[GiftCardResponse])
async def list_gift_cards(
    is_active: Optional[bool] = True,
    store_id: int = Depends(get_current_vendor_store_id),
    service: PromotionsService = Depends(get_promotions_service),
) -> List[GiftCardResponse]:
    gift_cards = await service.list_store_gift_cards(store_id, is_active)
    return [GiftCardResponse.model_validate(g) for g in gift_cards]