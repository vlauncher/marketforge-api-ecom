import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.promotions.models import Coupon, Promotion, GiftCard, DiscountType
from app.modules.promotions.schemas import CouponCreate
from app.modules.promotions.service import PromotionsService
from app.modules.catalog.models import Product


class TestCouponValidation:
    @pytest_asyncio.fixture
    async def promotions_service(self, db_session: AsyncSession) -> PromotionsService:
        return PromotionsService(db_session)

    @pytest.mark.asyncio
    async def test_validate_coupon_success(
        self,
        db_session: AsyncSession,
        sample_coupon: Coupon,
        promotions_service: PromotionsService,
    ):
        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="SAVE10",
            order_subtotal=100.00,
        )

        assert is_valid is True
        assert coupon is not None
        assert coupon.code == "SAVE10"
        assert discount == 10.00
        assert message == "Coupon is valid"

    @pytest.mark.asyncio
    async def test_validate_coupon_not_found(
        self,
        db_session: AsyncSession,
        promotions_service: PromotionsService,
    ):
        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="INVALID",
            order_subtotal=100.00,
        )

        assert is_valid is False
        assert coupon is None
        assert discount == 0.0
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_inactive(
        self,
        db_session: AsyncSession,
        sample_store,
        promotions_service: PromotionsService,
    ):
        inactive_coupon = Coupon(
            store_id=sample_store.id,
            code="INACTIVE",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            is_active=False,
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(inactive_coupon)
        await db_session.commit()

        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="INACTIVE",
            order_subtotal=100.00,
        )

        assert is_valid is False
        assert "not active" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_expired(
        self,
        db_session: AsyncSession,
        sample_store,
        promotions_service: PromotionsService,
    ):
        expired_coupon = Coupon(
            store_id=sample_store.id,
            code="EXPIRED",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            is_active=True,
            valid_from=datetime.now(timezone.utc) - timedelta(days=14),
            valid_until=datetime.now(timezone.utc) - timedelta(days=7),
        )
        db_session.add(expired_coupon)
        await db_session.commit()

        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="EXPIRED",
            order_subtotal=100.00,
        )

        assert is_valid is False
        assert "expired" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_not_yet_valid(
        self,
        db_session: AsyncSession,
        sample_store,
        promotions_service: PromotionsService,
    ):
        future_coupon = Coupon(
            store_id=sample_store.id,
            code="FUTURE",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            is_active=True,
            valid_from=datetime.now(timezone.utc) + timedelta(days=7),
            valid_until=datetime.now(timezone.utc) + timedelta(days=14),
        )
        db_session.add(future_coupon)
        await db_session.commit()

        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="FUTURE",
            order_subtotal=100.00,
        )

        assert is_valid is False
        assert "not yet valid" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_max_uses_reached(
        self,
        db_session: AsyncSession,
        sample_store,
        promotions_service: PromotionsService,
    ):
        limited_coupon = Coupon(
            store_id=sample_store.id,
            code="LIMITED",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            max_uses=1,
            uses_count=1,
            is_active=True,
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(limited_coupon)
        await db_session.commit()

        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="LIMITED",
            order_subtotal=100.00,
        )

        assert is_valid is False
        assert "limit reached" in message.lower()

    @pytest.mark.asyncio
    async def test_validate_coupon_min_order_not_met(
        self,
        db_session: AsyncSession,
        sample_store,
        promotions_service: PromotionsService,
    ):
        min_order_coupon = Coupon(
            store_id=sample_store.id,
            code="MINORDER",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            min_order_amount=50.0,
            is_active=True,
            valid_from=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(min_order_coupon)
        await db_session.commit()

        is_valid, coupon, discount, message = await promotions_service.validate_coupon(
            code="MINORDER",
            order_subtotal=25.00,
        )

        assert is_valid is False
        assert "minimum order" in message.lower()


class TestDiscountCalculation:
    @pytest_asyncio.fixture
    async def promotions_service(self, db_session: AsyncSession) -> PromotionsService:
        return PromotionsService(db_session)

    def test_calculate_percentage_discount(
        self,
        promotions_service: PromotionsService,
    ):
        discount = promotions_service._calculate_discount(
            discount_type=DiscountType.PERCENTAGE,
            discount_value=10.0,
            subtotal=100.00,
        )

        assert discount == 10.00

    def test_calculate_percentage_discount_with_max(
        self,
        promotions_service: PromotionsService,
    ):
        discount = promotions_service._calculate_discount(
            discount_type=DiscountType.PERCENTAGE,
            discount_value=20.0,
            subtotal=100.00,
            max_discount=15.00,
        )

        assert discount == 15.00

    def test_calculate_fixed_discount(
        self,
        promotions_service: PromotionsService,
    ):
        discount = promotions_service._calculate_discount(
            discount_type=DiscountType.FIXED,
            discount_value=25.00,
            subtotal=100.00,
        )

        assert discount == 25.00

    def test_calculate_fixed_discount_exceeds_subtotal(
        self,
        promotions_service: PromotionsService,
    ):
        discount = promotions_service._calculate_discount(
            discount_type=DiscountType.FIXED,
            discount_value=150.00,
            subtotal=100.00,
        )

        assert discount == 100.00

    def test_calculate_discount_rounding(
        self,
        promotions_service: PromotionsService,
    ):
        discount = promotions_service._calculate_discount(
            discount_type=DiscountType.PERCENTAGE,
            discount_value=33.33,
            subtotal=100.00,
        )

        assert discount == 33.33


class TestCouponRedemption:
    @pytest_asyncio.fixture
    async def promotions_service(self, db_session: AsyncSession) -> PromotionsService:
        return PromotionsService(db_session)

    @pytest.mark.asyncio
    async def test_redeem_coupon_increments_count(
        self,
        db_session: AsyncSession,
        sample_coupon: Coupon,
        promotions_service: PromotionsService,
    ):
        initial_count = sample_coupon.uses_count

        await promotions_service.redeem_coupon(sample_coupon.id)

        await db_session.refresh(sample_coupon)
        assert sample_coupon.uses_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_redeem_coupon_not_found(
        self,
        db_session: AsyncSession,
        promotions_service: PromotionsService,
    ):
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await promotions_service.redeem_coupon(9999)


class TestGiftCard:
    @pytest.mark.asyncio
    async def test_gift_card_creation(
        self,
        db_session: AsyncSession,
        sample_store,
    ):
        gift_card = GiftCard(
            store_id=sample_store.id,
            code="GIFT100",
            current_balance=100.00,
            original_balance=100.00,
            is_active=True,
        )
        db_session.add(gift_card)
        await db_session.commit()
        await db_session.refresh(gift_card)

        assert gift_card.code == "GIFT100"
        assert gift_card.current_balance == 100.00
        assert gift_card.is_active is True