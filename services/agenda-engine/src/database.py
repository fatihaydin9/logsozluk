import asyncpg
import redis.asyncio as redis
from typing import Optional
from contextlib import asynccontextmanager

from .config import get_settings


class Database:
    _pool: Optional[asyncpg.Pool] = None
    _redis: Optional[redis.Redis] = None

    @classmethod
    async def connect(cls):
        settings = get_settings()
        cls._pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=20
        )
        cls._redis = redis.from_url(settings.redis_url)

    @classmethod
    async def disconnect(cls):
        if cls._pool:
            await cls._pool.close()
        if cls._redis:
            await cls._redis.close()

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            raise RuntimeError("Database not connected")
        return cls._pool

    @classmethod
    def get_redis(cls) -> redis.Redis:
        if cls._redis is None:
            raise RuntimeError("Redis not connected")
        return cls._redis

    @classmethod
    @asynccontextmanager
    async def connection(cls):
        async with cls._pool.acquire() as conn:
            yield conn


async def get_db():
    return Database.get_pool()


async def get_redis():
    return Database.get_redis()
