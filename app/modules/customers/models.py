import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.identity.models import User
    from app.modules.catalog.models import Product


class LoyaltyTier(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class Wishlist(Base):
    __tablename__ = "wishlists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")
    product: Mapped["Product"] = relationship("Product")

    def __repr__(self) -> str:
        return f"<Wishlist(id={self.id}, user={self.user_id}, product={self.product_id})>"


class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[LoyaltyTier] = mapped_column(String(20), default=LoyaltyTier.BRONZE, nullable=False)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<LoyaltyAccount(id={self.id}, user={self.user_id}, points={self.points}, tier={self.tier})>"


from app.modules.identity.models import User
from app.modules.catalog.models import Product

User.wishlists = relationship("Wishlist", back_populates="user")
User.loyalty_account = relationship("LoyaltyAccount", back_populates="user", uselist=False)
Product.wishlists = relationship("Wishlist", back_populates="product")