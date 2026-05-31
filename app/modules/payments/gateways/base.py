from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class PaymentGatewayType(str, Enum):
    STRIPE = "stripe"
    PAYSTACK = "paystack"
    FLUTTERWAVE = "flutterwave"
    MONNIFY = "monnify"


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    reference: Optional[str] = None
    payment_url: Optional[str] = None
    status: str = "pending"
    message: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None


@dataclass
class VerificationResult:
    success: bool
    status: str = "pending"
    amount: Optional[float] = None
    currency: Optional[str] = None
    customer_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    gateway_response: Optional[Dict[str, Any]] = None


@dataclass
class RefundResult:
    success: bool
    status: str = "pending"
    refund_id: Optional[str] = None
    message: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None


class PaymentGateway(ABC):
    gateway_type: PaymentGatewayType

    @abstractmethod
    async def initialize_payment(
        self,
        amount: float,
        currency: str,
        email: str,
        reference: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        pass

    @abstractmethod
    async def verify_payment(self, reference: str) -> VerificationResult:
        pass

    @abstractmethod
    async def process_refund(
        self,
        transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        pass

    @abstractmethod
    async def get_payment_url(self, reference: str) -> Optional[str]:
        pass

    def get_webhook_signature_header(self) -> str:
        return "X-Gateway-Signature"

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        pass
