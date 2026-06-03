from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import UserRole
from app.modules.orders.schemas import (
    OrderResponse,
    OrderDetailResponse,
    OrderListResponse,
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
)
from app.modules.orders.service import OrderService
from app.modules.orders.models import OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])
vendor_router = APIRouter(prefix="/vendor/orders", tags=["Vendor Orders"])


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


@router.get("", response_model=OrderListResponse)
async def list_my_orders(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    orders, total = await service.list_user_orders(
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    order = await service.get_order_by_id(order_id)
    if order.user_id != current_user["user_id"] and current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("You can only view your own orders")
    return OrderDetailResponse.model_validate(order)


@router.get("/{order_number}/number", response_model=OrderDetailResponse)
async def get_order_by_number(
    order_number: str,
    service: OrderService = Depends(get_order_service),
) -> OrderDetailResponse:
    order = await service.get_order_by_number(order_number)
    return OrderDetailResponse.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    order = await service.get_order_by_id(order_id)
    if order.user_id != current_user["user_id"] and current_user["role"] != UserRole.ADMIN:
        raise ForbiddenError("You can only cancel your own orders")
    order = await service.cancel_order(order_id)
    return OrderResponse.model_validate(order)


@vendor_router.get("", response_model=OrderListResponse)
async def list_vendor_orders(
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    from app.modules.vendors.service import VendorService
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    if not vendor.stores:
        return OrderListResponse(items=[], total=0, limit=limit, offset=offset)
    store_id = vendor.stores[0].id

    orders, total = await OrderService(db).list_store_orders(
        store_id=store_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@vendor_router.post("/{order_id}/ship", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    order_id: int,
    shipment_data: ShipmentCreate,
    service: OrderService = Depends(get_order_service),
) -> ShipmentResponse:
    shipment = await service.create_shipment(
        order_id=order_id,
        carrier=shipment_data.carrier,
        tracking_number=shipment_data.tracking_number,
    )
    return ShipmentResponse.model_validate(shipment)


@vendor_router.patch("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    shipment_data: ShipmentUpdate,
    service: OrderService = Depends(get_order_service),
) -> ShipmentResponse:
    shipment = await service.update_shipment(
        shipment_id=shipment_id,
        status=shipment_data.status,
        tracking_number=shipment_data.tracking_number,
        shipped_at=shipment_data.shipped_at,
        delivered_at=shipment_data.delivered_at,
    )
    return ShipmentResponse.model_validate(shipment)


@vendor_router.get("/{order_id}/shipments", response_model=List[ShipmentResponse])
async def list_order_shipments(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> List[ShipmentResponse]:
    order = await service.get_order_by_id(order_id)
    return [ShipmentResponse.model_validate(s) for s in order.shipments]