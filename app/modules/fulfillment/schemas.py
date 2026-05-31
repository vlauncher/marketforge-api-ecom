from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.modules.fulfillment.models import ShipmentStatus


class TrackingEventCreate(BaseModel):
    status: str
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_data: Optional[dict] = None


class TrackingEventResponse(BaseModel):
    id: int
    shipment_id: int
    status: str
    location: Optional[str]
    description: Optional[str]
    timestamp: datetime
    raw_data: Optional[dict]

    model_config = {"from_attributes": True}


class ShipmentCreate(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None


class ShipmentUpdate(BaseModel):
    status: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class ShipmentResponse(BaseModel):
    id: int
    order_id: int
    carrier: Optional[str]
    tracking_number: Optional[str]
    status: str
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ShipmentDetailResponse(ShipmentResponse):
    tracking_events: List[TrackingEventResponse] = []

    model_config = {"from_attributes": True}


class ShipmentListResponse(BaseModel):
    items: List[ShipmentResponse]
    total: int
    limit: int
    offset: int