from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.modules.cart.models import Cart as CartModel


class CartItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(1, ge=1)
    selected_addons: Optional[Dict[str, Any]] = None


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)
    selected_addons: Optional[Dict[str, Any]] = None


class CartItemResponse(BaseModel):
    id: int
    cart_id: int
    product_id: int
    variant_id: Optional[int]
    quantity: int
    selected_addons: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: int
    user_id: Optional[int]
    session_id: Optional[str]
    store_id: int
    is_active: bool
    items: List[CartItemResponse] = []
    item_count: int = 0

    model_config = {"from_attributes": True}


class CartMergeRequest(BaseModel):
    session_id: str
    user_id: int