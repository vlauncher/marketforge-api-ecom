from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

from app.modules.storefronts.models import PageType


class ThemeColors(BaseModel):
    primary: Optional[str] = "#000000"
    secondary: Optional[str] = "#ffffff"
    accent: Optional[str] = "#cccccc"


class ThemeFonts(BaseModel):
    heading: Optional[str] = "Arial"
    body: Optional[str] = "Arial"


class ThemeLayout(BaseModel):
    header_style: Optional[str] = "standard"
    footer_style: Optional[str] = "standard"
    product_grid: Optional[str] = "3-column"


class StoreThemeCreate(BaseModel):
    colors: Optional[ThemeColors] = None
    fonts: Optional[ThemeFonts] = None
    layout: Optional[ThemeLayout] = None


class StoreThemeUpdate(BaseModel):
    colors: Optional[ThemeColors] = None
    fonts: Optional[ThemeFonts] = None
    layout: Optional[ThemeLayout] = None


class StoreThemeResponse(BaseModel):
    id: int
    store_id: int
    colors: Optional[Dict[str, Any]]
    fonts: Optional[Dict[str, Any]]
    layout: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class StorePageCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    page_type: PageType = PageType.CUSTOM
    is_published: bool = True
    sort_order: int = 0


class StorePageUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    page_type: Optional[PageType] = None
    is_published: Optional[bool] = None
    sort_order: Optional[int] = None


class StorePageResponse(BaseModel):
    id: int
    store_id: int
    slug: str
    title: str
    content: Optional[str]
    page_type: PageType
    is_published: bool
    sort_order: int

    model_config = {"from_attributes": True}


class StoreDomainCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    is_primary: bool = False


class StoreDomainResponse(BaseModel):
    id: int
    store_id: int
    domain: str
    is_primary: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class StoreCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class StoreResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreDetailResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    theme: Optional[StoreThemeResponse] = None
    pages: list[StorePageResponse] = []
    domains: list[StoreDomainResponse] = []

    model_config = {"from_attributes": True}