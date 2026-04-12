from datetime import datetime, timezone
from typing import Optional

from redis import asyncio as aioredis

from app.core.cache import get_redis
from app.core.config import settings


class RateLimiter:
    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        self.redis = redis_client
        self.enabled = settings.rate_limit_enabled
        self.requests_per_minute = settings.rate_limit_requests_per_minute
        self.burst = settings.rate_limit_burst

    async def _get_redis(self) -> aioredis.Redis:
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    async def is_allowed(self, key: str) -> bool:
        if not self.enabled:
            return True

        redis = await self._get_redis()
        current_time = int(datetime.now(timezone.utc).timestamp())
        window_start = current_time - (current_time % 60)

        window_key = f"ratelimit:{key}:{window_start}"

        try:
            pipe = redis.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, 120)
            results = await pipe.execute()

            current_count = results[0]
            return current_count <= self.requests_per_minute + self.burst
        except Exception:
            return True

    async def get_remaining(self, key: str) -> int:
        if not self.enabled:
            return self.requests_per_minute + self.burst

        redis = await self._get_redis()
        current_time = int(datetime.now(timezone.utc).timestamp())
        window_start = current_time - (current_time % 60)
        window_key = f"ratelimit:{key}:{window_start}"

        try:
            count = await redis.get(window_key)
            current_count = int(count) if count else 0
            return max(0, self.requests_per_minute + self.burst - current_count)
        except Exception:
            return self.requests_per_minute + self.burst


rate_limiter = RateLimiter()
