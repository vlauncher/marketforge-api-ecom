import httpx
import hashlib
import hmac
from typing import Dict, Any, Optional

from app.modules.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayType,
    PaymentResult,
    VerificationResult,
    RefundResult,
)


class PaystackGateway(PaymentGateway):
    gateway_type = PaymentGatewayType.PAYSTACK

    def __init__(
        self,
        secret_key: str,
        webhook_secret: str,
        base_url: str = "https://api.paystack.co",
    ):
        self.secret_key = secret_key
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
                    f"{self.base_url}/transaction/initialize",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "amount": int(amount * 100),
                        "currency": currency.upper(),
                        "email": email,
                        "reference": reference,
                        "description": description,
                        "metadata": metadata or {},
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    return PaymentResult(
                        success=True,
                        transaction_id=data["data"].get("reference"),
                        reference=reference,
                        payment_url=data["data"].get("authorization_url"),
                        status="pending",
                        message="Payment initialized",
                        gateway_response=data,
                    )
                else:
                    return PaymentResult(
                        success=False,
                        status="failed",
                        message=data.get("message", "Paystack error"),
                        gateway_response=data,
                    )
            else:
                return PaymentResult(
                    success=False,
                    status="failed",
                    message=f"Paystack error: {response.text}",
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
                    f"{self.base_url}/transaction/verify/{reference}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") and data.get("data"):
                    tx_data = data["data"]
                    return VerificationResult(
                        success=tx_data.get("status") == "success",
                        status=tx_data.get("status", "unknown"),
                        amount=tx_data.get("amount", 0) / 100,
                        currency=tx_data.get("currency", "").upper(),
                        customer_email=tx_data.get("customer", {}).get("email"),
                        metadata=tx_data.get("metadata"),
                        gateway_response=data,
                    )
                else:
                    return VerificationResult(
                        success=False,
                        status=data.get("data", {}).get("status", "not_found"),
                        gateway_response=data,
                    )
            else:
                return VerificationResult(
                    success=False,
                    status="error",
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
            data = {"transaction": transaction_id}
            if amount:
                data["amount"] = int(amount * 100)
            if reason:
                data["customer_note"] = reason

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/refund",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                    json=data,
                )

            if response.status_code in (200, 201):
                refund_data = response.json()
                if refund_data.get("status"):
                    return RefundResult(
                        success=True,
                        refund_id=refund_data["data"].get("id"),
                        status=refund_data["data"].get("status", "processed"),
                        message="Refund processed",
                        gateway_response=refund_data,
                    )
                else:
                    return RefundResult(
                        success=False,
                        status="failed",
                        message=refund_data.get("message", "Refund failed"),
                        gateway_response=refund_data,
                    )
            else:
                return RefundResult(
                    success=False,
                    status="failed",
                    message=f"Paystack refund error: {response.text}",
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
                    f"{self.base_url}/transaction/verify/{reference}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    return data["data"].get("authorization_url")
            return None

        except Exception:
            return None

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha512,
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
