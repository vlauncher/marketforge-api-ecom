from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.models import UserRole
from app.modules.identity.dependencies import get_current_user
from app.modules.vendors.schemas import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorDetailResponse,
    VendorStatusUpdate,
    VendorOnboardRequest,
)
from app.modules.vendors.service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("/onboard", response_model=VendorDetailResponse, status_code=status.HTTP_201_CREATED)
async def onboard_vendor(
    request: VendorOnboardRequest,
    db: AsyncSession = Depends(get_db),
) -> VendorDetailResponse:
    vendor_service = VendorService(db)
    vendor, _ = await vendor_service.onboard_vendor(request)
    return VendorDetailResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorDetailResponse)
async def get_vendor(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
) -> VendorDetailResponse:
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_id(vendor_id)
    return VendorDetailResponse.model_validate(vendor)


@router.patch("/{vendor_id}", response_model=VendorDetailResponse)
async def update_vendor(
    vendor_id: int,
    vendor_data: VendorUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VendorDetailResponse:
    vendor_service = VendorService(db)
    vendor = await vendor_service.update_vendor(vendor_id, vendor_data, current_user)
    return VendorDetailResponse.model_validate(vendor)


@router.patch("/{vendor_id}/status", response_model=VendorResponse)
async def update_vendor_status(
    vendor_id: int,
    status_update: VendorStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VendorResponse:
    vendor_service = VendorService(db)
    vendor = await vendor_service.update_vendor_status(vendor_id, status_update.status, current_user)
    return VendorResponse.model_validate(vendor)


@router.get("/me/profile", response_model=VendorDetailResponse)
async def get_my_vendor_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VendorDetailResponse:
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])
    return VendorDetailResponse.model_validate(vendor)