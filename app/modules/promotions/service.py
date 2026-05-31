from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.promotions.models import Coupon, Promotion, GiftCard, DiscountType


class PromotionsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_coupon(
        self,
        code: str,
        order_subtotal: float,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[Coupon], float, str]:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code)
        )
        coupon = result.scalar_one_or_none()

        if not coupon:
            return False, None, 0.0, "Coupon not found"

        if not coupon.is_active:
            return False, None, 0.0, "Coupon is not active"

        now = datetime.now(timezone.utc)
        if coupon.valid_from > now:
            return False, None, 0.0, "Coupon is not yet valid"

        if coupon.valid_until and coupon.valid_until < now:
            return False, None, 0.0, "Coupon has expired"

        if coupon.max_uses and coupon.uses_count >= coupon.max_uses:
            return False, None, 0.0, "Coupon usage limit reached"

        if order_subtotal < coupon.min_order_amount:
            return (
                False,
                None,
                0.0,
                f"Minimum order amount of {coupon.min_order_amount} required",
            )

        discount_amount = self._calculate_discount(
            coupon.discount_type,
            coupon.discount_value,
            order_subtotal,
            coupon.max_discount_amount,
        )

        return True, coupon, discount_amount, "Coupon is valid"

    def _calculate_discount(
        self,
        discount_type: DiscountType,
        discount_value: float,
        subtotal: float,
        max_discount: Optional[float] = None,
    ) -> float:
        if discount_type == DiscountType.PERCENTAGE:
            discount = subtotal * (discount_value / 100.0)
        elif discount_type == DiscountType.FIXED:
            discount = discount_value
        else:
            discount = 0.0

        if max_discount is not None and discount > max_discount:
            discount = max_discount

        if discount > subtotal:
            discount = subtotal

        return round(discount, 2)

    async def redeem_coupon(self, coupon_id: int) -> Coupon:
        result = await self.db.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            raise NotFoundError("Coupon", str(coupon_id))

        coupon.uses_count += 1
        await self.db.flush()
        await self.db.refresh(coupon)
        return coupon

    async def create_coupon(
        self,
        store_id: int,
        coupon_data,
    ) -> Coupon:
        existing = await self.db.execute(
            select(Coupon).where(Coupon.code == coupon_data.code)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"Coupon with code '{coupon_data.code}' already exists")

        coupon = Coupon(
            store_id=store_id,
            **coupon_data.model_dump(),
        )
        self.db.add(coupon)
        await self.db.flush()
        await self.db.refresh(coupon)
        return coupon

    async def get_coupon_by_id(self, coupon_id: int) -> Coupon:
        result = await self.db.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            raise NotFoundError("Coupon", str(coupon_id))
        return coupon

    async def list_store_coupons(
        self,
        store_id: int,
        is_active: Optional[bool] = True,
    ) -> List[Coupon]:
        query = select(Coupon).where(Coupon.store_id == store_id)
        if is_active is not None:
            query = query.where(Coupon.is_active == is_active)
        query = query.order_by(Coupon.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_coupon(
        self,
        coupon_id: int,
        coupon_data,
    ) -> Coupon:
        coupon = await self.get_coupon_by_id(coupon_id)
        for key, value in coupon_data.model_dump(exclude_unset=True).items():
            setattr(coupon, key, value)
        await self.db.flush()
        await self.db.refresh(coupon)
        return coupon

    async def create_promotion(
        self,
        store_id: int,
        promotion_data,
    ) -> Promotion:
        promotion = Promotion(
            store_id=store_id,
            **promotion_data.model_dump(),
        )
        self.db.add(promotion)
        await self.db.flush()
        await self.db.refresh(promotion)
        return promotion

    async def get_promotion_by_id(self, promotion_id: int) -> Promotion:
        result = await self.db.execute(
            select(Promotion).where(Promotion.id == promotion_id)
        )
        promotion = result.scalar_one_or_none()
        if not promotion:
            raise NotFoundError("Promotion", str(promotion_id))
        return promotion

    async def list_store_promotions(
        self,
        store_id: int,
        is_active: Optional[bool] = True,
    ) -> List[Promotion]:
        query = select(Promotion).where(Promotion.store_id == store_id)
        if is_active is not None:
            query = query.where(Promotion.is_active == is_active)
        query = query.order_by(Promotion.priority.desc(), Promotion.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_promotion(
        self,
        promotion_id: int,
        promotion_data,
    ) -> Promotion:
        promotion = await self.get_promotion_by_id(promotion_id)
        for key, value in promotion_data.model_dump(exclude_unset=True).items():
            setattr(promotion, key, value)
        await self.db.flush()
        await self.db.refresh(promotion)
        return promotion

    async def validate_gift_card(self, code: str) -> Tuple[bool, Optional[GiftCard], float, str]:
        result = await self.db.execute(
            select(GiftCard).where(GiftCard.code == code)
        )
        gift_card = result.scalar_one_or_none()

        if not gift_card:
            return False, None, 0.0, "Gift card not found"

        if not gift_card.is_active:
            return False, None, 0.0, "Gift card is not active"

        now = datetime.now(timezone.utc)
        if gift_card.expires_at and gift_card.expires_at < now:
            return False, None, 0.0, "Gift card has expired"

        if gift_card.current_balance <= 0:
            return False, None, 0.0, "Gift card has no balance"

        return (
            True,
            gift_card,
            gift_card.current_balance,
            "Gift card is valid",
        )

    async def create_gift_card(
        self,
        store_id: int,
        gift_card_data,
    ) -> GiftCard:
        existing = await self.db.execute(
            select(GiftCard).where(GiftCard.code == gift_card_data.code)
        )
        if existing.scalar_one_or_none():
            raise ValidationError(f"Gift card with code '{gift_card_data.code}' already exists")

        gift_card = GiftCard(
            store_id=store_id,
            **gift_card_data.model_dump(),
        )
        self.db.add(gift_card)
        await self.db.flush()
        await self.db.refresh(gift_card)
        return gift_card

    async def get_gift_card_by_id(self, gift_card_id: int) -> GiftCard:
        result = await self.db.execute(
            select(GiftCard).where(GiftCard.id == gift_card_id)
        )
        gift_card = result.scalar_one_or_none()
        if not gift_card:
            raise NotFoundError("GiftCard", str(gift_card_id))
        return gift_card

    async def redeem_gift_card(
        self,
        code: str,
        amount: float,
    ) -> Tuple[GiftCard, float]:
        valid, gift_card, balance, _ = await self.validate_gift_card(code)

        if not valid or not gift_card:
            raise ValidationError("Gift card is not valid")

        if amount > balance:
            raise ValidationError(f"Amount {amount} exceeds gift card balance {balance}")

        gift_card.current_balance -= amount
        await self.db.flush()
        await self.db.refresh(gift_card)

        return gift_card, amount

    async def list_store_gift_cards(
        self,
        store_id: int,
        is_active: Optional[bool] = True,
    ) -> List[GiftCard]:
        query = select(GiftCard).where(GiftCard.store_id == store_id)
        if is_active is not None:
            query = query.where(GiftCard.is_active == is_active)
        query = query.order_by(GiftCard.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())