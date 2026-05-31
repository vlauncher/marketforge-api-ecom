import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.vendors.models import Vendor


class PageType(str, enum.Enum):
    HOME = "home"
    ABOUT = "about"
    CONTACT = "contact"
    CUSTOM = "custom"


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="stores")
    theme: Mapped[Optional["StoreTheme"]] = relationship("StoreTheme", back_populates="store", uselist=False)
    pages: Mapped[list["StorePage"]] = relationship("StorePage", back_populates="store")
    domains: Mapped[list["StoreDomain"]] = relationship("StoreDomain", back_populates="store")

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name={self.name}, slug={self.slug})>"


class StoreTheme(Base):
    __tablename__ = "store_themes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), unique=True, nullable=False)
    colors: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    fonts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    layout: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    store: Mapped["Store"] = relationship("Store", back_populates="theme")

    def __repr__(self) -> str:
        return f"<StoreTheme(store_id={self.store_id})>"


class StorePage(Base):
    __tablename__ = "store_pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_type: Mapped[PageType] = mapped_column(SQLEnum(PageType), default=PageType.CUSTOM, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    store: Mapped["Store"] = relationship("Store", back_populates="pages")

    def __repr__(self) -> str:
        return f"<StorePage(id={self.id}, slug={self.slug}, store_id={self.store_id})>"


class StoreDomain(Base):
    __tablename__ = "store_domains"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    store: Mapped["Store"] = relationship("Store", back_populates="domains")

    def __repr__(self) -> str:
        return f"<StoreDomain(id={self.id}, domain={self.domain})>"