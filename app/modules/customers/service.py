from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.customers.models import Wishlist, LoyaltyAccount, LoyaltyTier


class CustomersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_to_wishlist(self, user_id: int, product_id: int) -> Wishlist:
        existing = await self.db.execute(
            select(Wishlist).where(
                and_(
                    Wishlist.user_id == user_id,
                    Wishlist.product_id == product_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Product already in wishlist")

        wishlist_item = Wishlist(
            user_id=user_id,
            product_id=product_id,
        )
        self.db.add(wishlist_item)
        await self.db.flush()
        await self.db.refresh(wishlist_item)
        return wishlist_item

    async def remove_from_wishlist(self, user_id: int, product_id: int) -> None:
        result = await self.db.execute(
            select(Wishlist).where(
                and_(
                    Wishlist.user_id == user_id,
                    Wishlist.product_id == product_id,
                )
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Wishlist item", str(product_id))

        await self.db.delete(item)
        await self.db.flush()

    async def get_user_wishlist(self, user_id: int) -> List[Wishlist]:
        result = await self.db.execute(
            select(Wishlist)
            .where(Wishlist.user_id == user_id)
            .order_by(Wishlist.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_or_create_loyalty_account(self, user_id: int) -> LoyaltyAccount:
        result = await self.db.execute(
            select(LoyaltyAccount).where(LoyaltyAccount.user_id == user_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            account = LoyaltyAccount(
                user_id=user_id,
                points=0,
                tier=LoyaltyTier.BRONZE,
                lifetime_points=0,
            )
            self.db.add(account)
            await self.db.flush()
            await self.db.refresh(account)

        return account

    async def add_points(
        self,
        user_id: int,
        points: int,
        description: Optional[str] = None,
    ) -> LoyaltyAccount:
        account = await self.get_or_create_loyalty_account(user_id)

        account.points += points
        account.lifetime_points += points
        account.updated_at = datetime.now(timezone.utc)

        account.tier = self._calculate_tier(account.lifetime_points)

        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def redeem_points(
        self,
        user_id: int,
        points: int,
    ) -> LoyaltyAccount:
        account = await self.get_or_create_loyalty_account(user_id)

        if account.points < points:
            raise ValidationError(
                f"Insufficient points. You have {account.points} points."
            )

        account.points -= points
        account.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(account)
        return account

    def _calculate_tier(self, lifetime_points: int) -> LoyaltyTier:
        if lifetime_points >= 10000:
            return LoyaltyTier.PLATINUM
        elif lifetime_points >= 5000:
            return LoyaltyTier.GOLD
        elif lifetime_points >= 1000:
            return LoyaltyTier.SILVER
        else:
            return LoyaltyTier.BRONZE

    def get_tier_info(self, tier: LoyaltyTier) -> Dict[str, Any]:
        tier_data = {
            LoyaltyTier.BRONZE: {
                "min_points": 0,
                "max_points": 999,
                "multiplier": 1.0,
                "benefits": ["Basic rewards", "Birthday bonus"],
            },
            LoyaltyTier.SILVER: {
                "min_points": 1000,
                "max_points": 4999,
                "multiplier": 1.25,
                "benefits": ["All Bronze benefits", "Early access", "Free shipping on orders over $50"],
            },
            LoyaltyTier.GOLD: {
                "min_points": 5000,
                "max_points": 9999,
                "multiplier": 1.5,
                "benefits": ["All Silver benefits", "Priority support", "Exclusive sales"],
            },
            LoyaltyTier.PLATINUM: {
                "min_points": 10000,
                "max_points": None,
                "multiplier": 2.0,
                "benefits": ["All Gold benefits", "VIP support", "Exclusive events", "Personal shopper"],
            },
        }
        return tier_data.get(tier, tier_data[LoyaltyTier.BRONZE])

    async def get_loyalty_info(self, user_id: int) -> Dict[str, Any]:
        account = await self.get_or_create_loyalty_account(user_id)
        tier_info = self.get_tier_info(account.tier)

        return {
            "account": account,
            "tier_info": tier_info,
            "points_to_next_tier": self._points_to_next_tier(account.tier, account.lifetime_points),
        }

    def _points_to_next_tier(self, current_tier: LoyaltyTier, lifetime_points: int) -> Optional[int]:
        tier_info = self.get_tier_info(current_tier)
        next_tier_points = tier_info.get("max_points")
        if next_tier_points is None:
            return None
        return int(next_tier_points + 1 - lifetime_points)