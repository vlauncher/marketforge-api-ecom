from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.payments.gateways.base import PaymentGatewayType
from app.modules.payments.gateways.factory import gateway_manager
from app.modules.payments.service import PaymentService
from app.modules.payments.models import PaymentStatus

router = APIRouter(prefix="/webhooks", tags=["Payment Webhooks"])


async def get_payment_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    payload: bytes = None,
    stripe_signature: Optional[str] = Header(None),
    service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    if payload is None:
        payload = await request.body()

    gateway = gateway_manager.get_gateway(PaymentGatewayType.STRIPE)
    if not gateway:
        return {"error": "Stripe gateway not configured"}

    if not await gateway.verify_webhook_signature(payload, stripe_signature or ""):
        return {"error": "Invalid signature"}

    import json
    event = json.loads(payload)

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        reference = data.get("metadata", {}).get("reference")
        if reference:
            await service.update_payment_by_reference(
                reference=reference,
                status=PaymentStatus.COMPLETED,
                transaction_id=data.get("id"),
            )

    elif event_type == "payment_intent.payment_failed":
        reference = data.get("metadata", {}).get("reference")
        if reference:
            await service.update_payment_by_reference(
                reference=reference,
                status=PaymentStatus.FAILED,
            )

    return {"received": True}


@router.post("/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    event = await request.json()

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.success":
        reference = data.get("reference")
        if reference:
            await service.update_payment_by_reference(
                reference=reference,
                status=PaymentStatus.COMPLETED,
                transaction_id=str(data.get("id")),
            )

    elif event_type in ("charge.failed", "transaction.failed"):
        reference = data.get("reference")
        if reference:
            await service.update_payment_by_reference(
                reference=reference,
                status=PaymentStatus.FAILED,
            )

    return {"received": True}


@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    event = await request.json()

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.completed":
        tx_ref = data.get("tx_ref")
        if tx_ref:
            await service.update_payment_by_reference(
                reference=tx_ref,
                status=PaymentStatus.COMPLETED,
                transaction_id=str(data.get("id")),
            )

    elif event_type == "charge.failed":
        tx_ref = data.get("tx_ref")
        if tx_ref:
            await service.update_payment_by_reference(
                reference=tx_ref,
                status=PaymentStatus.FAILED,
            )

    return {"received": True}


@router.post("/monnify", status_code=status.HTTP_200_OK)
async def monnify_webhook(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> Dict[str, Any]:
    event = await request.json()

    event_type = event.get("eventType")
    data = event.get("transactionReference")

    if event_type == "SUCCESSFUL":
        await service.update_payment_by_reference(
            reference=data,
            status=PaymentStatus.COMPLETED,
            transaction_id=data,
        )

    elif event_type == "FAILED":
        await service.update_payment_by_reference(
            reference=data,
            status=PaymentStatus.FAILED,
        )

    return {"received": True}
