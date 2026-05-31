from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ConflictError
from app.modules.pricing.models import Currency, ExchangeRate, Price
from app.modules.pricing.schemas import PriceBreakdown, PriceBreakdownItem
from app.modules.pricing.exchange_rates import exchange_rate_provider


class PricingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_currency(self, currency_data) -> Currency:
        existing = await self.db.execute(select(Currency).where(Currency.code == currency_data.code))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Currency with code '{currency_data.code}' already exists")

        if currency_data.is_default:
            await self.db.execute(
                select(Currency).where(Currency.is_default == True)
            )

        currency = Currency(**currency_data.model_dump())
        self.db.add(currency)
        await self.db.flush()
        await self.db.refresh(currency)
        return currency

    async def get_currency_by_id(self, currency_id: int) -> Currency:
        result = await self.db.execute(select(Currency).where(Currency.id == currency_id))
        currency = result.scalar_one_or_none()
        if not currency:
            raise NotFoundError("Currency", str(currency_id))
        return currency

    async def get_currency_by_code(self, code: str) -> Currency:
        result = await self.db.execute(select(Currency).where(Currency.code == code))
        currency = result.scalar_one_or_none()
        if not currency:
            raise NotFoundError("Currency", code)
        return currency

    async def list_currencies(self, is_active: bool = True) -> List[Currency]:
        query = select(Currency)
        if is_active is not None:
            query = query.where(Currency.is_active == is_active)
        query = query.order_by(Currency.is_default.desc(), Currency.code)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_currency(self, currency_id: int, currency_data) -> Currency:
        currency = await self.get_currency_by_id(currency_id)

        if currency_data.is_default and not currency.is_default:
            await self.db.execute(
                select(Currency).where(
                    and_(Currency.is_default == True, Currency.id != currency_id)
                )
            )

        for key, value in currency_data.model_dump(exclude_unset=True).items():
            setattr(currency, key, value)

        await self.db.flush()
        await self.db.refresh(currency)
        return currency

    async def create_exchange_rate(self, rate_data) -> ExchangeRate:
        from_currency = await self.get_currency_by_code(rate_data.from_currency_code)
        to_currency = await self.get_currency_by_code(rate_data.to_currency_code)

        existing = await self.db.execute(
            select(ExchangeRate).where(
                and_(
                    ExchangeRate.from_currency_id == from_currency.id,
                    ExchangeRate.to_currency_id == to_currency.id,
                    ExchangeRate.effective_at >= datetime.now(timezone.utc),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("An exchange rate for this currency pair already exists")

        rate = ExchangeRate(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            rate=rate_data.rate,
            effective_at=datetime.now(timezone.utc),
        )
        self.db.add(rate)
        await self.db.flush()
        await self.db.refresh(rate)
        return rate

    async def get_exchange_rate(
        self,
        from_currency_code: str,
        to_currency_code: str,
    ) -> Optional[float]:
        if from_currency_code == to_currency_code:
            return 1.0

        from_currency = await self.get_currency_by_code(from_currency_code)
        to_currency = await self.get_currency_by_code(to_currency_code)

        result = await self.db.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency_id == from_currency.id,
                    ExchangeRate.to_currency_id == to_currency.id,
                )
            )
            .order_by(ExchangeRate.effective_at.desc())
            .limit(1)
        )
        db_rate = result.scalar_one_or_none()

        if db_rate:
            return db_rate.rate

        return await exchange_rate_provider.get_rate(from_currency_code, to_currency_code)

    async def create_price(self, price_data) -> Price:
        currency = await self.get_currency_by_code(price_data.currency_code)

        existing_query = select(Price).where(
            and_(
                Price.product_id == price_data.product_id,
                Price.variant_id == price_data.variant_id,
                Price.addon_id == price_data.addon_id,
                Price.currency_id == currency.id,
            )
        )
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            raise ConflictError("Price for this combination already exists")

        price = Price(
            product_id=price_data.product_id,
            variant_id=price_data.variant_id,
            addon_id=price_data.addon_id,
            currency_id=currency.id,
            amount=price_data.amount,
            is_override=price_data.is_override,
            effective_from=price_data.effective_from,
            effective_until=price_data.effective_until,
        )
        self.db.add(price)
        await self.db.flush()
        await self.db.refresh(price)
        return price

    async def update_price(self, price_id: int, price_data) -> Price:
        result = await self.db.execute(select(Price).where(Price.id == price_id))
        price = result.scalar_one_or_none()
        if not price:
            raise NotFoundError("Price", str(price_id))

        for key, value in price_data.model_dump(exclude_unset=True).items():
            setattr(price, key, value)

        await self.db.flush()
        await self.db.refresh(price)
        return price

    async def get_product_prices(
        self,
        product_id: int,
        currency_code: str,
    ) -> Dict[str, Any]:
        currency = await self.get_currency_by_code(currency_code)

        price_result = await self.db.execute(
            select(Price).where(
                and_(
                    Price.product_id == product_id,
                    Price.currency_id == currency.id,
                    Price.variant_id.is_(None),
                    Price.addon_id.is_(None),
                )
            )
        )
        product_price = price_result.scalar_one_or_none()

        variant_prices_result = await self.db.execute(
            select(Price).where(
                and_(
                    Price.product_id == product_id,
                    Price.currency_id == currency.id,
                    Price.variant_id.isnot(None),
                )
            )
        )
        variant_prices = list(variant_prices_result.scalars().all())

        return {
            "product_id": product_id,
            "currency": currency,
            "base_price": product_price.amount if product_price else 0.0,
            "variant_prices": variant_prices,
        }

    async def resolve_price(
        self,
        product_id: int,
        variant_id: Optional[int],
        addon_ids: List[int],
        currency_code: str,
        quantity: int = 1,
    ) -> Tuple[float, PriceBreakdown]:
        currency = await self.get_currency_by_code(currency_code)

        base_price_result = await self.db.execute(
            select(Price).where(
                and_(
                    Price.product_id == product_id,
                    Price.currency_id == currency.id,
                    Price.variant_id.is_(None),
                    Price.addon_id.is_(None),
                )
            )
        )
        base_price_record = base_price_result.scalar_one_or_none()
        base_price = base_price_record.amount if base_price_record else 0.0

        variant_delta = 0.0
        if variant_id:
            variant_price_result = await self.db.execute(
                select(Price).where(
                    and_(
                        Price.variant_id == variant_id,
                        Price.currency_id == currency.id,
                    )
                )
            )
            variant_price_record = variant_price_result.scalar_one_or_none()
            if variant_price_record:
                variant_delta = variant_price_record.amount

        addon_deltas: List[PriceBreakdownItem] = []
        addon_total = 0.0
        for addon_id in addon_ids:
            addon_price_result = await self.db.execute(
                select(Price).where(
                    and_(
                        Price.addon_id == addon_id,
                        Price.currency_id == currency.id,
                    )
                )
            )
            addon_price_record = addon_price_result.scalar_one_or_none()
            if addon_price_record:
                addon_deltas.append(
                    PriceBreakdownItem(
                        label=f"Addon {addon_id}",
                        amount=addon_price_record.amount,
                        currency=currency_code,
                    )
                )
                addon_total += addon_price_record.amount

        subtotal = base_price + variant_delta + addon_total

        converted_from = None
        exchange_rate = None
        if currency_code != "USD":
            usd_rate = await self.get_exchange_rate("USD", currency_code)
            if usd_rate and usd_rate != 1.0:
                converted_from = "USD"
                exchange_rate = usd_rate

        tax_estimate = subtotal * 0.0
        shipping_estimate = 0.0
        discount = 0.0
        total = subtotal + tax_estimate + shipping_estimate - discount

        breakdown = PriceBreakdown(
            base_price=base_price,
            variant_delta=variant_delta,
            addon_deltas=addon_deltas,
            subtotal=subtotal,
            tax_estimate=tax_estimate,
            shipping_estimate=shipping_estimate,
            discount=discount,
            total=total,
            currency=currency_code,
            converted_from=converted_from,
            exchange_rate=exchange_rate,
        )

        return subtotal, breakdown

    async def list_exchange_rates(
        self,
        from_currency_code: Optional[str] = None,
        to_currency_code: Optional[str] = None,
    ) -> List[ExchangeRate]:
        query = select(ExchangeRate)

        if from_currency_code:
            currency = await self.get_currency_by_code(from_currency_code)
            query = query.where(ExchangeRate.from_currency_id == currency.id)

        if to_currency_code:
            currency = await self.get_currency_by_code(to_currency_code)
            query = query.where(ExchangeRate.to_currency_id == currency.id)

        query = query.order_by(ExchangeRate.effective_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())