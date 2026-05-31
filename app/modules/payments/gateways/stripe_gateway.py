import httpx
from typing import Dict, Any, Optional

from app.modules.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayType,
    PaymentResult,
    VerificationResult,
    RefundResult,
)


class StripeGateway(PaymentGateway):
    gateway_type = PaymentGatewayType.STRIPE

    def __init__(
        self,
        api_key: str,
        webhook_secret: str,
        base_url: str = "https://api.stripe.com/v1",
    ):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.base_url = base_url

    async def initialize_payment(
        self,
        amount: float,
        currency: str,
        email: str,
        reference: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/checkout/sessions",
                    auth=(self.api_key, ""),
                    data={
                        "mode": "payment",
                        "payment_method_types[]": "card",
                        "line_items[0][price_data][currency]": currency.lower(),
                        "line_items[0][price_data][unit_amount]": int(amount * 100),
                        "line_items[0][price_data][product_data][name]": description,
                        "customer_email": email,
                        "success_url": "{CHECKOUT_SESSION_ID}/success",
                        "cancel_url": "{CHECKOUT_SESSION_ID}/cancel",
                        "metadata[reference]": reference,
                    },
                )

            if response.status_code == 200:
                data = response.json()
                return PaymentResult(
                    success=True,
                    transaction_id=data.get("id"),
                    reference=reference,
                    payment_url=data.get("url"),
                    status="pending",
                    message="Payment session created",
                    gateway_response=data,
                )
            else:
                return PaymentResult(
                    success=False,
                    status="failed",
                    message=f"Stripe error: {response.text}",
                    gateway_response=response.json() if response.text else None,
                )

        except Exception as e:
            return PaymentResult(
                success=False,
                status="error",
                message=str(e),
            )

    async def verify_payment(self, reference: str) -> VerificationResult:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/checkout/sessions/{reference}",
                    auth=(self.api_key, ""),
                )

            if response.status_code == 200:
                data = response.json()
                return VerificationResult(
                    success=data.get("payment_status") == "paid",
                    status=data.get("payment_status", "unknown"),
                    amount=data.get("amount_total", 0) / 100 if data.get("amount_total") else None,
                    currency=data.get("currency", "").upper(),
                    customer_email=data.get("customer_email"),
                    metadata=data.get("metadata"),
                    gateway_response=data,
                )
            else:
                return VerificationResult(
                    success=False,
                    status="not_found",
                    gateway_response=response.json() if response.text else None,
                )

        except Exception as e:
            return VerificationResult(
                success=False,
                status="error",
                gateway_response={"error": str(e)},
            )

    async def process_refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        try:
            data = {"charge": transaction_id}
            if amount:
                data["amount"] = int(amount * 100)
            if reason:
                data["reason"] = reason

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/refunds",
                    auth=(self.api_key, ""),
                    data=data,
                )

            if response.status_code == 200:
                refund_data = response.json()
                return RefundResult(
                    success=True,
                    refund_id=refund_data.get("id"),
                    status=refund_data.get("status", "succeeded"),
                    message="Refund processed",
                    gateway_response=refund_data,
                )
            else:
                return RefundResult(
                    success=False,
                    status="failed",
                    message=f"Stripe refund error: {response.text}",
                    gateway_response=response.json() if response.text else None,
                )

        except Exception as e:
            return RefundResult(
                success=False,
                status="error",
                message=str(e),
            )

    async def get_payment_url(self, reference: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/checkout/sessions/{reference}",
                    auth=(self.api_key, ""),
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("url")
            return None

        except Exception:
            return None

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        import hmac
        import hashlib

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(f"sha256={expected_signature}", signature)
        except Exception:
            return False
