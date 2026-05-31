from typing import Dict, Optional, List
from app.modules.payments.gateways.base import (
    PaymentGateway,
    PaymentGatewayType,
    PaymentResult,
    VerificationResult,
    RefundResult,
)
from app.modules.payments.gateways.stripe_gateway import StripeGateway
from app.modules.payments.gateways.paystack_gateway import PaystackGateway
from app.modules.payments.gateways.flutterwave_gateway import FlutterwaveGateway
from app.modules.payments.gateways.monnify_gateway import MonnifyGateway


class PaymentGatewayManager:
    def __init__(self):
        self._gateways: Dict[PaymentGatewayType, PaymentGateway] = {}
        self._default_gateway: Optional[PaymentGatewayType] = None

    def register_gateway(
        self,
        gateway_type: PaymentGatewayType,
        gateway: PaymentGateway,
        set_default: bool = False,
    ) -> None:
        self._gateways[gateway_type] = gateway
        if set_default or not self._default_gateway:
            self._default_gateway = gateway_type

    def set_default_gateway(self, gateway_type: PaymentGatewayType) -> None:
        if gateway_type in self._gateways:
            self._default_gateway = gateway_type

    def get_gateway(self, gateway_type: Optional[PaymentGatewayType] = None) -> Optional[PaymentGateway]:
        if gateway_type and gateway_type in self._gateways:
            return self._gateways[gateway_type]
        if self._default_gateway:
            return self._gateways.get(self._default_gateway)
        return None

    def get_available_gateways(self) -> List[PaymentGatewayType]:
        return list(self._gateways.keys())

    async def initialize_payment(
        self,
        amount: float,
        currency: str,
        email: str,
        reference: str,
        description: str,
        gateway_type: Optional[PaymentGatewayType] = None,
        metadata: Optional[Dict] = None,
    ) -> PaymentResult:
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            return PaymentResult(
                success=False,
                status="error",
                message=f"Gateway {gateway_type} not configured",
            )
        return await gateway.initialize_payment(
            amount=amount,
            currency=currency,
            email=email,
            reference=reference,
            description=description,
            metadata=metadata,
        )

    async def verify_payment(
        self,
        reference: str,
        gateway_type: Optional[PaymentGatewayType] = None,
    ) -> VerificationResult:
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            return VerificationResult(
                success=False,
                status="error",
                gateway_response={"error": f"Gateway {gateway_type} not configured"},
            )
        return await gateway.verify_payment(reference)

    async def process_refund(
        self,
        transaction_id: str,
        gateway_type: Optional[PaymentGatewayType] = None,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            return RefundResult(
                success=False,
                status="error",
                message=f"Gateway {gateway_type} not configured",
            )
        return await gateway.process_refund(
            transaction_id=transaction_id,
            amount=amount,
            reason=reason,
        )

    async def get_payment_url(
        self,
        reference: str,
        gateway_type: Optional[PaymentGatewayType] = None,
    ) -> Optional[str]:
        gateway = self.get_gateway(gateway_type)
        if not gateway:
            return None
        return await gateway.get_payment_url(reference)


gateway_manager = PaymentGatewayManager()


def setup_gateways(
    stripe_key: Optional[str] = None,
    stripe_webhook_secret: Optional[str] = None,
    paystack_key: Optional[str] = None,
    paystack_webhook_secret: Optional[str] = None,
    flutterwave_public_key: Optional[str] = None,
    flutterwave_secret_key: Optional[str] = None,
    flutterwave_webhook_secret: Optional[str] = None,
    monnify_api_key: Optional[str] = None,
    monnify_secret_key: Optional[str] = None,
    monnify_contract_code: Optional[str] = None,
    monnify_webhook_secret: Optional[str] = None,
    default_gateway: PaymentGatewayType = PaymentGatewayType.STRIPE,
) -> PaymentGatewayManager:
    if stripe_key and stripe_webhook_secret:
        gateway_manager.register_gateway(
            PaymentGatewayType.STRIPE,
            StripeGateway(api_key=stripe_key, webhook_secret=stripe_webhook_secret),
            set_default=(default_gateway == PaymentGatewayType.STRIPE),
        )

    if paystack_key and paystack_webhook_secret:
        gateway_manager.register_gateway(
            PaymentGatewayType.PAYSTACK,
            PaystackGateway(secret_key=paystack_key, webhook_secret=paystack_webhook_secret),
            set_default=(default_gateway == PaymentGatewayType.PAYSTACK),
        )

    if flutterwave_public_key and flutterwave_secret_key and flutterwave_webhook_secret:
        gateway_manager.register_gateway(
            PaymentGatewayType.FLUTTERWAVE,
            FlutterwaveGateway(
                public_key=flutterwave_public_key,
                secret_key=flutterwave_secret_key,
                webhook_secret=flutterwave_webhook_secret,
            ),
            set_default=(default_gateway == PaymentGatewayType.FLUTTERWAVE),
        )

    if monnify_api_key and monnify_secret_key and monnify_contract_code and monnify_webhook_secret:
        gateway_manager.register_gateway(
            PaymentGatewayType.MONNIFY,
            MonnifyGateway(
                api_key=monnify_api_key,
                secret_key=monnify_secret_key,
                contract_code=monnify_contract_code,
                webhook_secret=monnify_webhook_secret,
            ),
            set_default=(default_gateway == PaymentGatewayType.MONNIFY),
        )

    return gateway_manager
