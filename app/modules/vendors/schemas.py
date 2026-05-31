from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from app.modules.vendors.models import VendorStatus


class VendorProfileCreate(BaseModel):
    bio: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class VendorProfileUpdate(BaseModel):
    bio: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class VendorProfileResponse(BaseModel):
    id: int
    vendor_id: int
    bio: Optional[str]
    logo_url: Optional[str]
    contact_email: Optional[str]
    phone: Optional[str]
    address: Optional[str]

    model_config = {"from_attributes": True}


class VendorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    profile: Optional[VendorProfileCreate] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    profile: Optional[VendorProfileUpdate] = None


class VendorStatusUpdate(BaseModel):
    status: VendorStatus


class VendorResponse(BaseModel):
    id: int
    user_id: int
    name: str
    slug: str
    status: VendorStatus
    commission_rate: float
    created_at: datetime

    model_config = {"from_attributes": True}


class VendorDetailResponse(BaseModel):
    id: int
    user_id: int
    name: str
    slug: str
    status: VendorStatus
    commission_rate: float
    created_at: datetime
    profile: Optional[VendorProfileResponse] = None

    model_config = {"from_attributes": True}


class VendorOnboardRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    store_name: str = Field(..., min_length=2, max_length=255)
    profile: Optional[VendorProfileCreate] = None