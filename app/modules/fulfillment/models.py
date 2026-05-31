import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.orders.models import Shipment


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="tracking_events")

    def __repr__(self) -> str:
        return f"<TrackingEvent(id={self.id}, shipment={self.shipment_id}, status={self.status})>"


from app.modules.orders.models import Shipment
Shipment.tracking_events = relationship("TrackingEvent", back_populates="shipment", cascade="all, delete-orphan")