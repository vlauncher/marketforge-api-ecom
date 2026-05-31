from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.modules.inventory.models import InventoryLocation, InventoryItem, InventoryMovement, MovementType
from app.modules.inventory.schemas import ReservationItem, ReservationResult


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_location(self, location_data) -> InventoryLocation:
        location = InventoryLocation(**location_data.model_dump())
        self.db.add(location)
        await self.db.flush()
        await self.db.refresh(location)
        return location

    async def get_location_by_id(self, location_id: int) -> InventoryLocation:
        result = await self.db.execute(
            select(InventoryLocation).where(InventoryLocation.id == location_id)
        )
        location = result.scalar_one_or_none()
        if not location:
            raise NotFoundError("InventoryLocation", str(location_id))
        return location

    async def list_locations(self, store_id: int, is_active: bool = True) -> List[InventoryLocation]:
        query = select(InventoryLocation).where(InventoryLocation.store_id == store_id)
        if is_active is not None:
            query = query.where(InventoryLocation.is_active == is_active)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_location(self, location_id: int, location_data) -> InventoryLocation:
        location = await self.get_location_by_id(location_id)
        for key, value in location_data.model_dump(exclude_unset=True).items():
            setattr(location, key, value)
        await self.db.flush()
        await self.db.refresh(location)
        return location

    async def get_or_create_inventory_item(
        self,
        location_id: int,
        product_id: int,
        variant_id: Optional[int] = None,
    ) -> InventoryItem:
        query = select(InventoryItem).where(
            and_(
                InventoryItem.location_id == location_id,
                InventoryItem.product_id == product_id,
                InventoryItem.variant_id == variant_id,
            )
        )
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()

        if not item:
            item = InventoryItem(
                location_id=location_id,
                product_id=product_id,
                variant_id=variant_id,
                quantity=0,
                reserved_quantity=0,
            )
            self.db.add(item)
            await self.db.flush()
            await self.db.refresh(item)

        return item

    async def get_inventory_item(self, item_id: int) -> InventoryItem:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.movements))
            .where(InventoryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("InventoryItem", str(item_id))
        return item

    async def list_inventory(
        self,
        location_id: Optional[int] = None,
        product_id: Optional[int] = None,
        store_id: Optional[int] = None,
    ) -> List[InventoryItem]:
        query = select(InventoryItem).options(selectinload(InventoryItem.location))

        if location_id:
            query = query.where(InventoryItem.location_id == location_id)
        if product_id:
            query = query.where(InventoryItem.product_id == product_id)
        if store_id:
            query = query.join(InventoryItem.location).where(InventoryLocation.store_id == store_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def adjust_stock(
        self,
        location_id: int,
        product_id: int,
        quantity_change: int,
        notes: Optional[str] = None,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        variant_id: Optional[int] = None,
    ) -> InventoryItem:
        item = await self.get_or_create_inventory_item(location_id, product_id, variant_id)

        new_quantity = item.quantity + quantity_change
        if new_quantity < 0:
            raise ValidationError(
                f"Cannot reduce quantity by {quantity_change}. Current: {item.quantity}, Available: {item.available_quantity}"
            )

        item.quantity = new_quantity

        movement = InventoryMovement(
            inventory_item_id=item.id,
            quantity_change=quantity_change,
            movement_type=MovementType.ADJUSTED if quantity_change != 0 else MovementType.RECEIVED,
            notes=notes,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def reserve_stock(
        self,
        items: List[ReservationItem],
        order_id: str,
    ) -> ReservationResult:
        reserved_items = []
        failed_items = []

        for item_req in items:
            result = await self.db.execute(
                select(InventoryItem).where(
                    and_(
                        InventoryItem.product_id == item_req.product_id,
                        InventoryItem.variant_id == item_req.variant_id,
                    )
                ).with_for_update()
            )
            item = result.scalar_one_or_none()

            if not item:
                failed_items.append({
                    "product_id": item_req.product_id,
                    "variant_id": item_req.variant_id,
                    "reason": "Inventory item not found",
                })
                continue

            available = item.quantity - item.reserved_quantity
            if available < item_req.quantity:
                failed_items.append({
                    "product_id": item_req.product_id,
                    "variant_id": item_req.variant_id,
                    "requested": item_req.quantity,
                    "available": available,
                    "reason": "Insufficient stock",
                })
                continue

            item.reserved_quantity += item_req.quantity

            movement = InventoryMovement(
                inventory_item_id=item.id,
                quantity_change=item_req.quantity,
                movement_type=MovementType.RESERVED,
                reference_id=order_id,
                reference_type="order",
            )
            self.db.add(movement)
            reserved_items.append({
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "reserved": item_req.quantity,
            })

        await self.db.flush()

        return ReservationResult(
            success=len(failed_items) == 0,
            reserved_items=reserved_items,
            failed_items=failed_items,
            message="All items reserved" if not failed_items else "Some items could not be reserved",
        )

    async def release_stock(
        self,
        order_id: str,
    ) -> List[InventoryItem]:
        result = await self.db.execute(
            select(InventoryMovement).where(
                and_(
                    InventoryMovement.reference_id == order_id,
                    InventoryMovement.reference_type == "order",
                    InventoryMovement.movement_type == MovementType.RESERVED,
                )
            )
        )
        movements = list(result.scalars().all())

        released_items = []
        for movement in movements:
            item = await self.get_inventory_item(movement.inventory_item_id)
            item.reserved_quantity = max(0, item.reserved_quantity - abs(movement.quantity_change))

            release_movement = InventoryMovement(
                inventory_item_id=item.id,
                quantity_change=-abs(movement.quantity_change),
                movement_type=MovementType.RELEASED,
                reference_id=order_id,
                reference_type="order",
            )
            self.db.add(release_movement)
            released_items.append(item)

        await self.db.flush()
        return released_items

    async def commit_reserved_stock(
        self,
        order_id: str,
    ) -> List[InventoryItem]:
        result = await self.db.execute(
            select(InventoryMovement).where(
                and_(
                    InventoryMovement.reference_id == order_id,
                    InventoryMovement.reference_type == "order",
                    InventoryMovement.movement_type == MovementType.RESERVED,
                )
            )
        )
        movements = list(result.scalars().all())

        committed_items = []
        for movement in movements:
            item = await self.get_inventory_item(movement.inventory_item_id)

            item.quantity -= abs(movement.quantity_change)
            item.reserved_quantity = max(0, item.reserved_quantity - abs(movement.quantity_change))

            commit_movement = InventoryMovement(
                inventory_item_id=item.id,
                quantity_change=-abs(movement.quantity_change),
                movement_type=MovementType.SOLD,
                reference_id=order_id,
                reference_type="order",
            )
            self.db.add(commit_movement)
            committed_items.append(item)

        await self.db.flush()
        return committed_items

    async def get_low_stock_items(self, store_id: int) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(InventoryItem)
            .join(InventoryItem.location)
            .where(
                and_(
                    InventoryLocation.store_id == store_id,
                    InventoryItem.quantity <= InventoryItem.low_stock_threshold,
                )
            )
        )
        items = list(result.scalars().all())

        return [
            {
                "item": item,
                "below_threshold": item.quantity <= item.low_stock_threshold,
            }
            for item in items
        ]

    async def get_movement_history(
        self,
        item_id: Optional[int] = None,
        product_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[InventoryMovement]:
        query = select(InventoryMovement).options(
            selectinload(InventoryMovement.item)
        )

        if item_id:
            query = query.where(InventoryMovement.inventory_item_id == item_id)
        if product_id:
            query = query.join(InventoryMovement.item).where(
                InventoryItem.product_id == product_id
            )

        query = query.order_by(InventoryMovement.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


from app.modules.inventory.models import InventoryLocation
InventoryService.__init__.__annotations__["db"] = AsyncSession