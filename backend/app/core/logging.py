import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def setup_logging():
    """Configure structured logging."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.ExtraAdder(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if settings.environment == "production" 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        import time
        import uuid

        from starlette.requests import Request
        from starlette.responses import Response

        request = Request(scope, receive)

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", request_id)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        start_time = time.perf_counter()

        response_headers = {}

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                for key, value in message.get("headers", []):
                    response_headers[key.decode()] = value.decode()
                message["headers"].append((b"X-Request-ID", request_id.encode()))
                message["headers"].append((b"X-Correlation-ID", correlation_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger = get_logger(__name__)
            logger.info(
                "Request completed",
                status_code=response_headers.get("status", ""),
                duration_ms=round(duration_ms, 2),
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger = get_logger(__name__)
            logger.error(
                "Request failed with exception",
                error=str(exc),
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()
