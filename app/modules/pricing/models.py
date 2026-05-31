from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.catalog.models import Product, ProductVariant, ProductAddon


class Currency(Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    prices: Mapped[list["Price"]] = relationship("Price", back_populates="currency")
    exchange_rates_from: Mapped[list["ExchangeRate"]] = relationship(
        "ExchangeRate",
        foreign_keys="ExchangeRate.from_currency_id",
        back_populates="from_currency",
    )
    exchange_rates_to: Mapped[list["ExchangeRate"]] = relationship(
        "ExchangeRate",
        foreign_keys="ExchangeRate.to_currency_id",
        back_populates="to_currency",
    )

    def __repr__(self) -> str:
        return f"<Currency(code={self.code}, symbol={self.symbol})>"


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    to_currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    from_currency: Mapped["Currency"] = relationship(
        "Currency",
        foreign_keys=[from_currency_id],
        back_populates="exchange_rates_from",
    )
    to_currency: Mapped["Currency"] = relationship(
        "Currency",
        foreign_keys=[to_currency_id],
        back_populates="exchange_rates_to",
    )

    __table_args__ = (
        UniqueConstraint("from_currency_id", "to_currency_id", "effective_at", name="uq_exchange_rate_currency_pair_effective"),
    )

    def __repr__(self) -> str:
        return f"<ExchangeRate(from={self.from_currency_id}, to={self.to_currency_id}, rate={self.rate})>"


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    addon_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_addons.id"), nullable=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    effective_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    currency: Mapped["Currency"] = relationship("Currency", overlaps="prices")
    product: Mapped[Optional["Product"]] = relationship("Product", foreign_keys=[product_id], overlaps="prices")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant", foreign_keys=[variant_id], overlaps="prices")
    addon: Mapped[Optional["ProductAddon"]] = relationship("ProductAddon", foreign_keys=[addon_id], overlaps="prices")

    __table_args__ = (
        UniqueConstraint("product_id", "variant_id", "addon_id", "currency_id", name="uq_price_product_variant_addon_currency"),
    )

    def __repr__(self) -> str:
        return f"<Price(product={self.product_id}, amount={self.amount}, currency={self.currency_id})>"


from app.modules.catalog.models import Product, ProductVariant, ProductAddon
Product.prices = relationship("Price", foreign_keys=[Price.product_id], overlaps="product")
ProductVariant.prices = relationship("Price", foreign_keys=[Price.variant_id], overlaps="variant")
ProductAddon.prices = relationship("Price", foreign_keys=[Price.addon_id], overlaps="addon")