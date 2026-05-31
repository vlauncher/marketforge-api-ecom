from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import CartItemCreate, CartItemUpdate


class CartService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_cart(
        self,
        store_id: int,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> Cart:
        if user_id:
            result = await self.db.execute(
                select(Cart).where(
                    and_(Cart.user_id == user_id, Cart.store_id == store_id, Cart.is_active == True)
                )
            )
        elif session_id:
            result = await self.db.execute(
                select(Cart).where(
                    and_(Cart.session_id == session_id, Cart.store_id == store_id, Cart.is_active == True)
                )
            )
        else:
            raise ValidationError("Either user_id or session_id is required")

        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(
                user_id=user_id,
                session_id=session_id,
                store_id=store_id,
                is_active=True,
            )
            self.db.add(cart)
            await self.db.flush()
            await self.db.refresh(cart)

        return cart

    async def get_cart_by_id(self, cart_id: int) -> Cart:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.id == cart_id)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            raise NotFoundError("Cart", str(cart_id))
        return cart

    async def get_cart_for_user(self, user_id: int, store_id: int) -> Optional[Cart]:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items))
            .where(
                and_(
                    Cart.user_id == user_id,
                    Cart.store_id == store_id,
                    Cart.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def add_item(
        self,
        cart_id: int,
        item_data: CartItemCreate,
    ) -> CartItem:
        existing = await self.db.execute(
            select(CartItem).where(
                and_(
                    CartItem.cart_id == cart_id,
                    CartItem.product_id == item_data.product_id,
                    CartItem.variant_id == item_data.variant_id,
                )
            )
        )
        existing_item = existing.scalar_one_or_none()

        if existing_item:
            existing_item.quantity += item_data.quantity
            if item_data.selected_addons:
                existing_item.selected_addons = item_data.selected_addons
            await self.db.flush()
            await self.db.refresh(existing_item)
            return existing_item

        item = CartItem(
            cart_id=cart_id,
            **item_data.model_dump(),
        )
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update_item(
        self,
        item_id: int,
        item_data: CartItemUpdate,
    ) -> CartItem:
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("CartItem", str(item_id))

        if item_data.quantity is not None:
            item.quantity = item_data.quantity
        if item_data.selected_addons is not None:
            item.selected_addons = item_data.selected_addons

        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def remove_item(self, item_id: int) -> None:
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("CartItem", str(item_id))

        await self.db.delete(item)
        await self.db.flush()

    async def clear_cart(self, cart_id: int) -> None:
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        )
        items = result.scalars().all()
        for item in items:
            await self.db.delete(item)
        await self.db.flush()

    async def merge_carts(
        self,
        source_cart_id: int,
        target_cart_id: int,
    ) -> Cart:
        source_cart = await self.get_cart_by_id(source_cart_id)
        target_cart = await self.get_cart_by_id(target_cart_id)

        for source_item in source_cart.items:
            existing = await self.db.execute(
                select(CartItem).where(
                    and_(
                        CartItem.cart_id == target_cart_id,
                        CartItem.product_id == source_item.product_id,
                        CartItem.variant_id == source_item.variant_id,
                    )
                )
            )
            existing_item = existing.scalar_one_or_none()

            if existing_item:
                existing_item.quantity += source_item.quantity
            else:
                new_item = CartItem(
                    cart_id=target_cart_id,
                    product_id=source_item.product_id,
                    variant_id=source_item.variant_id,
                    quantity=source_item.quantity,
                    selected_addons=source_item.selected_addons,
                )
                self.db.add(new_item)

        source_cart.is_active = False
        await self.db.flush()
        return await self.get_cart_by_id(target_cart_id)

    async def get_cart_item_count(self, cart_id: int) -> int:
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart_id)
        )
        items = result.scalars().all()
        return sum(item.quantity for item in items)