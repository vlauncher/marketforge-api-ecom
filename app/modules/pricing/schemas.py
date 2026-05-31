from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

from app.modules.pricing.models import Price as PriceModel


class CurrencyCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=10)
    decimal_places: int = 2
    is_default: bool = False


class CurrencyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    symbol: Optional[str] = Field(None, min_length=1, max_length=10)
    decimal_places: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class CurrencyResponse(BaseModel):
    id: int
    code: str
    name: str
    symbol: str
    decimal_places: int
    is_active: bool
    is_default: bool

    model_config = {"from_attributes": True}


class ExchangeRateCreate(BaseModel):
    from_currency_code: str
    to_currency_code: str
    rate: float = Field(..., gt=0)


class ExchangeRateResponse(BaseModel):
    id: int
    from_currency_id: int
    to_currency_id: int
    rate: float
    effective_at: datetime

    model_config = {"from_attributes": True}


class PriceCreate(BaseModel):
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    addon_id: Optional[int] = None
    currency_code: str
    amount: float = Field(..., ge=0)
    is_override: bool = False
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class PriceUpdate(BaseModel):
    amount: Optional[float] = Field(None, ge=0)
    is_override: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None


class PriceResponse(BaseModel):
    id: int
    product_id: Optional[int]
    variant_id: Optional[int]
    addon_id: Optional[int]
    currency_id: int
    amount: float
    is_override: bool
    effective_from: Optional[datetime]
    effective_until: Optional[datetime]

    model_config = {"from_attributes": True}


class PriceBreakdownItem(BaseModel):
    label: str
    amount: float
    currency: str


class PriceBreakdown(BaseModel):
    base_price: float
    variant_delta: float = 0.0
    addon_deltas: list[PriceBreakdownItem] = []
    subtotal: float
    tax_estimate: float = 0.0
    shipping_estimate: float = 0.0
    discount: float = 0.0
    total: float
    currency: str
    converted_from: Optional[str] = None
    exchange_rate: Optional[float] = None


class PriceResolutionRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    addon_ids: list[int] = []
    currency_code: str = "USD"
    quantity: int = 1


class PriceResolutionResponse(BaseModel):
    product_id: int
    variant_id: Optional[int]
    currency: str
    quantity: int
    breakdown: PriceBreakdown
    unit_price: float
    line_total: float