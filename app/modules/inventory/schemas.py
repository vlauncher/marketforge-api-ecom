from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.modules.inventory.models import MovementType


class InventoryLocationCreate(BaseModel):
    store_id: int
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    low_stock_threshold: int = 10


class InventoryLocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    is_active: Optional[bool] = None
    low_stock_threshold: Optional[int] = None


class InventoryLocationResponse(BaseModel):
    id: int
    store_id: int
    name: str
    address: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryItemCreate(BaseModel):
    location_id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(0, ge=0)
    low_stock_threshold: int = 10


class InventoryItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = None


class InventoryItemResponse(BaseModel):
    id: int
    location_id: int
    product_id: int
    variant_id: Optional[int]
    quantity: int
    reserved_quantity: int
    available_quantity: int
    low_stock_threshold: int

    model_config = {"from_attributes": True}


class InventoryAdjustment(BaseModel):
    quantity_change: int
    notes: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None


class ReservationItem(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)


class ReservationRequest(BaseModel):
    items: List[ReservationItem]
    order_id: Optional[str] = None


class ReservationResult(BaseModel):
    success: bool
    reserved_items: List[Dict[str, Any]] = []
    failed_items: List[Dict[str, Any]] = []
    message: str


class ReleaseRequest(BaseModel):
    order_id: str


class InventoryMovementResponse(BaseModel):
    id: int
    inventory_item_id: int
    quantity_change: int
    movement_type: MovementType
    reference_id: Optional[str]
    reference_type: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LowStockAlert(BaseModel):
    item: InventoryItemResponse
    below_threshold: bool