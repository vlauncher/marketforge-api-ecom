"""Commerce modules."""

from app.modules.identity.models import User, UserRole
from app.modules.identity.service import AuthService
from app.modules.identity.router import router as identity_router

from app.modules.vendors.models import Vendor, VendorProfile, VendorStatus
from app.modules.vendors.service import VendorService
from app.modules.vendors.router import router as vendor_router

from app.modules.storefronts.models import Store, StoreTheme, StorePage, StoreDomain
from app.modules.storefronts.service import StorefrontService
from app.modules.storefronts.router import router as storefront_router

from app.modules.catalog.models import (
    Category, Brand, Product, ProductVariant,
    ProductAttribute, ProductImage, AddonGroup, ProductAddon,
    ProductType,
)
from app.modules.catalog.service import CatalogService
from app.modules.catalog.router import router as catalog_router

from app.modules.pricing.models import Currency, ExchangeRate, Price
from app.modules.pricing.service import PricingService
from app.modules.pricing.router import router as pricing_router

from app.modules.inventory.models import InventoryLocation, InventoryItem, InventoryMovement, MovementType
from app.modules.inventory.service import InventoryService
from app.modules.inventory.router import router as inventory_router

__all__ = [
    "User",
    "UserRole",
    "AuthService",
    "identity_router",
    "Vendor",
    "VendorProfile",
    "VendorStatus",
    "VendorService",
    "vendor_router",
    "Store",
    "StoreTheme",
    "StorePage",
    "StoreDomain",
    "StorefrontService",
    "storefront_router",
    "Category",
    "Brand",
    "Product",
    "ProductVariant",
    "ProductAttribute",
    "ProductImage",
    "AddonGroup",
    "ProductAddon",
    "ProductType",
    "CatalogService",
    "catalog_router",
    "Currency",
    "ExchangeRate",
    "Price",
    "PricingService",
    "pricing_router",
    "InventoryLocation",
    "InventoryItem",
    "InventoryMovement",
    "MovementType",
    "InventoryService",
    "inventory_router",
]