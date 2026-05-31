from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.modules.orders.models import Order, OrderItem, Shipment, OrderStatus


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_order_number(self) -> str:
        from datetime import datetime
        import random
        import string
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_chars}"

    async def create_order(
        self,
        user_id: Optional[int],
        store_id: int,
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        billing_address: Optional[Dict[str, Any]],
        subtotal: float,
        tax_amount: float,
        shipping_amount: float,
        discount_amount: float,
        total: float,
        currency_code: str,
        idempotency_key: Optional[str],
        notes: Optional[str],
    ) -> Order:
        if idempotency_key:
            existing = await self.db.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
            existing_order = existing.scalar_one_or_none()
            if existing_order:
                return existing_order

        order_number = self._generate_order_number()

        order = Order(
            user_id=user_id,
            store_id=store_id,
            order_number=order_number,
            status=OrderStatus.PENDING,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total=total,
            currency_code=currency_code,
            shipping_address=shipping_address,
            billing_address=billing_address or shipping_address,
            idempotency_key=idempotency_key,
            notes=notes,
        )
        self.db.add(order)
        await self.db.flush()

        for item_data in items:
            item = OrderItem(
                order_id=order.id,
                **item_data,
                total_price=item_data["quantity"] * item_data["unit_price"],
            )
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def get_order_by_id(self, order_id: int) -> Order:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipments))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", str(order_id))
        return order

    async def get_order_by_number(self, order_number: str) -> Order:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.shipments))
            .where(Order.order_number == order_number)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundError("Order", order_number)
        return order

    async def get_order_by_idempotency_key(self, key: str) -> Optional[Order]:
        result = await self.db.execute(
            select(Order).where(Order.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_user_orders(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Order], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Order).where(Order.user_id == user_id)
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        orders = list(result.scalars().all())
        return orders, total

    async def list_store_orders(
        self,
        store_id: int,
        status: Optional[OrderStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Order], int]:
        conditions = [Order.store_id == store_id]
        if status:
            conditions.append(Order.status == status)

        count_result = await self.db.execute(
            select(func.count()).select_from(Order).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        orders = list(result.scalars().all())
        return orders, total

    async def update_order_status(
        self,
        order_id: int,
        status: OrderStatus,
    ) -> Order:
        order = await self.get_order_by_id(order_id)
        order.status = status
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def cancel_order(self, order_id: int) -> Order:
        order = await self.get_order_by_id(order_id)
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValidationError("Cannot cancel order that has been shipped or delivered")
        order.status = OrderStatus.CANCELLED
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def create_shipment(
        self,
        order_id: int,
        carrier: Optional[str],
        tracking_number: Optional[str],
    ) -> Shipment:
        order = await self.get_order_by_id(order_id)
        if order.status not in (OrderStatus.CONFIRMED, OrderStatus.PROCESSING):
            raise ValidationError("Order must be confirmed or processing to add shipment")

        shipment = Shipment(
            order_id=order_id,
            carrier=carrier,
            tracking_number=tracking_number,
            status="pending",
        )
        self.db.add(shipment)
        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment

    async def update_shipment(
        self,
        shipment_id: int,
        status: Optional[str],
        tracking_number: Optional[str],
        shipped_at: Optional[datetime],
        delivered_at: Optional[datetime],
    ) -> Shipment:
        result = await self.db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()
        if not shipment:
            raise NotFoundError("Shipment", str(shipment_id))

        if status is not None:
            shipment.status = status
        if tracking_number is not None:
            shipment.tracking_number = tracking_number
        if shipped_at is not None:
            shipment.shipped_at = shipped_at
        if delivered_at is not None:
            shipment.delivered_at = delivered_at

        await self.db.flush()
        await self.db.refresh(shipment)
        return shipment