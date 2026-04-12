import asyncio
import json
import logging
from typing import Any, Optional, Union

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_redis_lock = asyncio.Lock()


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        async with _redis_lock:
            if _redis_client is None:
                _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class Cache:

    @staticmethod
    async def get(key: str) -> Optional[str]:
        try:
            r = await get_redis()
            return await r.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {e}")
            # Re-raise connection errors so caller can handle appropriately
            raise

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        value = await Cache.get(key)
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid JSON in cache for key '{key}'")
                await Cache.delete(key)
        return None

    @staticmethod
    async def set(
        key: str,
        value: Union[str, bytes, int, float],
        expire: Optional[int] = None,
    ):
        try:
            r = await get_redis()
            await r.set(key, value, ex=expire)
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {e}")

    @staticmethod
    async def set_json(key: str, value: Any, expire: Optional[int] = None):
        await Cache.set(key, json.dumps(value), expire)

    @staticmethod
    async def delete(key: str):
        try:
            r = await get_redis()
            await r.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {e}")

    @staticmethod
    async def exists(key: str) -> bool:
        try:
            r = await get_redis()
            return await r.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists failed for key '{key}': {e}")
            return False

    @staticmethod
    async def expire(key: str, seconds: int):
        try:
            r = await get_redis()
            await r.expire(key, seconds)
        except Exception as e:
            logger.warning(f"Cache expire failed for key '{key}': {e}")


class DistributedLock:

    def __init__(self, redis_client: redis.Redis, lock_key: str, timeout: int = 300):
        self.redis = redis_client
        self.lock_key = f"lock:{lock_key}"
        self.timeout = timeout
        self.lock_value = None

    async def acquire(self) -> bool:
        import uuid

        lock_value = str(uuid.uuid4())
        acquired = await self.redis.set(
            self.lock_key, lock_value, nx=True, ex=self.timeout
        )
        if acquired:
            self.lock_value = lock_value
        return acquired is not None

    async def release(self):
        if self.lock_value:
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self.redis.eval(lua_script, 1, self.lock_key, self.lock_value)
            self.lock_value = None

    async def __aenter__(self):
        if not await self.acquire():
            raise Exception(f"Could not acquire lock: {self.lock_key}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
