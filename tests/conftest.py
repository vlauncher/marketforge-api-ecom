import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.modules.identity.models import User, UserRole
from app.modules.vendors.models import Vendor, VendorProfile, VendorStatus
from app.modules.storefronts.models import Store
from app.modules.catalog.models import Category, Brand, Product, ProductVariant, ProductType
from app.modules.pricing.models import Currency, ExchangeRate, Price
from app.modules.inventory.models import InventoryLocation, InventoryItem, MovementType
from app.modules.promotions.models import Coupon, Promotion, DiscountType


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def default_currency(db_session: AsyncSession) -> Currency:
    currency = Currency(
        code="USD",
        name="US Dollar",
        symbol="$",
        is_default=True,
        is_active=True,
        decimal_places=2,
    )
    db_session.add(currency)
    await db_session.commit()
    await db_session.refresh(currency)
    return currency


@pytest_asyncio.fixture
async def secondary_currency(db_session: AsyncSession) -> Currency:
    currency = Currency(
        code="EUR",
        name="Euro",
        symbol="€",
        is_default=False,
        is_active=True,
        decimal_places=2,
    )
    db_session.add(currency)
    await db_session.commit()
    await db_session.refresh(currency)
    return currency


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    from app.core.security import get_password_hash

    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_vendor(db_session: AsyncSession, sample_user: User) -> Vendor:
    vendor = Vendor(
        user_id=sample_user.id,
        name="Test Vendor",
        slug="test-vendor",
        status=VendorStatus.VERIFIED,
        commission_rate=0.10,
    )
    db_session.add(vendor)
    await db_session.commit()
    await db_session.refresh(vendor)
    return vendor


@pytest_asyncio.fixture
async def sample_store(db_session: AsyncSession, sample_vendor: Vendor) -> Store:
    store = Store(
        vendor_id=sample_vendor.id,
        name="Test Store",
        slug="test-store",
        description="A test store",
        is_active=True,
    )
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> Category:
    category = Category(
        name="Electronics",
        slug="electronics",
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def sample_product(
    db_session: AsyncSession,
    sample_store: Store,
    sample_category: Category,
    default_currency: Currency,
) -> Product:
    product = Product(
        store_id=sample_store.id,
        category_id=sample_category.id,
        name="Test Product",
        slug="test-product",
        description="A test product",
        is_active=True,
        product_type=ProductType.PHYSICAL,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    price = Price(
        product_id=product.id,
        currency_id=default_currency.id,
        amount=99.99,
        is_override=False,
    )
    db_session.add(price)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def sample_inventory_item(
    db_session: AsyncSession,
    sample_store: Store,
    sample_product: Product,
) -> InventoryItem:
    location = InventoryLocation(
        store_id=sample_store.id,
        name="Main Warehouse",
        is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    item = InventoryItem(
        location_id=location.id,
        product_id=sample_product.id,
        variant_id=None,
        quantity=100,
        reserved_quantity=0,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def sample_coupon(db_session: AsyncSession, sample_store: Store) -> Coupon:
    coupon = Coupon(
        store_id=sample_store.id,
        code="SAVE10",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=10.0,
        min_order_amount=0.0,
        max_uses=100,
        is_active=True,
        valid_from=datetime.now(timezone.utc),
        valid_until=datetime.now(timezone.utc),
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


class MockExchangeRateProvider:
    _rates = {
        ("USD", "EUR"): 0.85,
        ("EUR", "USD"): 1.18,
        ("USD", "GBP"): 0.73,
        ("GBP", "USD"): 1.37,
    }

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        return self._rates.get((from_currency, to_currency), 1.0)


@pytest.fixture
def mock_exchange_rate_provider() -> MockExchangeRateProvider:
    return MockExchangeRateProvider()