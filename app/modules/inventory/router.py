from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.vendors.service import VendorService
from app.modules.inventory.schemas import (
    InventoryLocationCreate,
    InventoryLocationUpdate,
    InventoryLocationResponse,
    InventoryItemCreate,
    InventoryItemUpdate,
    InventoryItemResponse,
    InventoryAdjustment,
    ReservationRequest,
    ReservationResult,
    ReleaseRequest,
    InventoryMovementResponse,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(tags=["Inventory"])
vendor_router = APIRouter(prefix="/vendor/inventory", tags=["Vendor Inventory"])


async def get_inventory_service(db: AsyncSession = Depends(get_db)) -> InventoryService:
    return InventoryService(db)


async def get_current_vendor_store_id(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    if not vendor.stores:
        raise ValueError("Vendor has no stores")
    return vendor.stores[0].id


@vendor_router.get("/locations", response_model=List[InventoryLocationResponse])
async def list_locations(
    store_id: int = Depends(get_current_vendor_store_id),
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryLocationResponse]:
    locations = await service.list_locations(store_id)
    return [InventoryLocationResponse.model_validate(l) for l in locations]


@vendor_router.post("/locations", response_model=InventoryLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: InventoryLocationCreate,
    store_id: int = Depends(get_current_vendor_store_id),
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryLocationResponse:
    location_data.store_id = store_id
    location = await service.create_location(location_data)
    return InventoryLocationResponse.model_validate(location)


@vendor_router.patch("/locations/{location_id}", response_model=InventoryLocationResponse)
async def update_location(
    location_id: int,
    location_data: InventoryLocationUpdate,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryLocationResponse:
    location = await service.update_location(location_id, location_data)
    return InventoryLocationResponse.model_validate(location)


@vendor_router.get("/", response_model=List[InventoryItemResponse])
async def list_inventory(
    location_id: Optional[int] = None,
    product_id: Optional[int] = None,
    store_id: int = Depends(get_current_vendor_store_id),
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryItemResponse]:
    items = await service.list_inventory(
        location_id=location_id,
        product_id=product_id,
        store_id=store_id,
    )
    return [
        InventoryItemResponse(
            id=item.id,
            location_id=item.location_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            reserved_quantity=item.reserved_quantity,
            available_quantity=item.available_quantity,
            low_stock_threshold=item.low_stock_threshold,
        )
        for item in items
    ]


@vendor_router.post("/adjust", response_model=InventoryItemResponse)
async def adjust_stock(
    location_id: int,
    product_id: int,
    adjustment: InventoryAdjustment,
    variant_id: Optional[int] = None,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryItemResponse:
    item = await service.adjust_stock(
        location_id=location_id,
        product_id=product_id,
        quantity_change=adjustment.quantity_change,
        notes=adjustment.notes,
        reference_id=adjustment.reference_id,
        reference_type=adjustment.reference_type,
        variant_id=variant_id,
    )
    return InventoryItemResponse(
        id=item.id,
        location_id=item.location_id,
        product_id=item.product_id,
        variant_id=item.variant_id,
        quantity=item.quantity,
        reserved_quantity=item.reserved_quantity,
        available_quantity=item.available_quantity,
        low_stock_threshold=item.low_stock_threshold,
    )


@vendor_router.post("/reserve", response_model=ReservationResult)
async def reserve_stock(
    reservation: ReservationRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> ReservationResult:
    result = await service.reserve_stock(
        items=reservation.items,
        order_id=reservation.order_id or "pending",
    )
    return result


@vendor_router.post("/release", response_model=List[InventoryItemResponse])
async def release_stock(
    release: ReleaseRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryItemResponse]:
    items = await service.release_stock(order_id=release.order_id)
    return [
        InventoryItemResponse(
            id=item.id,
            location_id=item.location_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            reserved_quantity=item.reserved_quantity,
            available_quantity=item.available_quantity,
            low_stock_threshold=item.low_stock_threshold,
        )
        for item in items
    ]


@vendor_router.get("/low-stock")
async def get_low_stock(
    store_id: int = Depends(get_current_vendor_store_id),
    service: InventoryService = Depends(get_inventory_service),
) -> List[Dict[str, Any]]:
    items = await service.get_low_stock_items(store_id)
    return [
        {
            "item": InventoryItemResponse(
                id=item["item"].id,
                location_id=item["item"].location_id,
                product_id=item["item"].product_id,
                variant_id=item["item"].variant_id,
                quantity=item["item"].quantity,
                reserved_quantity=item["item"].reserved_quantity,
                available_quantity=item["item"].available_quantity,
                low_stock_threshold=item["item"].low_stock_threshold,
            ),
            "below_threshold": item["below_threshold"],
        }
        for item in items
    ]


@vendor_router.get("/movements", response_model=List[InventoryMovementResponse])
async def get_movements(
    item_id: Optional[int] = None,
    product_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryMovementResponse]:
    movements = await service.get_movement_history(
        item_id=item_id,
        product_id=product_id,
        limit=limit,
    )
    return [InventoryMovementResponse.model_validate(m) for m in movements]