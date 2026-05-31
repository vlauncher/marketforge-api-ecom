from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.modules.payments.models import Payment, Refund, PaymentStatus


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_payment(
        self,
        order_id: int,
        amount: float,
        currency_code: str,
        payment_method: Optional[str],
        idempotency_key: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> Payment:
        if idempotency_key:
            existing = await self.db.execute(
                select(Payment).where(Payment.idempotency_key == idempotency_key)
            )
            existing_payment = existing.scalar_one_or_none()
            if existing_payment:
                return existing_payment

        payment = Payment(
            order_id=order_id,
            amount=amount,
            currency_code=currency_code,
            payment_method=payment_method,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_payment_by_id(self, payment_id: int) -> Payment:
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.refunds))
            .where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise NotFoundError("Payment", str(payment_id))
        return payment

    async def get_payment_by_order_id(self, order_id: int) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.refunds))
            .where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def update_payment_status(
        self,
        payment_id: int,
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
    ) -> Payment:
        payment = await self.get_payment_by_id(payment_id)
        payment.status = status
        if transaction_id:
            payment.transaction_id = transaction_id
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def complete_payment(self, payment_id: int, transaction_id: str) -> Payment:
        return await self.update_payment_status(
            payment_id=payment_id,
            status=PaymentStatus.COMPLETED,
            transaction_id=transaction_id,
        )

    async def fail_payment(self, payment_id: int) -> Payment:
        return await self.update_payment_status(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
        )

    async def process_payment(
        self,
        payment_id: int,
    ) -> Payment:
        payment = await self.get_payment_by_id(payment_id)

        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(f"Payment {payment_id} is not in pending state")

        payment.status = PaymentStatus.PROCESSING
        await self.db.flush()

        import random
        transaction_id = f"txn_{random.randint(100000, 999999)}"

        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = transaction_id
        await self.db.flush()
        await self.db.refresh(payment)

        return payment

    async def create_refund(
        self,
        payment_id: int,
        amount: float,
        reason: Optional[str],
        idempotency_key: Optional[str],
    ) -> Refund:
        if idempotency_key:
            existing = await self.db.execute(
                select(Refund).where(Refund.idempotency_key == idempotency_key)
            )
            existing_refund = existing.scalar_one_or_none()
            if existing_refund:
                return existing_refund

        payment = await self.get_payment_by_id(payment_id)

        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError("Payment must be completed to issue refund")

        total_refunded = sum(r.amount for r in payment.refunds if r.status == "completed")
        if total_refunded + amount > payment.amount:
            raise ValidationError(
                f"Refund amount {amount} exceeds available refund amount {payment.amount - total_refunded}"
            )

        refund = Refund(
            payment_id=payment_id,
            amount=amount,
            reason=reason,
            status="pending",
            idempotency_key=idempotency_key,
        )
        self.db.add(refund)
        await self.db.flush()
        await self.db.refresh(refund)

        refund.status = "completed"
        await self.db.flush()

        total_refunded_after = sum(r.amount for r in payment.refunds if r.status == "completed")
        if total_refunded_after >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED
        await self.db.flush()

        return refund

    async def list_vendor_payments(
        self,
        vendor_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Payment], int]:
        from app.modules.orders.models import Order
        from app.modules.vendors.models import Vendor

        count_result = await self.db.execute(
            select(func.count())
            .select_from(Payment)
            .join(Payment.order)
            .join(Order.store)
            .where(Order.store_id == Vendor.stores)
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.refunds))
            .join(Payment.order)
            .join(Order.store)
            .where(Vendor.id == vendor_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        payments = list(result.scalars().all())
        return payments, total

    async def handle_webhook(self, event_data: Dict[str, Any]) -> Optional[Payment]:
        event_type = event_data.get("event_type")
        payment_intent_id = event_data.get("payment_intent_id")

        if not payment_intent_id:
            return None

        result = await self.db.execute(
            select(Payment).where(Payment.transaction_id == payment_intent_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return None

        if event_type == "payment_intent.succeeded":
            payment.status = PaymentStatus.COMPLETED
        elif event_type == "payment_intent.failed":
            payment.status = PaymentStatus.FAILED
        elif event_type == "refund.created":
            pass

        await self.db.flush()
        await self.db.refresh(payment)
        return payment