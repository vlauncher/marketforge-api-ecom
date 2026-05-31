import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.core.redis import redis_client


class ExchangeRateProvider:
    def __init__(self) -> None:
        self.api_key = settings.EXCHANGE_RATE_API_KEY
        self.api_url = settings.EXCHANGE_RATE_API_URL
        self.cache_key_prefix = "exchange_rate:"
        self.cache_ttl = 3600

    async def fetch_rates(self, base_currency: str = "USD") -> Dict[str, Any]:
        cache_key = f"{self.cache_key_prefix}{base_currency}"

        cached = await redis_client.get_json(cache_key)
        if cached:
            return cached

        if not self.api_key:
            return await self._get_default_rates(base_currency)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/{base_currency}",
                    headers={"Authorization": f"ApiKey {self.api_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                rates = {
                    "base": base_currency,
                    "rates": data.get("rates", {}),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                await redis_client.set_json(cache_key, rates, ex=self.cache_ttl)
                return rates

        except httpx.HTTPError:
            return await self._get_default_rates(base_currency)

    async def _get_default_rates(self, base_currency: str) -> Dict[str, Any]:
        default_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0,
            "CAD": 1.25,
            "AUD": 1.35,
            "CHF": 0.92,
            "CNY": 6.45,
            "INR": 74.5,
            "MXN": 20.0,
        }

        if base_currency == "USD":
            return {
                "base": base_currency,
                "rates": default_rates,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

        base_rate = default_rates.get(base_currency, 1.0)
        converted = {
            code: rate / base_rate for code, rate in default_rates.items()
        }
        return {
            "base": base_currency,
            "rates": converted,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[float]:
        if from_currency == to_currency:
            return 1.0

        rates_data = await self.fetch_rates(from_currency)
        rates = rates_data.get("rates", {})

        if to_currency in rates:
            return rates[to_currency]

        inverse_rates = await self.fetch_rates(to_currency)
        inverse = inverse_rates.get("rates", {})
        if from_currency in inverse:
            return 1.0 / inverse[from_currency]

        return None


exchange_rate_provider = ExchangeRateProvider()