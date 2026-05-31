from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import UserRole
from app.modules.fulfillment.schemas import (
    ShipmentCreate,
    ShipmentUpdate,
    ShipmentResponse,
    ShipmentDetailResponse,
    ShipmentListResponse,
    TrackingEventCreate,
    TrackingEventResponse,
)
from app.modules.fulfillment.service import FulfillmentService

router = APIRouter(prefix="/orders", tags=["Fulfillment"])
vendor_router = APIRouter(prefix="/vendor", tags=["Vendor Fulfillment"])


async def get_fulfillment_service(db: AsyncSession = Depends(get_db)) -> FulfillmentService:
    return FulfillmentService(db)


@router.get("/{order_id}/shipments", response_model=ShipmentListResponse)
async def list_order_shipments(
    order_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> ShipmentListResponse:
    shipments = await service.get_order_shipments(order_id)
    return ShipmentListResponse(
        items=[ShipmentResponse.model_validate(s) for s in shipments],
        total=len(shipments),
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}/shipments/{shipment_id}", response_model=ShipmentDetailResponse)
async def get_shipment_details(
    order_id: int,
    shipment_id: int,
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> ShipmentDetailResponse:
    shipment = await service.get_shipment_by_id(shipment_id)
    return ShipmentDetailResponse.model_validate(shipment)


@router.post("/{order_id}/ship", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    order_id: int,
    shipment_data: ShipmentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> ShipmentResponse:
    shipment = await service.create_shipment(
        order_id=order_id,
        carrier=shipment_data.carrier,
        tracking_number=shipment_data.tracking_number,
    )
    return ShipmentResponse.model_validate(shipment)


@vendor_router.post("/orders/{order_id}/ship", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def vendor_create_shipment(
    order_id: int,
    shipment_data: ShipmentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
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
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> ShipmentResponse:
    shipment = await service.update_shipment_status(
        shipment_id=shipment_id,
        status=shipment_data.status,
        tracking_number=shipment_data.tracking_number,
        carrier=shipment_data.carrier,
    )
    return ShipmentResponse.model_validate(shipment)


@vendor_router.patch("/shipments/{shipment_id}/status", response_model=ShipmentResponse)
async def update_shipment_status(
    shipment_id: int,
    status: str,
    location: Optional[str] = None,
    description: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> ShipmentResponse:
    shipment = await service.update_shipment_status(
        shipment_id=shipment_id,
        status=status,
        location=location,
        description=description,
    )
    return ShipmentResponse.model_validate(shipment)


@vendor_router.post("/shipments/{shipment_id}/tracking", response_model=TrackingEventResponse, status_code=status.HTTP_201_CREATED)
async def add_tracking_event(
    shipment_id: int,
    event_data: TrackingEventCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> TrackingEventResponse:
    event = await service.add_tracking_event(
        shipment_id=shipment_id,
        status=event_data.status,
        location=event_data.location,
        description=event_data.description,
        timestamp=event_data.timestamp,
        raw_data=event_data.raw_data,
    )
    return TrackingEventResponse.model_validate(event)


@vendor_router.get("/shipments/{shipment_id}/tracking", response_model=List[TrackingEventResponse])
async def get_tracking_history(
    shipment_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> List[TrackingEventResponse]:
    events = await service.get_tracking_history(shipment_id)
    return [TrackingEventResponse.model_validate(e) for e in events]


@vendor_router.post("/shipments/{shipment_id}/commit-inventory", status_code=status.HTTP_204_NO_CONTENT)
async def commit_inventory(
    shipment_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> None:
    await service.commit_inventory_for_shipment(shipment_id)


@vendor_router.post("/shipments/{shipment_id}/release-inventory", status_code=status.HTTP_204_NO_CONTENT)
async def release_inventory(
    shipment_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: FulfillmentService = Depends(get_fulfillment_service),
) -> None:
    await service.release_inventory_for_shipment(shipment_id)