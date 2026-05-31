from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.orders.models import Order, Shipment, OrderStatus
from app.modules.fulfillment.models import TrackingEvent, ShipmentStatus
from app.modules.inventory.service import InventoryService


class FulfillmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_order_shipments(self, order_id: int) -> List[Shipment]:
        result = await self.db.execute(
            select(Shipment)
            .options(selectinload(Shipment.tracking_events))
            .where(Shipment.order_id == order_id)
        )
        return list(result.scalars().all())

    async def get_shipment_by_id(self, shipment_id: int) -> Shipment:
        result = await self.db.execute(
            select(Shipment)
            .options(selectinload(Shipment.tracking_events))
            .where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()
        if not shipment:
            raise NotFoundError("Shipment", str(shipment_id))
        return shipment

    async def create_shipment(
        self,
        order_id: int,
        carrier: Optional[str] = None,
        tracking_number: Optional[str] = None,
    ) -> Shipment:
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", str(order_id))

        if order.status not in (OrderStatus.CONFIRMED, OrderStatus.PROCESSING):
            raise ValidationError("Order must be confirmed or processing to create shipment")

        shipment = Shipment(
            order_id=order_id,
            carrier=carrier,
            tracking_number=tracking_number,
            status=ShipmentStatus.PENDING.value,
        )
        self.db.add(shipment)
        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment

    async def update_shipment_status(
        self,
        shipment_id: int,
        status: str,
        tracking_number: Optional[str] = None,
        carrier: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        raw_data: Optional[dict] = None,
    ) -> Shipment:
        shipment = await self.get_shipment_by_id(shipment_id)

        old_status = shipment.status
        shipment.status = status

        if tracking_number:
            shipment.tracking_number = tracking_number
        if carrier:
            shipment.carrier = carrier

        if status == ShipmentStatus.SHIPPED.value and old_status != ShipmentStatus.SHIPPED.value:
            shipment.shipped_at = datetime.utcnow()

        if status == ShipmentStatus.DELIVERED.value:
            shipment.delivered_at = datetime.utcnow()

        tracking_event = TrackingEvent(
            shipment_id=shipment_id,
            status=status,
            location=location,
            description=description,
            timestamp=datetime.utcnow(),
            raw_data=raw_data,
        )
        self.db.add(tracking_event)

        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment

    async def release_inventory_for_shipment(self, shipment_id: int) -> bool:
        shipment = await self.get_shipment_by_id(shipment_id)

        order = await self.db.execute(
            select(Order).where(Order.id == shipment.order_id)
        )
        order = order.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", str(shipment.order_id))

        inventory_service = InventoryService(self.db)
        try:
            await inventory_service.release_stock(order_id=str(order.id))
            return True
        except Exception:
            return False

    async def commit_inventory_for_shipment(self, shipment_id: int) -> bool:
        shipment = await self.get_shipment_by_id(shipment_id)

        order_result = await self.db.execute(
            select(Order).where(Order.id == shipment.order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", str(shipment.order_id))

        inventory_service = InventoryService(self.db)
        try:
            await inventory_service.commit_reserved_stock(order_id=str(order.id))
            return True
        except Exception:
            return False

    async def add_tracking_event(
        self,
        shipment_id: int,
        status: str,
        location: Optional[str] = None,
        description: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        raw_data: Optional[dict] = None,
    ) -> TrackingEvent:
        shipment = await self.get_shipment_by_id(shipment_id)

        event = TrackingEvent(
            shipment_id=shipment_id,
            status=status,
            location=location,
            description=description,
            timestamp=timestamp or datetime.utcnow(),
            raw_data=raw_data,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_tracking_history(self, shipment_id: int) -> List[TrackingEvent]:
        result = await self.db.execute(
            select(TrackingEvent)
            .where(TrackingEvent.shipment_id == shipment_id)
            .order_by(TrackingEvent.timestamp.desc())
        )
        return list(result.scalars().all())