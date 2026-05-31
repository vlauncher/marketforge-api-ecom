import httpx
import base64
import hashlib
import time
from typing import Dict, Any, Optional

from app.modules.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayType,
    PaymentResult,
    VerificationResult,
    RefundResult,
)


class MonnifyGateway(PaymentGateway):
    gateway_type = PaymentGatewayType.MONNIFY

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        contract_code: str,
        webhook_secret: str,
        base_url: str = "https://api.monnify.com/api/v1",
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.contract_code = contract_code
        self.webhook_secret = webhook_secret
        self.base_url = base_url
        self._access_token = None
        self._token_expiry = 0

    async def _get_access_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        try:
            auth_string = f"{self.api_key}:{self.secret_key}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    headers={
                        "Authorization": f"Basic {encoded_auth}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                self._access_token = data.get("responseBody", {}).get("accessToken")
                self._token_expiry = time.time() + 3500
                return self._access_token
            return None

        except Exception:
            return None

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
            access_token = await self._get_access_token()
            if not access_token:
                return PaymentResult(
                    success=False,
                    status="error",
                    message="Failed to authenticate with Monnify",
                )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transaction/initialize",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "amount": str(amount),
                        "currencyCode": currency.upper(),
                        "customerEmail": email,
                        "paymentReference": reference,
                        "paymentDescription": description,
                        "contractCode": self.contract_code,
                        "metadata": metadata or {},
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("requestSuccessful"):
                    return PaymentResult(
                        success=True,
                        transaction_id=data["responseBody"].get("transactionReference"),
                        reference=reference,
                        payment_url=data["responseBody"].get("checkoutUrl"),
                        status="pending",
                        message="Payment initialized",
                        gateway_response=data,
                    )
                else:
                    return PaymentResult(
                        success=False,
                        status="failed",
                        message=data.get("responseMessage", "Monnify error"),
                        gateway_response=data,
                    )
            else:
                return PaymentResult(
                    success=False,
                    status="failed",
                    message=f"Monnify error: {response.text}",
                )

        except Exception as e:
            return PaymentResult(
                success=False,
                status="error",
                message=str(e),
            )

    async def verify_payment(self, reference: str) -> VerificationResult:
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return VerificationResult(
                    success=False,
                    status="error",
                    gateway_response={"error": "Failed to authenticate with Monnify"},
                )

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transaction/{reference}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("requestSuccessful"):
                    tx_data = data.get("responseBody", {})
                    return VerificationResult(
                        success=tx_data.get("paymentStatus") == "PAID",
                        status=tx_data.get("paymentStatus", "unknown").lower(),
                        amount=float(tx_data.get("amountPaid", 0)),
                        currency=tx_data.get("currencyCode", "").upper(),
                        customer_email=tx_data.get("customerEmail"),
                        metadata=tx_data.get("metadata"),
                        gateway_response=data,
                    )
                else:
                    return VerificationResult(
                        success=False,
                        status=data.get("responseMessage", "not_found").lower(),
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
            access_token = await self._get_access_token()
            if not access_token:
                return RefundResult(
                    success=False,
                    status="error",
                    message="Failed to authenticate with Monnify",
                )

            data = {
                "transactionReference": transaction_id,
                "refundReason": reason or "Refund requested",
            }
            if amount:
                data["amount"] = str(amount)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transaction/refund",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=data,
                )

            if response.status_code == 200:
                refund_data = response.json()
                if refund_data.get("requestSuccessful"):
                    return RefundResult(
                        success=True,
                        refund_id=refund_data["responseBody"].get("refundReference"),
                        status=refund_data["responseBody"].get("refundStatus", "processed").lower(),
                        message="Refund processed",
                        gateway_response=refund_data,
                    )
                else:
                    return RefundResult(
                        success=False,
                        status="failed",
                        message=refund_data.get("responseMessage", "Refund failed"),
                        gateway_response=refund_data,
                    )
            else:
                return RefundResult(
                    success=False,
                    status="failed",
                    message=f"Monnify refund error: {response.text}",
                )

        except Exception as e:
            return RefundResult(
                success=False,
                status="error",
                message=str(e),
            )

    async def get_payment_url(self, reference: str) -> Optional[str]:
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return None

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transaction/{reference}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                if data.get("requestSuccessful"):
                    return data["responseBody"].get("checkoutUrl")
            return None

        except Exception:
            return None

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        import hmac

        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha512,
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
