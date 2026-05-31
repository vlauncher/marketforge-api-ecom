from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError
from app.modules.identity.models import UserRole
from app.modules.storefronts.models import Store, StoreTheme, StorePage, StoreDomain, PageType
from app.modules.storefronts.schemas import (
    StoreCreate,
    StoreUpdate,
    StoreThemeCreate,
    StoreThemeUpdate,
    StorePageCreate,
    StorePageUpdate,
    StoreDomainCreate,
)


class StorefrontService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_slug(self, name: str) -> str:
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    async def create_store(self, store_data: StoreCreate, vendor_id: int) -> Store:
        slug = self._generate_slug(store_data.name)
        counter = 1
        base_slug = slug
        while True:
            existing = await self.db.execute(select(Store).where(Store.slug == slug))
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        store = Store(
            vendor_id=vendor_id,
            name=store_data.name,
            slug=slug,
            description=store_data.description,
        )
        self.db.add(store)
        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def get_store_by_id(self, store_id: int) -> Store:
        result = await self.db.execute(
            select(Store)
            .options(
                selectinload(Store.theme),
                selectinload(Store.pages),
                selectinload(Store.domains),
            )
            .where(Store.id == store_id)
        )
        store = result.scalar_one_or_none()
        if not store:
            raise NotFoundError("Store", str(store_id))
        return store

    async def get_store_by_slug(self, slug: str) -> Store:
        result = await self.db.execute(
            select(Store)
            .options(
                selectinload(Store.theme),
                selectinload(Store.pages),
                selectinload(Store.domains),
            )
            .where(Store.slug == slug)
        )
        store = result.scalar_one_or_none()
        if not store:
            raise NotFoundError("Store", slug)
        return store

    async def list_active_stores(self, limit: int = 50, offset: int = 0) -> List[Store]:
        result = await self.db.execute(
            select(Store)
            .where(Store.is_active == True)
            .order_by(Store.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_store(
        self,
        store_id: int,
        store_data: StoreUpdate,
        current_user: Dict[str, Any],
        vendor_id: Optional[int] = None,
    ) -> Store:
        store = await self.get_store_by_id(store_id)

        if vendor_id is not None and store.vendor_id != vendor_id:
            raise ForbiddenError("You do not own this store")

        if current_user["role"] != UserRole.ADMIN and store.vendor_id != vendor_id:
            raise ForbiddenError("You do not own this store")

        if store_data.name is not None:
            store.name = store_data.name
        if store_data.description is not None:
            store.description = store_data.description
        if store_data.is_active is not None:
            store.is_active = store_data.is_active

        await self.db.flush()
        await self.db.refresh(store)
        return store

    async def create_or_update_theme(
        self,
        store_id: int,
        theme_data: StoreThemeCreate,
        current_user: Dict[str, Any],
    ) -> StoreTheme:
        store = await self.get_store_by_id(store_id)
        if current_user["role"] != UserRole.ADMIN and store.vendor_id != current_user.get("vendor_id"):
            raise ForbiddenError("You do not own this store")

        if store.theme:
            theme = store.theme
            if theme_data.colors:
                theme.colors = theme_data.colors.model_dump() if theme_data.colors else None
            if theme_data.fonts:
                theme.fonts = theme_data.fonts.model_dump() if theme_data.fonts else None
            if theme_data.layout:
                theme.layout = theme_data.layout.model_dump() if theme_data.layout else None
        else:
            theme = StoreTheme(
                store_id=store_id,
                colors=theme_data.colors.model_dump() if theme_data.colors else None,
                fonts=theme_data.fonts.model_dump() if theme_data.fonts else None,
                layout=theme_data.layout.model_dump() if theme_data.layout else None,
            )
            self.db.add(theme)

        await self.db.flush()
        await self.db.refresh(theme)
        return theme

    async def create_page(
        self,
        store_id: int,
        page_data: StorePageCreate,
        current_user: Dict[str, Any],
    ) -> StorePage:
        store = await self.get_store_by_id(store_id)
        if current_user["role"] != UserRole.ADMIN and store.vendor_id != current_user.get("vendor_id"):
            raise ForbiddenError("You do not own this store")

        existing = await self.db.execute(
            select(StorePage).where(
                and_(StorePage.store_id == store_id, StorePage.slug == page_data.slug)
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Page with slug '{page_data.slug}' already exists in this store")

        page = StorePage(
            store_id=store_id,
            **page_data.model_dump(),
        )
        self.db.add(page)
        await self.db.flush()
        await self.db.refresh(page)
        return page

    async def update_page(
        self,
        store_id: int,
        page_id: int,
        page_data: StorePageUpdate,
        current_user: Dict[str, Any],
    ) -> StorePage:
        store = await self.get_store_by_id(store_id)
        if current_user["role"] != UserRole.ADMIN and store.vendor_id != current_user.get("vendor_id"):
            raise ForbiddenError("You do not own this store")

        result = await self.db.execute(
            select(StorePage).where(
                and_(StorePage.id == page_id, StorePage.store_id == store_id)
            )
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError("StorePage", str(page_id))

        if page_data.slug is not None:
            page.slug = page_data.slug
        if page_data.title is not None:
            page.title = page_data.title
        if page_data.content is not None:
            page.content = page_data.content
        if page_data.page_type is not None:
            page.page_type = page_data.page_type
        if page_data.is_published is not None:
            page.is_published = page_data.is_published
        if page_data.sort_order is not None:
            page.sort_order = page_data.sort_order

        await self.db.flush()
        await self.db.refresh(page)
        return page

    async def get_store_page(
        self,
        store_slug: str,
        page_slug: str,
    ) -> StorePage:
        store = await self.get_store_by_slug(store_slug)
        result = await self.db.execute(
            select(StorePage).where(
                and_(
                    StorePage.store_id == store.id,
                    StorePage.slug == page_slug,
                    StorePage.is_published == True,
                )
            )
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError("StorePage", page_slug)
        return page