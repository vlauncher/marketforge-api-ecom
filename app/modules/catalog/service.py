from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError
from app.modules.catalog.models import (
    Category, Brand, Product, ProductVariant,
    ProductAttribute, ProductImage, AddonGroup, ProductAddon,
    ProductType,
)


class CatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_slug(self, name: str) -> str:
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    async def create_category(self, category_data) -> Category:
        slug = category_data.slug or self._generate_slug(category_data.name)
        existing = await self.db.execute(select(Category).where(Category.slug == slug))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Category with slug '{slug}' already exists")

        category = Category(**category_data.model_dump(exclude_unset=True))
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get_category_by_id(self, category_id: int) -> Category:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError("Category", str(category_id))
        return category

    async def get_category_by_slug(self, slug: str) -> Category:
        result = await self.db.execute(select(Category).where(Category.slug == slug))
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError("Category", slug)
        return category

    async def list_categories(self, parent_id: Optional[int] = None, is_active: bool = True) -> List[Category]:
        query = select(Category)
        if parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        if is_active is not None:
            query = query.where(Category.is_active == is_active)
        query = query.order_by(Category.sort_order, Category.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_category(self, category_id: int, category_data) -> Category:
        category = await self.get_category_by_id(category_id)
        for key, value in category_data.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def create_brand(self, brand_data) -> Brand:
        slug = brand_data.slug or self._generate_slug(brand_data.name)
        existing = await self.db.execute(select(Brand).where(Brand.slug == slug))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Brand with slug '{slug}' already exists")

        brand = Brand(**brand_data.model_dump(exclude_unset=True))
        self.db.add(brand)
        await self.db.flush()
        await self.db.refresh(brand)
        return brand

    async def get_brand_by_id(self, brand_id: int) -> Brand:
        result = await self.db.execute(select(Brand).where(Brand.id == brand_id))
        brand = result.scalar_one_or_none()
        if not brand:
            raise NotFoundError("Brand", str(brand_id))
        return brand

    async def get_brand_by_slug(self, slug: str) -> Brand:
        result = await self.db.execute(select(Brand).where(Brand.slug == slug))
        brand = result.scalar_one_or_none()
        if not brand:
            raise NotFoundError("Brand", slug)
        return brand

    async def list_brands(self, is_active: bool = True) -> List[Brand]:
        query = select(Brand)
        if is_active is not None:
            query = query.where(Brand.is_active == is_active)
        query = query.order_by(Brand.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_brand(self, brand_id: int, brand_data) -> Brand:
        brand = await self.get_brand_by_id(brand_id)
        for key, value in brand_data.model_dump(exclude_unset=True).items():
            setattr(brand, key, value)
        await self.db.flush()
        await self.db.refresh(brand)
        return brand

    async def create_product(
        self,
        product_data,
        store_id: int,
        current_user: Dict[str, Any],
    ) -> Product:
        slug = product_data.slug or self._generate_slug(product_data.name)

        existing = await self.db.execute(
            select(Product).where(
                and_(Product.store_id == store_id, Product.slug == slug)
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Product with slug '{slug}' already exists in this store")

        product = Product(
            store_id=store_id,
            **product_data.model_dump(exclude_unset=True),
        )
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def get_product_by_id(self, product_id: int) -> Product:
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.attributes),
                selectinload(Product.images),
                selectinload(Product.addon_groups).selectinload(AddonGroup.addons),
            )
            .where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Product", str(product_id))
        return product

    async def get_product_by_slug(self, store_slug: str, product_slug: str) -> Product:
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.attributes),
                selectinload(Product.images),
                selectinload(Product.addon_groups).selectinload(AddonGroup.addons),
            )
            .join(Product.store)
            .where(and_(Product.slug == product_slug))
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Product", product_slug)
        return product

    async def list_store_products(
        self,
        store_id: int,
        is_active: Optional[bool] = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        query = select(Product).where(Product.store_id == store_id)
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        query = query.order_by(Product.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_product(
        self,
        product_id: int,
        product_data,
        current_user: Dict[str, Any],
    ) -> Product:
        product = await self.get_product_by_id(product_id)
        for key, value in product_data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def delete_product(self, product_id: int) -> None:
        product = await self.get_product_by_id(product_id)
        await self.db.delete(product)
        await self.db.flush()

    async def add_variant(self, product_id: int, variant_data) -> ProductVariant:
        await self.get_product_by_id(product_id)

        existing = await self.db.execute(select(ProductVariant).where(ProductVariant.sku == variant_data.sku))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Variant with SKU '{variant_data.sku}' already exists")

        variant = ProductVariant(
            product_id=product_id,
            **variant_data.model_dump(),
        )
        self.db.add(variant)
        await self.db.flush()
        await self.db.refresh(variant)
        return variant

    async def update_variant(self, variant_id: int, variant_data) -> ProductVariant:
        result = await self.db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
        variant = result.scalar_one_or_none()
        if not variant:
            raise NotFoundError("ProductVariant", str(variant_id))

        for key, value in variant_data.model_dump(exclude_unset=True).items():
            setattr(variant, key, value)
        await self.db.flush()
        await self.db.refresh(variant)
        return variant

    async def add_attribute(self, product_id: int, attr_data) -> ProductAttribute:
        await self.get_product_by_id(product_id)

        attribute = ProductAttribute(
            product_id=product_id,
            **attr_data.model_dump(),
        )
        self.db.add(attribute)
        await self.db.flush()
        await self.db.refresh(attribute)
        return attribute

    async def add_image(self, product_id: int, image_data) -> ProductImage:
        await self.get_product_by_id(product_id)

        if image_data.is_primary:
            await self.db.execute(
                select(ProductImage)
                .where(and_(ProductImage.product_id == product_id, ProductImage.is_primary == True))
            )

        image = ProductImage(
            product_id=product_id,
            **image_data.model_dump(),
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    async def add_addon_group(self, product_id: int, group_data) -> AddonGroup:
        await self.get_product_by_id(product_id)

        group = AddonGroup(
            product_id=product_id,
            **group_data.model_dump(),
        )
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def add_addon(self, group_id: int, addon_data) -> ProductAddon:
        result = await self.db.execute(select(AddonGroup).where(AddonGroup.id == group_id))
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("AddonGroup", str(group_id))

        addon = ProductAddon(
            addon_group_id=group_id,
            **addon_data.model_dump(),
        )
        self.db.add(addon)
        await self.db.flush()
        await self.db.refresh(addon)
        return addon