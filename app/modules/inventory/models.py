import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, Float, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.storefronts.models import Store
    from app.modules.catalog.models import Product, ProductVariant


class MovementType(str, enum.Enum):
    RECEIVED = "received"
    SOLD = "sold"
    RESERVED = "reserved"
    RELEASED = "released"
    ADJUSTED = "adjusted"
    RETURNED = "returned"


class InventoryLocation(Base):
    __tablename__ = "inventory_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    store: Mapped["Store"] = relationship("Store")
    items: Mapped[list["InventoryItem"]] = relationship("InventoryItem", back_populates="location")

    def __repr__(self) -> str:
        return f"<InventoryLocation(id={self.id}, name={self.name})>"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("inventory_locations.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    location: Mapped["InventoryLocation"] = relationship("InventoryLocation", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    movements: Mapped[list["InventoryMovement"]] = relationship("InventoryMovement", back_populates="item")

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity

    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, product={self.product_id}, qty={self.quantity})>"


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(SQLEnum(MovementType), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    item: Mapped["InventoryItem"] = relationship("InventoryItem", back_populates="movements")

    def __repr__(self) -> str:
        return f"<InventoryMovement(id={self.id}, type={self.movement_type}, delta={self.quantity_change})>"


from app.modules.storefronts.models import Store
from app.modules.catalog.models import Product, ProductVariant

Store.locations = relationship("InventoryLocation", back_populates="store")