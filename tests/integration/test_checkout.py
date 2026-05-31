import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import CartItemCreate, CartItemUpdate
from app.modules.cart.service import CartService
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import OrderService
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.inventory.schemas import ReservationItem
from app.modules.inventory.service import InventoryService


class TestCartOperations:
    @pytest_asyncio.fixture
    async def cart_service(self, db_session: AsyncSession) -> CartService:
        return CartService(db_session)

    @pytest.mark.asyncio
    async def test_get_or_create_cart_for_user(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        assert cart is not None
        assert cart.user_id == sample_user.id
        assert cart.store_id == sample_store.id
        assert cart.is_active is True

    @pytest.mark.asyncio
    async def test_get_or_create_cart_for_session(
        self,
        db_session: AsyncSession,
        sample_store,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            session_id="test-session-123",
            store_id=sample_store.id,
        )

        assert cart is not None
        assert cart.session_id == "test-session-123"
        assert cart.store_id == sample_store.id

    @pytest.mark.asyncio
    async def test_add_item_to_cart(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        item_data = CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=2,
        )

        item = await cart_service.add_item(cart.id, item_data)

        assert item is not None
        assert item.product_id == sample_product.id
        assert item.quantity == 2

    @pytest.mark.asyncio
    async def test_add_item_increments_quantity(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        item_data = CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=1,
        )
        await cart_service.add_item(cart.id, item_data)

        item_data.quantity = 3
        item = await cart_service.add_item(cart.id, item_data)

        await db_session.refresh(item)
        assert item.quantity == 4

    @pytest.mark.asyncio
    async def test_update_cart_item(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        item_data = CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=2,
        )
        item = await cart_service.add_item(cart.id, item_data)

        update_data = CartItemUpdate(quantity=5)
        updated_item = await cart_service.update_item(item.id, update_data)

        assert updated_item.quantity == 5

    @pytest.mark.asyncio
    async def test_remove_cart_item(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        item_data = CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=2,
        )
        item = await cart_service.add_item(cart.id, item_data)

        await cart_service.remove_item(item.id)

        from app.core.exceptions import NotFoundError
        with pytest.raises(NotFoundError):
            await cart_service.update_item(item.id, CartItemUpdate(quantity=1))

    @pytest.mark.asyncio
    async def test_clear_cart(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        cart_service: CartService,
    ):
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )

        item_data = CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=2,
        )
        await cart_service.add_item(cart.id, item_data)
        await cart_service.add_item(cart.id, CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=1,
        ))

        await cart_service.clear_cart(cart.id)

        updated_cart = await cart_service.get_cart_by_id(cart.id)
        assert len(updated_cart.items) == 0


class TestCheckoutFlow:
    @pytest_asyncio.fixture
    async def order_service(self, db_session: AsyncSession) -> OrderService:
        return OrderService(db_session)

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        order_service: OrderService,
    ):
        from app.modules.cart.schemas import CartItemCreate
        from app.modules.cart.service import CartService

        cart_service = CartService(db_session)
        cart = await cart_service.get_or_create_cart(
            user_id=sample_user.id,
            store_id=sample_store.id,
        )
        await cart_service.add_item(cart.id, CartItemCreate(
            product_id=sample_product.id,
            variant_id=None,
            quantity=1,
            unit_price=99.99,
            name="Test Product",
        ))

        shipping_address = {
            "street": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "US",
        }

        order = await order_service.create_order(
            user_id=sample_user.id,
            store_id=sample_store.id,
            items=[{
                "product_id": sample_product.id,
                "variant_id": None,
                "quantity": 1,
                "unit_price": 99.99,
                "name": "Test Product",
            }],
            shipping_address=shipping_address,
            billing_address=None,
            subtotal=99.99,
            tax_amount=8.00,
            shipping_amount=5.00,
            discount_amount=0.0,
            total=112.99,
            currency_code="USD",
            idempotency_key=None,
            notes=None,
        )

        assert order is not None
        assert order.user_id == sample_user.id
        assert order.total == 112.99
        assert order.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_idempotent_order_creation(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        order_service: OrderService,
    ):
        shipping_address = {
            "street": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country": "US",
        }

        items = [{
            "product_id": sample_product.id,
            "variant_id": None,
            "quantity": 1,
            "unit_price": 99.99,
            "name": "Test Product",
        }]

        order1 = await order_service.create_order(
            user_id=sample_user.id,
            store_id=sample_store.id,
            items=items,
            shipping_address=shipping_address,
            billing_address=None,
            subtotal=99.99,
            tax_amount=8.00,
            shipping_amount=5.00,
            discount_amount=0.0,
            total=112.99,
            currency_code="USD",
            idempotency_key="idem-key-123",
            notes=None,
        )

        order2 = await order_service.create_order(
            user_id=sample_user.id,
            store_id=sample_store.id,
            items=items,
            shipping_address=shipping_address,
            billing_address=None,
            subtotal=99.99,
            tax_amount=8.00,
            shipping_amount=5.00,
            discount_amount=0.0,
            total=112.99,
            currency_code="USD",
            idempotency_key="idem-key-123",
            notes=None,
        )

        assert order1.id == order2.id


class TestInventoryReservationOnCheckout:
    @pytest.mark.asyncio
    async def test_reserve_inventory_on_order(
        self,
        db_session: AsyncSession,
        sample_inventory_item: InventoryItem,
        sample_user,
        sample_store,
        sample_product,
    ):
        inventory_service = InventoryService(db_session)
        initial_quantity = sample_inventory_item.quantity
        initial_reserved = sample_inventory_item.reserved_quantity

        reservation_items = [
            ReservationItem(
                product_id=sample_product.id,
                variant_id=None,
                quantity=10,
            )
        ]

        result = await inventory_service.reserve_stock(reservation_items, "ORD-RES-001")

        assert result.success is True
        await db_session.refresh(sample_inventory_item)
        assert sample_inventory_item.reserved_quantity == initial_reserved + 10

    @pytest.mark.asyncio
    async def test_order_total_multi_currency(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
        sample_product,
        default_currency,
        secondary_currency,
    ):
        order_service = OrderService(db_session)

        shipping_address = {
            "street": "123 Main St",
            "city": "Berlin",
            "state": "BE",
            "postal_code": "10115",
            "country": "DE",
        }

        order = await order_service.create_order(
            user_id=sample_user.id,
            store_id=sample_store.id,
            items=[{
                "product_id": sample_product.id,
                "variant_id": None,
                "quantity": 1,
                "unit_price": 99.99,
                "name": "Test Product",
            }],
            shipping_address=shipping_address,
            billing_address=None,
            subtotal=99.99,
            tax_amount=19.00,
            shipping_amount=15.00,
            discount_amount=0.0,
            total=133.99,
            currency_code="EUR",
            idempotency_key=None,
            notes=None,
        )

        assert order.currency_code == "EUR"
        assert order.total == 133.99


class TestRefundFlow:
    @pytest.mark.asyncio
    async def test_payment_refund(
        self,
        db_session: AsyncSession,
        sample_user,
        sample_store,
    ):
        payment = Payment(
            order_id=1,
            amount=100.00,
            currency_code="USD",
            status=PaymentStatus.COMPLETED,
            payment_method="card",
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        from app.modules.payments.service import PaymentService
        payment_service = PaymentService(db_session)

        refund = await payment_service.create_refund(
            payment_id=payment.id,
            amount=50.00,
            reason="Partial refund",
            idempotency_key=None,
        )

        assert refund is not None
        assert refund.amount == 50.00
        assert refund.status == "completed"