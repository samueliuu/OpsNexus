from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import RateLimitException
from app.core.ratelimit import rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.rate_limit_enabled

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")[:50]
        key = f"{client_ip}:{user_agent}"

        if not await rate_limiter.is_allowed(key):
            raise RateLimitException()

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(await rate_limiter.get_remaining(key))
        return response
