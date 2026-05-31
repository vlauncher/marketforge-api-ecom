from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

from app.modules.catalog.models import ProductType


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: int
    parent_id: Optional[int]
    name: str
    slug: str
    description: Optional[str]
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class CategoryTreeResponse(BaseModel):
    id: int
    name: str
    slug: str
    children: list["CategoryTreeResponse"] = []

    model_config = {"from_attributes": True}


class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = None
    description: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str
    logo_url: Optional[str]
    description: Optional[str]
    is_active: bool

    model_config = {"from_attributes": True}


class ProductVariantCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    attributes: Optional[Dict[str, Any]] = None
    price_delta: float = 0.0
    is_active: bool = True


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    attributes: Optional[Dict[str, Any]] = None
    price_delta: Optional[float] = None
    is_active: Optional[bool] = None


class ProductVariantResponse(BaseModel):
    id: int
    product_id: int
    sku: str
    attributes: Optional[Dict[str, Any]]
    price_delta: float
    is_active: bool

    model_config = {"from_attributes": True}


class ProductAttributeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    values: Optional[Dict[str, Any]] = None


class ProductAttributeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    values: Optional[Dict[str, Any]] = None


class ProductAttributeResponse(BaseModel):
    id: int
    product_id: int
    name: str
    values: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class ProductImageCreate(BaseModel):
    url: str = Field(..., max_length=500)
    alt_text: Optional[str] = Field(None, max_length=255)
    sort_order: int = 0
    is_primary: bool = False


class ProductImageUpdate(BaseModel):
    url: Optional[str] = Field(None, max_length=500)
    alt_text: Optional[str] = Field(None, max_length=255)
    sort_order: Optional[int] = None
    is_primary: Optional[bool] = None


class ProductImageResponse(BaseModel):
    id: int
    product_id: int
    url: str
    alt_text: Optional[str]
    sort_order: int
    is_primary: bool

    model_config = {"from_attributes": True}


class ProductAddonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price_delta: float = 0.0
    sort_order: int = 0


class ProductAddonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_delta: Optional[float] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ProductAddonResponse(BaseModel):
    id: int
    addon_group_id: int
    name: str
    description: Optional[str]
    price_delta: float
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class AddonGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_required: bool = False
    min_select: int = 0
    max_select: Optional[int] = None
    sort_order: int = 0


class AddonGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_required: Optional[bool] = None
    min_select: Optional[int] = None
    max_select: Optional[int] = None
    sort_order: Optional[int] = None


class AddonGroupResponse(BaseModel):
    id: int
    product_id: int
    name: str
    description: Optional[str]
    is_required: bool
    min_select: int
    max_select: Optional[int]
    sort_order: int
    addons: list[ProductAddonResponse] = []

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    product_type: ProductType = ProductType.SIMPLE
    status: str = "draft"
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    product_type: Optional[ProductType] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    store_id: int
    category_id: Optional[int]
    brand_id: Optional[int]
    name: str
    slug: str
    description: Optional[str]
    product_type: ProductType
    status: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductDetailResponse(BaseModel):
    id: int
    store_id: int
    category_id: Optional[int]
    brand_id: Optional[int]
    name: str
    slug: str
    description: Optional[str]
    product_type: ProductType
    status: str
    is_active: bool
    created_at: datetime
    variants: list[ProductVariantResponse] = []
    attributes: list[ProductAttributeResponse] = []
    images: list[ProductImageResponse] = []
    addon_groups: list[AddonGroupResponse] = []

    model_config = {"from_attributes": True}


class ProductSearchParams(BaseModel):
    query: Optional[str] = None
    category_slug: Optional[str] = None
    brand_slug: Optional[str] = None
    store_slug: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    is_active: bool = True
    sort_by: str = "created_at"
    sort_order: str = "desc"
    limit: int = 50
    offset: int = 0