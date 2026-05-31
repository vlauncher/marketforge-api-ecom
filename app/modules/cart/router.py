from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user, get_optional_user
from app.modules.cart.schemas import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
    CartMergeRequest,
)
from app.modules.cart.service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


async def get_cart_service(db: AsyncSession = Depends(get_db)) -> CartService:
    return CartService(db)


def cart_to_response(cart) -> CartResponse:
    return CartResponse(
        id=cart.id,
        user_id=cart.user_id,
        session_id=cart.session_id,
        store_id=cart.store_id,
        is_active=cart.is_active,
        items=[CartItemResponse.model_validate(i) for i in cart.items],
        item_count=sum(i.quantity for i in cart.items),
    )


@router.get("", response_model=CartResponse, summary="Get current cart")
async def get_cart(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    session_id: Optional[str] = Query(None),
    store_id: int = Query(1),
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """
    Get the current shopping cart.

    - Authenticated users get their persistent cart
    - Anonymous users get cart by session_id
    - Cart is created automatically if it doesn't exist
    """
    if current_user:
        cart = await service.get_cart_for_user(current_user["user_id"], store_id)
        if cart:
            return cart_to_response(cart)
        cart = await service.get_or_create_cart(user_id=current_user["user_id"], store_id=store_id)
    elif session_id:
        cart = await service.get_or_create_cart(session_id=session_id, store_id=store_id)
    else:
        raise ValueError("Either authentication or session_id is required")

    return cart_to_response(cart)


@router.post("/items", response_model=CartItemResponse, status_code=201, summary="Add item to cart")
async def add_item(
    item_data: CartItemCreate,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    session_id: Optional[str] = Query(None),
    store_id: int = Query(1),
    service: CartService = Depends(get_cart_service),
) -> CartItemResponse:
    """
    Add an item to the shopping cart.

    - **product_id**: ID of the product to add
    - **variant_id**: Optional specific variant
    - **quantity**: Number of items (must be > 0)
    - **selected_addons**: Optional addons to include
    """
    if current_user:
        cart = await service.get_cart_for_user(current_user["user_id"], store_id)
        if not cart:
            cart = await service.get_or_create_cart(user_id=current_user["user_id"], store_id=store_id)
    elif session_id:
        cart = await service.get_or_create_cart(session_id=session_id, store_id=store_id)
    else:
        raise ValueError("Either authentication or session_id is required")

    item = await service.add_item(cart.id, item_data)
    return CartItemResponse.model_validate(item)


@router.patch("/items/{item_id}", response_model=CartItemResponse)
async def update_item(
    item_id: int,
    item_data: CartItemUpdate,
    service: CartService = Depends(get_cart_service),
) -> CartItemResponse:
    item = await service.update_item(item_id, item_data)
    return CartItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(
    item_id: int,
    service: CartService = Depends(get_cart_service),
) -> None:
    await service.remove_item(item_id)


@router.post("/merge", response_model=CartResponse)
async def merge_carts(
    merge_request: CartMergeRequest,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    source_cart = await service.get_cart_for_user(merge_request.user_id, 1)
    target_cart = await service.get_or_create_cart(user_id=merge_request.user_id, store_id=1)

    if source_cart and source_cart.id != target_cart.id:
        cart = await service.merge_carts(source_cart.id, target_cart.id)
    else:
        cart = target_cart

    return cart_to_response(cart)


@router.delete("", status_code=204)
async def clear_cart(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
    session_id: Optional[str] = Query(None),
    store_id: int = Query(1),
    service: CartService = Depends(get_cart_service),
) -> None:
    if current_user:
        cart = await service.get_cart_for_user(current_user["user_id"], store_id)
        if cart:
            await service.clear_cart(cart.id)
    elif session_id:
        cart = await service.get_or_create_cart(session_id=session_id, store_id=store_id)
        await service.clear_cart(cart.id)