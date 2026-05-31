from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.customers.schemas import (
    WishlistItemResponse,
    WishlistResponse,
    LoyaltyAccountResponse,
    RedeemPointsRequest,
    LoyaltyTierInfo,
)
from app.modules.customers.service import CustomersService

router = APIRouter(prefix="/customers", tags=["Customers"])


async def get_customers_service(db: AsyncSession = Depends(get_db)) -> CustomersService:
    return CustomersService(db)


@router.post("/wishlist/{product_id}", status_code=201)
async def add_to_wishlist(
    product_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CustomersService = Depends(get_customers_service),
) -> Dict[str, str]:
    await service.add_to_wishlist(current_user["user_id"], product_id)
    return {"status": "added"}


@router.delete("/wishlist/{product_id}", status_code=204)
async def remove_from_wishlist(
    product_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CustomersService = Depends(get_customers_service),
) -> None:
    await service.remove_from_wishlist(current_user["user_id"], product_id)


@router.get("/wishlist", response_model=WishlistResponse)
async def get_wishlist(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CustomersService = Depends(get_customers_service),
) -> WishlistResponse:
    items = await service.get_user_wishlist(current_user["user_id"])
    return WishlistResponse(
        items=[WishlistItemResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/loyalty", response_model=LoyaltyAccountResponse)
async def get_loyalty_account(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CustomersService = Depends(get_customers_service),
) -> LoyaltyAccountResponse:
    account = await service.get_or_create_loyalty_account(current_user["user_id"])
    return LoyaltyAccountResponse.model_validate(account)


@router.post("/loyalty/redeem", response_model=LoyaltyAccountResponse)
async def redeem_points(
    request: RedeemPointsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CustomersService = Depends(get_customers_service),
) -> LoyaltyAccountResponse:
    account = await service.redeem_points(
        user_id=current_user["user_id"],
        points=request.points,
    )
    return LoyaltyAccountResponse.model_validate(account)


@router.get("/loyalty/tiers", response_model=List[LoyaltyTierInfo])
async def get_loyalty_tiers(
    service: CustomersService = Depends(get_customers_service),
) -> List[LoyaltyTierInfo]:
    from app.modules.customers.models import LoyaltyTier
    return [
        LoyaltyTierInfo(
            tier=tier,
            **service.get_tier_info(tier),
        )
        for tier in LoyaltyTier
    ]