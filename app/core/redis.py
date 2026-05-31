import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings


class RedisClient:
    def __init__(self) -> None:
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        self._pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=10,
            decode_responses=True,
        )
        self._client = Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    @property
    def client(self) -> Redis:
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> None:
        await self.client.set(key, value, ex=ex)

    async def get_json(self, key: str) -> Optional[Any]:
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> None:
        await self.set(key, json.dumps(value), ex=ex)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))


redis_client = RedisClient()


async def get_redis() -> RedisClient:
    return redis_client