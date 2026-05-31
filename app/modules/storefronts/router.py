from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.models import UserRole
from app.modules.identity.dependencies import get_current_user
from app.modules.vendors.service import VendorService
from app.modules.storefronts.schemas import (
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    StoreDetailResponse,
    StoreThemeCreate,
    StoreThemeUpdate,
    StoreThemeResponse,
    StorePageCreate,
    StorePageUpdate,
    StorePageResponse,
    StoreDomainCreate,
    StoreDomainResponse,
)
from app.modules.storefronts.service import StorefrontService

router = APIRouter(tags=["Storefronts"])

storefront_service = StorefrontService


async def get_storefront_service(db: AsyncSession = Depends(get_db)) -> StorefrontService:
    return StorefrontService(db)


async def get_current_vendor(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if current_user["role"] == UserRole.ADMIN:
        return {"vendor_id": None, "is_admin": True, **current_user}
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    return {"vendor_id": vendor.id, "is_admin": False, **current_user}


@router.get("/stores", response_model=list[StoreResponse])
async def list_stores(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: StorefrontService = Depends(get_storefront_service),
) -> list[StoreResponse]:
    stores = await service.list_active_stores(limit=limit, offset=offset)
    return [StoreResponse.model_validate(s) for s in stores]


@router.get("/stores/{slug}", response_model=StoreDetailResponse)
async def get_store(
    slug: str,
    service: StorefrontService = Depends(get_storefront_service),
) -> StoreDetailResponse:
    store = await service.get_store_by_slug(slug)
    return StoreDetailResponse.model_validate(store)


@router.get("/stores/{store_slug}/pages/{page_slug}", response_model=StorePageResponse)
async def get_store_page(
    store_slug: str,
    page_slug: str,
    service: StorefrontService = Depends(get_storefront_service),
) -> StorePageResponse:
    page = await service.get_store_page(store_slug, page_slug)
    return StorePageResponse.model_validate(page)


vendor_router = APIRouter(prefix="/vendor/stores", tags=["Vendor Stores"])


@vendor_router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    store_data: StoreCreate,
    current_vendor: Dict[str, Any] = Depends(get_current_vendor),
    service: StorefrontService = Depends(get_storefront_service),
) -> StoreResponse:
    store = await service.create_store(store_data, current_vendor["vendor_id"])
    return StoreResponse.model_validate(store)


@vendor_router.patch("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    store_data: StoreUpdate,
    current_vendor: Dict[str, Any] = Depends(get_current_vendor),
    service: StorefrontService = Depends(get_storefront_service),
) -> StoreResponse:
    store = await service.update_store(
        store_id, store_data, current_vendor,
        vendor_id=current_vendor["vendor_id"] if not current_vendor["is_admin"] else None,
    )
    return StoreResponse.model_validate(store)


@vendor_router.post("/{store_id}/theme", response_model=StoreThemeResponse)
async def update_theme(
    store_id: int,
    theme_data: StoreThemeCreate,
    current_vendor: Dict[str, Any] = Depends(get_current_vendor),
    service: StorefrontService = Depends(get_storefront_service),
) -> StoreThemeResponse:
    theme = await service.create_or_update_theme(store_id, theme_data, current_vendor)
    return StoreThemeResponse.model_validate(theme)


@vendor_router.post("/{store_id}/pages", response_model=StorePageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    store_id: int,
    page_data: StorePageCreate,
    current_vendor: Dict[str, Any] = Depends(get_current_vendor),
    service: StorefrontService = Depends(get_storefront_service),
) -> StorePageResponse:
    page = await service.create_page(store_id, page_data, current_vendor)
    return StorePageResponse.model_validate(page)


@vendor_router.patch("/{store_id}/pages/{page_id}", response_model=StorePageResponse)
async def update_page(
    store_id: int,
    page_id: int,
    page_data: StorePageUpdate,
    current_vendor: Dict[str, Any] = Depends(get_current_vendor),
    service: StorefrontService = Depends(get_storefront_service),
) -> StorePageResponse:
    page = await service.update_page(store_id, page_id, page_data, current_vendor)
    return StorePageResponse.model_validate(page)