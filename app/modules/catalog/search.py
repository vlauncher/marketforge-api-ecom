from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import Product, Category, Brand, Store, ProductVariant


class CatalogSearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_products(
        self,
        query: Optional[str] = None,
        category_slug: Optional[str] = None,
        brand_slug: Optional[str] = None,
        store_slug: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        is_active: bool = True,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        conditions = []

        if is_active is not None:
            conditions.append(Product.is_active == is_active)

        if query:
            search_term = f"%{query}%"
            conditions.append(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )

        if category_slug:
            category_result = await self.db.execute(
                select(Category).where(Category.slug == category_slug)
            )
            category = category_result.scalar_one_or_none()
            if category:
                conditions.append(Product.category_id == category.id)

        if brand_slug:
            brand_result = await self.db.execute(
                select(Brand).where(Brand.slug == brand_slug)
            )
            brand = brand_result.scalar_one_or_none()
            if brand:
                conditions.append(Product.brand_id == brand.id)

        if store_slug:
            store_result = await self.db.execute(
                select(Store).where(Store.slug == store_slug)
            )
            store = store_result.scalar_one_or_none()
            if store:
                conditions.append(Product.store_id == store.id)

        if min_price is not None or max_price is not None:
            variant_subquery = (
                select(ProductVariant.product_id, func.min(ProductVariant.price_delta).label("min_price"))
                .group_by(ProductVariant.product_id)
                .subquery()
            )
            conditions.append(Product.id == variant_subquery.c.product_id)
            if min_price is not None:
                conditions.append(variant_subquery.c.min_price >= min_price)
            if max_price is not None:
                conditions.append(variant_subquery.c.min_price <= max_price)

        order_column = getattr(Product, sort_by, Product.created_at)
        if sort_order.lower() == "asc":
            order_clause = order_column.asc()
        else:
            order_clause = order_column.desc()

        count_query = select(func.count()).select_from(Product).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        search_query = (
            select(Product)
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
                selectinload(Product.category),
                selectinload(Product.brand),
            )
            .where(and_(*conditions))
            .order_by(order_clause)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(search_query)
        products = list(result.scalars().all())

        return {
            "items": products,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_featured_collections(
        self,
        store_slug: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        store_result = await self.db.execute(
            select(Store).where(Store.slug == store_slug)
        )
        store = store_result.scalar_one_or_none()
        if not store:
            return []

        categories_result = await self.db.execute(
            select(Category)
            .where(and_(Category.is_active == True, Category.parent_id == None))
            .order_by(Category.sort_order)
            .limit(limit)
        )
        categories = list(categories_result.scalars().all())

        collections = []
        for category in categories:
            products_result = await self.db.execute(
                select(Product)
                .options(selectinload(Product.images))
                .where(
                    and_(
                        Product.store_id == store.id,
                        Product.category_id == category.id,
                        Product.is_active == True,
                    )
                )
                .order_by(Product.created_at.desc())
                .limit(8)
            )
            products = list(products_result.scalars().all())

            collections.append({
                "category": category,
                "products": products,
            })

        return collections


from app.modules.catalog.models import Category, Brand
CatalogSearchService.__init__.__annotations__["db"] = AsyncSession