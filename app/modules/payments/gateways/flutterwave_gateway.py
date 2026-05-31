import httpx
import hashlib
import hmac
import time
from typing import Dict, Any, Optional

from app.modules.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayType,
    PaymentResult,
    VerificationResult,
    RefundResult,
)


class FlutterwaveGateway(PaymentGateway):
    gateway_type = PaymentGatewayType.FLUTTERWAVE

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        webhook_secret: str,
        base_url: str = "https://api.flutterwave.com/v3",
    ):
        self.public_key = public_key
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.base_url = base_url

    def _generate_tx_ref(self) -> str:
        return f"FLW-{int(time.time() * 1000)}"

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
                    f"{self.base_url}/payments",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "tx_ref": reference,
                        "amount": amount,
                        "currency": currency.upper(),
                        "email": email,
                        "phonenumber": metadata.get("phone", "") if metadata else "",
                        "redirect_url": metadata.get("redirect_url", "") if metadata else "",
                        "meta": metadata or {},
                        "description": description,
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return PaymentResult(
                        success=True,
                        transaction_id=data["data"].get("id"),
                        reference=reference,
                        payment_url=data["data"].get("link"),
                        status="pending",
                        message="Payment link generated",
                        gateway_response=data,
                    )
                else:
                    return PaymentResult(
                        success=False,
                        status="failed",
                        message=data.get("message", "Flutterwave error"),
                        gateway_response=data,
                    )
            else:
                return PaymentResult(
                    success=False,
                    status="failed",
                    message=f"Flutterwave error: {response.text}",
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
                    f"{self.base_url}/transactions/{reference}/verify",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    tx_data = data.get("data", {})
                    return VerificationResult(
                        success=tx_data.get("status") == "successful",
                        status=tx_data.get("status", "unknown"),
                        amount=tx_data.get("amount"),
                        currency=tx_data.get("currency", "").upper(),
                        customer_email=tx_data.get("customer", {}).get("email"),
                        metadata=tx_data.get("meta"),
                        gateway_response=data,
                    )
                else:
                    return VerificationResult(
                        success=False,
                        status=data.get("status", "not_found"),
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
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/refunds",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "transaction_id": transaction_id,
                        "amount": amount,
                        "comment": reason or "Refund requested",
                    },
                )

            if response.status_code in (200, 201):
                refund_data = response.json()
                if refund_data.get("status") == "success":
                    return RefundResult(
                        success=True,
                        refund_id=str(refund_data["data"].get("id")),
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
                    message=f"Flutterwave refund error: {response.text}",
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
                    f"{self.base_url}/transactions/{reference}/verify",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data["data"].get("link")
            return None

        except Exception:
            return None

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        try:
            expected_hash = hashlib.sha256(
                (self.webhook_secret + payload.decode()).encode()
            ).hexdigest()

            return hmac.compare_digest(expected_hash, signature)
        except Exception:
            return False
