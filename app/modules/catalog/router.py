from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.storefronts.service import StorefrontService
from app.modules.vendors.service import VendorService
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTreeResponse,
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductDetailResponse,
    ProductVariantCreate,
    ProductVariantUpdate,
    ProductVariantResponse,
    ProductAttributeCreate,
    ProductAttributeResponse,
    ProductImageCreate,
    ProductImageResponse,
    AddonGroupCreate,
    AddonGroupResponse,
    ProductAddonCreate,
    ProductAddonResponse,
)
from app.modules.catalog.service import CatalogService
from app.modules.catalog.search import CatalogSearchService

router = APIRouter(tags=["Catalog"])
vendor_router = APIRouter(prefix="/vendor", tags=["Vendor Catalog"])

storefront_service = StorefrontService


async def get_catalog_service(db: AsyncSession = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


async def get_search_service(db: AsyncSession = Depends(get_db)) -> CatalogSearchService:
    return CatalogSearchService(db)


async def get_current_vendor_store(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> int:
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    if not vendor.stores:
        raise ValueError("Vendor has no stores")
    return vendor.stores[0].id


@router.get("/stores/{store_slug}/products", response_model=list[ProductResponse])
async def list_store_products(
    store_slug: str,
    is_active: Optional[bool] = True,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: CatalogService = Depends(get_catalog_service),
) -> list[ProductResponse]:
    from app.modules.storefronts.models import Store
    result = await service.db.execute(select(Store).where(Store.slug == store_slug))
    store = result.scalar_one_or_none()
    if not store:
        return []
    products = await service.list_store_products(store.id, is_active, limit, offset)
    return [ProductResponse.model_validate(p) for p in products]


@router.get("/stores/{store_slug}/products/{product_slug}", response_model=ProductDetailResponse)
async def get_product_detail(
    store_slug: str,
    product_slug: str,
    service: CatalogService = Depends(get_catalog_service),
) -> ProductDetailResponse:
    product = await service.get_product_by_slug(store_slug, product_slug)
    return ProductDetailResponse.model_validate(product)


@router.get("/stores/{store_slug}/collections", response_model=list[dict])
async def get_collections(
    store_slug: str,
    limit: int = Query(10, ge=1, le=50),
    search_service: CatalogSearchService = Depends(get_search_service),
) -> list[dict]:
    collections = await search_service.get_featured_collections(store_slug, limit)
    return [
        {
            "category": c["category"],
            "products": [ProductResponse.model_validate(p) for p in c["products"]],
        }
        for c in collections
    ]


@router.get("/products/search")
async def search_products(
    query: Optional[str] = None,
    category_slug: Optional[str] = None,
    brand_slug: Optional[str] = None,
    store_slug: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_active: bool = True,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search_service: CatalogSearchService = Depends(get_search_service),
) -> dict:
    result = await search_service.search_products(
        query=query,
        category_slug=category_slug,
        brand_slug=brand_slug,
        store_slug=store_slug,
        min_price=min_price,
        max_price=max_price,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [ProductResponse.model_validate(p) for p in result["items"]],
        "total": result["total"],
        "limit": result["limit"],
        "offset": result["offset"],
    }


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    parent_id: Optional[int] = None,
    is_active: bool = True,
    service: CatalogService = Depends(get_catalog_service),
) -> list[CategoryResponse]:
    categories = await service.list_categories(parent_id, is_active)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.get("/brands", response_model=list[BrandResponse])
async def list_brands(
    is_active: bool = True,
    service: CatalogService = Depends(get_catalog_service),
) -> list[BrandResponse]:
    brands = await service.list_brands(is_active)
    return [BrandResponse.model_validate(b) for b in brands]


@vendor_router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    store_id: int = Depends(get_current_vendor_store),
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductResponse:
    product = await service.create_product(product_data, store_id, current_user)
    return ProductResponse.model_validate(product)


@vendor_router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductResponse:
    product = await service.update_product(product_id, product_data, current_user)
    return ProductResponse.model_validate(product)


@vendor_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> None:
    await service.delete_product(product_id)


@vendor_router.post("/products/{product_id}/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def add_variant(
    product_id: int,
    variant_data: ProductVariantCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductVariantResponse:
    variant = await service.add_variant(product_id, variant_data)
    return ProductVariantResponse.model_validate(variant)


@vendor_router.patch("/products/{product_id}/variants/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    product_id: int,
    variant_id: int,
    variant_data: ProductVariantUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductVariantResponse:
    variant = await service.update_variant(variant_id, variant_data)
    return ProductVariantResponse.model_validate(variant)


@vendor_router.post("/products/{product_id}/attributes", response_model=ProductAttributeResponse, status_code=status.HTTP_201_CREATED)
async def add_attribute(
    product_id: int,
    attr_data: ProductAttributeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductAttributeResponse:
    attribute = await service.add_attribute(product_id, attr_data)
    return ProductAttributeResponse.model_validate(attribute)


@vendor_router.post("/products/{product_id}/images", response_model=ProductImageResponse, status_code=status.HTTP_201_CREATED)
async def add_image(
    product_id: int,
    image_data: ProductImageCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductImageResponse:
    image = await service.add_image(product_id, image_data)
    return ProductImageResponse.model_validate(image)


@vendor_router.post("/products/{product_id}/addon-groups", response_model=AddonGroupResponse, status_code=status.HTTP_201_CREATED)
async def add_addon_group(
    product_id: int,
    group_data: AddonGroupCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> AddonGroupResponse:
    group = await service.add_addon_group(product_id, group_data)
    return AddonGroupResponse.model_validate(group)


@vendor_router.post("/addon-groups/{group_id}/addons", response_model=ProductAddonResponse, status_code=status.HTTP_201_CREATED)
async def add_addon(
    group_id: int,
    addon_data: ProductAddonCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ProductAddonResponse:
    addon = await service.add_addon(group_id, addon_data)
    return ProductAddonResponse.model_validate(addon)