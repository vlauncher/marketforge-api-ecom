from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import UserRole
from app.modules.payments.schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentDetailResponse,
    PaymentListResponse,
    RefundCreate,
    RefundResponse,
    PaymentWebhook,
)
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])
admin_router = APIRouter(prefix="/admin/payments", tags=["Admin Payments"])
vendor_router = APIRouter(prefix="/vendor/payments", tags=["Vendor Payments"])


async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def payment_webhook(
    webhook_data: PaymentWebhook,
    service: PaymentService = Depends(get_payment_service),
) -> Dict[str, str]:
    event_dict = {
        "event_type": webhook_data.event_type,
        "payment_intent_id": webhook_data.payment_intent_id,
        "amount": webhook_data.amount,
        "currency": webhook_data.currency,
        "status": webhook_data.status,
        "metadata": webhook_data.metadata,
    }
    await service.handle_webhook(event_dict)
    return {"status": "received"}


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentDetailResponse:
    payment = await service.get_payment_by_id(payment_id)
    return PaymentDetailResponse.model_validate(payment)


@vendor_router.get("", response_model=PaymentListResponse)
async def list_vendor_payments(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    from app.modules.vendors.service import VendorService
    vendor_service = VendorService(db)
    vendor = await vendor_service.get_vendor_by_user_id(current_user["user_id"])

    payments, total = await PaymentService(db).list_vendor_payments(
        vendor_id=vendor.id,
        limit=limit,
        offset=offset,
    )
    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    payment_id: int,
    refund_data: RefundCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> RefundResponse:
    if current_user["role"] not in (UserRole.ADMIN, UserRole.VENDOR):
        raise PermissionError("Vendor or admin access required")

    refund = await service.create_refund(
        payment_id=payment_id,
        amount=refund_data.amount,
        reason=refund_data.reason,
        idempotency_key=refund_data.idempotency_key,
    )
    return RefundResponse.model_validate(refund)


@router.post("/{order_id}/pay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_for_order(
    order_id: int,
    payment_data: PaymentCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    payment = await service.create_payment(
        order_id=order_id,
        amount=payment_data.amount,
        currency_code=payment_data.currency_code,
        payment_method=payment_data.payment_method,
        idempotency_key=payment_data.idempotency_key,
        metadata=payment_data.metadata,
    )
    payment = await service.process_payment(payment.id)
    return PaymentResponse.model_validate(payment)