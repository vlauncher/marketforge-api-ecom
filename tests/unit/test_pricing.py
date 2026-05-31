import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.models import Currency, ExchangeRate, Price
from app.modules.pricing.schemas import PriceCreate
from app.modules.pricing.service import PricingService
from app.modules.catalog.models import Product
from app.modules.catalog.service import CatalogService


class TestPricingService:
    @pytest_asyncio.fixture
    async def pricing_service(self, db_session: AsyncSession) -> PricingService:
        return PricingService(db_session)

    @pytest.mark.asyncio
    async def test_create_currency(
        self,
        db_session: AsyncSession,
        pricing_service: PricingService,
    ):
        currency_data = PriceCreate(
            code="GBP",
            name="British Pound",
            symbol="£",
            is_default=False,
            is_active=True,
            decimal_places=2,
        ) if False else None

        from app.modules.pricing.schemas import CurrencyCreate
        currency_data = CurrencyCreate(
            code="GBP",
            name="British Pound",
            symbol="£",
            is_default=False,
            is_active=True,
            decimal_places=2,
        )
        currency = await pricing_service.create_currency(currency_data)

        assert currency.code == "GBP"
        assert currency.name == "British Pound"
        assert currency.symbol == "£"
        assert currency.is_active is True

    @pytest.mark.asyncio
    async def test_create_duplicate_currency_fails(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        pricing_service: PricingService,
    ):
        from app.modules.pricing.schemas import CurrencyCreate
        from app.core.exceptions import ConflictError

        currency_data = CurrencyCreate(
            code="USD",
            name="US Dollar Duplicate",
            symbol="$",
            is_default=False,
            is_active=True,
            decimal_places=2,
        )

        with pytest.raises(ConflictError):
            await pricing_service.create_currency(currency_data)

    @pytest.mark.asyncio
    async def test_list_currencies(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        secondary_currency: Currency,
        pricing_service: PricingService,
    ):
        currencies = await pricing_service.list_currencies()

        assert len(currencies) == 2
        codes = [c.code for c in currencies]
        assert "USD" in codes
        assert "EUR" in codes

    @pytest.mark.asyncio
    async def test_get_currency_by_code(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        pricing_service: PricingService,
    ):
        currency = await pricing_service.get_currency_by_code("USD")

        assert currency.code == "USD"
        assert currency.is_default is True

    @pytest.mark.asyncio
    async def test_get_currency_not_found(
        self,
        db_session: AsyncSession,
        pricing_service: PricingService,
    ):
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await pricing_service.get_currency_by_code("XXX")

    @pytest.mark.asyncio
    async def test_get_product_prices(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        prices = await pricing_service.get_product_prices(
            product_id=sample_product.id,
            currency_code="USD",
        )

        assert prices["product_id"] == sample_product.id
        assert prices["base_price"] == 99.99

    @pytest.mark.asyncio
    async def test_resolve_price_no_variant(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        total, breakdown = await pricing_service.resolve_price(
            product_id=sample_product.id,
            variant_id=None,
            addon_ids=[],
            currency_code="USD",
            quantity=1,
        )

        assert total == 99.99
        assert breakdown.base_price == 99.99
        assert breakdown.variant_delta == 0.0
        assert breakdown.subtotal == 99.99
        assert breakdown.total == 99.99

    @pytest.mark.asyncio
    async def test_resolve_price_with_addons(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        addon_price = Price(
            product_id=sample_product.id,
            addon_id=1,
            currency_id=default_currency.id,
            amount=15.00,
            is_override=False,
        )
        db_session.add(addon_price)
        await db_session.flush()

        total, breakdown = await pricing_service.resolve_price(
            product_id=sample_product.id,
            variant_id=None,
            addon_ids=[1],
            currency_code="USD",
            quantity=1,
        )

        assert total == 114.99
        assert breakdown.base_price == 99.99
        assert len(breakdown.addon_deltas) == 1
        assert breakdown.addon_deltas[0].amount == 15.00

    @pytest.mark.asyncio
    async def test_resolve_price_multiple_addons(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        addon1 = Price(
            product_id=sample_product.id,
            addon_id=1,
            currency_id=default_currency.id,
            amount=10.00,
            is_override=False,
        )
        addon2 = Price(
            product_id=sample_product.id,
            addon_id=2,
            currency_id=default_currency.id,
            amount=5.00,
            is_override=False,
        )
        db_session.add(addon1)
        db_session.add(addon2)
        await db_session.flush()

        total, breakdown = await pricing_service.resolve_price(
            product_id=sample_product.id,
            variant_id=None,
            addon_ids=[1, 2],
            currency_code="USD",
            quantity=1,
        )

        assert total == 114.00
        assert len(breakdown.addon_deltas) == 2


class TestCurrencyConversion:
    @pytest.mark.asyncio
    async def test_same_currency_no_conversion(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        total, breakdown = await pricing_service.resolve_price(
            product_id=sample_product.id,
            variant_id=None,
            addon_ids=[],
            currency_code="USD",
            quantity=1,
        )

        assert breakdown.converted_from is None
        assert breakdown.exchange_rate is None

    @pytest.mark.asyncio
    async def test_create_exchange_rate(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        secondary_currency: Currency,
        pricing_service: PricingService,
    ):
        from app.modules.pricing.schemas import ExchangeRateCreate

        rate_data = ExchangeRateCreate(
            from_currency_code="USD",
            to_currency_code="EUR",
            rate=0.85,
        )
        rate = await pricing_service.create_exchange_rate(rate_data)

        assert rate.rate == 0.85
        assert rate.from_currency_id == default_currency.id
        assert rate.to_currency_id == secondary_currency.id


class TestRoundingRules:
    @pytest.mark.asyncio
    async def test_price_with_two_decimal_places(
        self,
        db_session: AsyncSession,
        default_currency: Currency,
        sample_product: Product,
        pricing_service: PricingService,
    ):
        price = await db_session.get(Price, sample_product.id)
        if not price:
            price = Price(
                product_id=sample_product.id,
                currency_id=default_currency.id,
                amount=33.33,
                is_override=False,
            )
            db_session.add(price)
            await db_session.commit()

        total, breakdown = await pricing_service.resolve_price(
            product_id=sample_product.id,
            variant_id=None,
            addon_ids=[],
            currency_code="USD",
            quantity=3,
        )

        assert total == round(total, 2)