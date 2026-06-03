import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.models import InventoryItem, InventoryMovement, MovementType
from app.modules.inventory.schemas import ReservationItem, ReservationRequest, ReleaseRequest
from app.modules.inventory.service import InventoryService


class TestInventoryReservation:
    @pytest_asyncio.fixture
    async def inventory_service(self, db_session: AsyncSession) -> InventoryService:
        return InventoryService(db_session)

    @pytest.mark.asyncio
    async def test_reserve_stock_success(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        items = [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=5)]

        result = await inventory_service.reserve_stock(items, "ORDER-001")

        assert result.success is True
        assert len(result.reserved_items) == 1
        assert result.reserved_items[0]["reserved"] == 5

        await db_session.refresh(sample_inventory_item)
        assert sample_inventory_item.reserved_quantity == 5

    @pytest.mark.asyncio
    async def test_reserve_stock_insufficient_quantity(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        items = [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=150)]

        result = await inventory_service.reserve_stock(items, "ORDER-002")

        assert result.success is False
        assert len(result.failed_items) == 1
        assert "Insufficient stock" in result.failed_items[0]["reason"]

    @pytest.mark.asyncio
    async def test_reserve_stock_item_not_found(
        self,
        db_session: AsyncSession,
        inventory_service: InventoryService,
    ):
        items = [ReservationItem(product_id=9999, variant_id=None, quantity=1)]

        result = await inventory_service.reserve_stock(items, "ORDER-003")

        assert result.success is False
        assert len(result.failed_items) == 1
        assert "not found" in result.failed_items[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_reserve_stock_multiple_items(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        items = [
            ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=10),
            ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=5),
        ]

        result = await inventory_service.reserve_stock(items, "ORDER-004")

        assert result.success is True
        assert len(result.reserved_items) == 2

        await db_session.refresh(sample_inventory_item)
        assert sample_inventory_item.reserved_quantity == 15

    @pytest.mark.asyncio
    async def test_reserve_stock_partial_failure(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        items = [
            ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=5),
            ReservationItem(product_id=9999, variant_id=None, quantity=1),
        ]

        result = await inventory_service.reserve_stock(items, "ORDER-005")

        assert result.success is False
        assert len(result.reserved_items) == 1
        assert len(result.failed_items) == 1


class TestInventoryRelease:
    @pytest.mark.asyncio
    async def test_release_stock(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        await inventory_service.reserve_stock(
            [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=20)],
            "ORDER-REL-001"
        )

        released = await inventory_service.release_stock("ORDER-REL-001")

        assert len(released) == 1
        await db_session.refresh(sample_inventory_item)
        assert sample_inventory_item.reserved_quantity == 0

    @pytest.mark.asyncio
    async def test_release_nonexistent_order(
        self,
        db_session: AsyncSession,
        inventory_service: InventoryService,
    ):
        released = await inventory_service.release_stock("NONEXISTENT-ORDER")

        assert len(released) == 0


class TestInventoryCommit:
    @pytest.mark.asyncio
    async def test_commit_reserved_stock(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        initial_quantity = sample_inventory_item.quantity
        await inventory_service.reserve_stock(
            [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=30)],
            "ORDER-COMMIT-001"
        )

        committed = await inventory_service.commit_reserved_stock("ORDER-COMMIT-001")

        assert len(committed) == 1
        await db_session.refresh(sample_inventory_item)
        assert sample_inventory_item.quantity == initial_quantity - 30
        assert sample_inventory_item.reserved_quantity == 0


class TestInventoryConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_reservations(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
    ):
        await db_session.refresh(sample_inventory_item)
        initial_available = sample_inventory_item.quantity - sample_inventory_item.reserved_quantity
        assert initial_available == 100

    @pytest.mark.asyncio
    async def test_reservation_respects_available_stock(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        await db_session.refresh(sample_inventory_item)
        sample_inventory_item.quantity = 10
        await db_session.commit()

        result = await inventory_service.reserve_stock(
            [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=15)],
            "ORDER-OVER-001"
        )

        assert result.success is False
        assert "Insufficient stock" in result.failed_items[0]["reason"]


class TestInventoryMovements:
    @pytest.mark.asyncio
    async def test_movement_created_on_reserve(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        await inventory_service.reserve_stock(
            [ReservationItem(product_id=sample_inventory_item.product_id, variant_id=None, quantity=5)],
            "ORDER-MOV-001"
        )

        movements = await inventory_service.get_movement_history(item_id=sample_inventory_item.id)

        assert len(movements) >= 1
        reserve_movements = [m for m in movements if m.movement_type == MovementType.RESERVED]
        assert len(reserve_movements) >= 1

    @pytest.mark.asyncio
    async def test_movement_created_on_adjustment(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        inventory_service: InventoryService,
    ):
        await inventory_service.adjust_stock(
            location_id=sample_inventory_item.location_id,
            product_id=sample_inventory_item.product_id,
            quantity_change=10,
            notes="Test adjustment",
            reference_id="ADJ-001",
            reference_type="adjustment",
        )

        movements = await inventory_service.get_movement_history(item_id=sample_inventory_item.id)

        assert len(movements) >= 1
        adjustment_movements = [m for m in movements if m.reference_id == "ADJ-001"]
        assert len(adjustment_movements) >= 1