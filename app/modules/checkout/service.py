import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, ConflictError
from app.core.redis import redis_client
from app.modules.cart.models import Cart
from app.modules.cart.service import CartService
from app.modules.pricing.service import PricingService
from app.modules.pricing.schemas import PriceBreakdown
from app.modules.inventory.service import InventoryService
from app.modules.inventory.schemas import ReservationItem
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.orders.service import OrderService
from app.modules.checkout.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    CouponValidationResult,
    ShippingCalculationResult,
    ShippingRate,
    TaxCalculationResult,
)


class CheckoutService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cart_service = CartService(db)
        self.pricing_service = PricingService(db)
        self.inventory_service = InventoryService(db)
        self.order_service = OrderService(db)

    async def _get_idempotency_key(self, key: str) -> Optional[Order]:
        cache_key = f"checkout:idempotency:{key}"
        cached = await redis_client.get(cache_key)
        if cached:
            order_id = json.loads(cached)
            return await self.order_service.get_order_by_id(order_id)
        return None

    async def _store_idempotency_key(self, key: str, order_id: int) -> None:
        cache_key = f"checkout:idempotency:{key}"
        await redis_client.set(cache_key, json.dumps(order_id), ex=86400)

    async def validate_cart(self, cart_id: int) -> Cart:
        cart = await self.cart_service.get_cart_by_id(cart_id)
        if not cart.items:
            raise ValidationError("Cart is empty")
        return cart

    async def calculate_shipping(
        self,
        cart_id: int,
        shipping_address: Dict[str, Any],
        currency: str = "USD",
    ) -> ShippingCalculationResult:
        rates = [
            ShippingRate(carrier="ups", service="Ground", price=9.99, estimated_days=5),
            ShippingRate(carrier="ups", service="Express", price=19.99, estimated_days=2),
            ShippingRate(carrier="fedex", service="Standard", price=12.99, estimated_days=4),
            ShippingRate(carrier="fedex", service="Overnight", price=34.99, estimated_days=1),
        ]
        return ShippingCalculationResult(rates=rates, currency=currency)

    async def calculate_tax(
        self,
        cart_id: int,
        shipping_address: Dict[str, Any],
        currency: str = "USD",
    ) -> TaxCalculationResult:
        cart = await self.validate_cart(cart_id)
        subtotal = 0.0
        for item in cart.items:
            price_data = await self.pricing_service.resolve_price(
                product_id=item.product_id,
                variant_id=item.variant_id,
                addon_ids=[],
                currency_code=currency,
                quantity=item.quantity,
            )
            subtotal += price_data[0]

        tax_rate = 0.08
        tax_amount = subtotal * tax_rate

        return TaxCalculationResult(
            tax_amount=round(tax_amount, 2),
            tax_rate=tax_rate,
            taxable_amount=subtotal,
            currency=currency,
        )

    async def validate_coupon(
        self,
        coupon_code: str,
        cart_id: int,
    ) -> CouponValidationResult:
        return CouponValidationResult(
            valid=True,
            coupon_code=coupon_code,
            discount_type="percentage",
            discount_value=10.0,
            discount_amount=0.0,
            message="Coupon is valid",
        )

    async def process_checkout(
        self,
        request: CheckoutRequest,
        current_user: Dict[str, Any],
    ) -> CheckoutResponse:
        existing_order = await self._get_idempotency_key(request.idempotency_key)
        if existing_order:
            return CheckoutResponse(
                order_id=existing_order.id,
                order_number=existing_order.order_number,
                payment_intent_id=None,
                total=existing_order.total,
                currency=existing_order.currency_code,
                status=existing_order.status,
            )

        cart = await self.validate_cart(request.cart_id)

        pricing_service = PricingService(self.db)
        subtotal = 0.0
        order_items = []
        for item in cart.items:
            line_total, _ = await pricing_service.resolve_price(
                product_id=item.product_id,
                variant_id=item.variant_id,
                addon_ids=[],
                currency_code=request.billing_address.country if hasattr(request.billing_address, 'country') else "US",
                quantity=item.quantity,
            )
            subtotal += line_total

            order_items.append({
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "name": item.product.name if item.product else f"Product {item.product_id}",
                "sku": None,
                "quantity": item.quantity,
                "unit_price": line_total / item.quantity if item.quantity > 0 else 0,
                "addons": item.selected_addons,
            })

        tax_calc = await self.calculate_tax(
            request.cart_id,
            request.shipping_address.model_dump(),
            "USD",
        )
        shipping_calc = await self.calculate_shipping(
            request.cart_id,
            request.shipping_address.model_dump(),
            "USD",
        )

        default_shipping = shipping_calc.rates[0] if shipping_calc.rates else None
        shipping_amount = default_shipping.price if default_shipping else 0.0
        discount_amount = 0.0

        if request.coupon_code:
            coupon_result = await self.validate_coupon(request.coupon_code, request.cart_id)
            if coupon_result.valid and coupon_result.discount_amount:
                discount_amount = coupon_result.discount_amount

        total = subtotal + tax_calc.tax_amount + shipping_amount - discount_amount

        reservation_items = [
            ReservationItem(
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
            )
            for item in cart.items
        ]

        reservation_result = await self.inventory_service.reserve_stock(
            items=reservation_items,
            order_id=f"pending-{request.idempotency_key}",
        )

        if not reservation_result.success:
            raise ValidationError(
                f"Insufficient stock for: {[i['product_id'] for i in reservation_result.failed_items]}"
            )

        order = await self.order_service.create_order(
            user_id=current_user.get("user_id"),
            store_id=cart.store_id,
            items=order_items,
            shipping_address=request.shipping_address.model_dump(),
            billing_address=request.billing_address.model_dump() if request.billing_address else None,
            subtotal=subtotal,
            tax_amount=tax_calc.tax_amount,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total=total,
            currency_code="USD",
            idempotency_key=request.idempotency_key,
            notes=None,
        )

        await self._store_idempotency_key(request.idempotency_key, order.id)

        await self.inventory_service.release_stock(f"pending-{request.idempotency_key}")

        return CheckoutResponse(
            order_id=order.id,
            order_number=order.order_number,
            payment_intent_id=None,
            total=order.total,
            currency=order.currency_code,
            status=order.status,
        )