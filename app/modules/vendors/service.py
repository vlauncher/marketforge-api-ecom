from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError
from app.modules.identity.models import User, UserRole
from app.modules.identity.schemas import UserCreate
from app.modules.identity.service import AuthService
from app.modules.vendors.models import Vendor, VendorProfile, VendorStatus
from app.modules.vendors.schemas import VendorCreate, VendorUpdate, VendorProfileCreate
from app.modules.storefronts.models import Store
from app.modules.storefronts.schemas import StoreCreate


class VendorService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _generate_slug(self, name: str) -> str:
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    async def create_vendor(self, vendor_data: VendorCreate, user_id: int) -> Vendor:
        slug = self._generate_slug(vendor_data.name)
        counter = 1
        base_slug = slug
        while True:
            existing = await self.db.execute(select(Vendor).where(Vendor.slug == slug))
            if not existing.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        vendor = Vendor(
            user_id=user_id,
            name=vendor_data.name,
            slug=slug,
            status=VendorStatus.PENDING,
        )
        self.db.add(vendor)
        await self.db.flush()

        if vendor_data.profile:
            profile = VendorProfile(
                vendor_id=vendor.id,
                **vendor_data.profile.model_dump(),
            )
            self.db.add(profile)
            await self.db.flush()

        await self.db.refresh(vendor)
        return vendor

    async def get_vendor_by_id(self, vendor_id: int) -> Vendor:
        result = await self.db.execute(
            select(Vendor)
            .options(selectinload(Vendor.profile))
            .where(Vendor.id == vendor_id)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise NotFoundError("Vendor", str(vendor_id))
        return vendor

    async def get_vendor_by_user_id(self, user_id: int) -> Vendor:
        result = await self.db.execute(
            select(Vendor)
            .options(selectinload(Vendor.profile))
            .where(Vendor.user_id == user_id)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise NotFoundError("Vendor", str(user_id))
        return vendor

    async def get_vendor_by_slug(self, slug: str) -> Vendor:
        result = await self.db.execute(
            select(Vendor)
            .options(selectinload(Vendor.profile))
            .where(Vendor.slug == slug)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            raise NotFoundError("Vendor", slug)
        return vendor

    async def update_vendor(
        self,
        vendor_id: int,
        vendor_data: VendorUpdate,
        current_user: Dict[str, Any],
    ) -> Vendor:
        vendor = await self.get_vendor_by_id(vendor_id)

        if vendor.user_id != current_user["user_id"] and current_user["role"] != UserRole.ADMIN:
            raise ForbiddenError("You can only update your own vendor profile")

        if vendor_data.name is not None:
            vendor.name = vendor_data.name
        if vendor_data.profile is not None:
            if vendor.profile:
                for key, value in vendor_data.profile.model_dump(exclude_unset=True).items():
                    setattr(vendor.profile, key, value)
            else:
                profile = VendorProfile(
                    vendor_id=vendor.id,
                    **vendor_data.profile.model_dump(),
                )
                self.db.add(profile)

        await self.db.flush()
        await self.db.refresh(vendor)
        return vendor

    async def update_vendor_status(
        self,
        vendor_id: int,
        status: VendorStatus,
        current_user: Dict[str, Any],
    ) -> Vendor:
        if current_user["role"] != UserRole.ADMIN:
            raise ForbiddenError("Only admins can update vendor status")

        vendor = await self.get_vendor_by_id(vendor_id)
        vendor.status = status
        await self.db.flush()
        await self.db.refresh(vendor)
        return vendor

    async def onboard_vendor(
        self,
        request,
    ) -> Tuple[Vendor, Store]:
        auth_service = AuthService(self.db)

        user_data = UserCreate(email=request.email, password=request.password)
        user = await auth_service.register_user(user_data, role=UserRole.VENDOR)

        vendor_data = VendorCreate(name=request.name, profile=request.profile)
        vendor = await self.create_vendor(vendor_data, user.id)

        store_data = StoreCreate(
            name=request.store_name,
            description=f"Default store for {request.store_name}",
        )
        from app.modules.storefronts.service import StorefrontService
        storefront_service = StorefrontService(self.db)
        store = await storefront_service.create_store(store_data, vendor.id)

        return vendor, store