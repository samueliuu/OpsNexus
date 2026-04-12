import asyncio
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.cache import close_redis
from app.core.config import settings
from app.core.database import AsyncSessionLocal, close_db, init_db
from app.core.events import event_bus
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    BMCAuthenticationException,
    BMCConnectionException,
    ConflictException,
    NotFoundException,
    OpsNexusException,
    RateLimitException,
    ValidationException,
    general_exception_handler,
    http_exception_handler,
    opsnexus_exception_handler,
    validation_exception_handler,
)
from app.core.logging import LoggingMiddleware, get_logger, setup_logging
from app.core.middleware import RateLimitMiddleware
from app.modules import asset, audit, autoops, knowledge, monitor, outband, system
from app.integrations import router as netbox_router

logger = get_logger(__name__)


AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PATHS = {
    "/api/v1/system/auth/login",
    "/api/v1/system/auth/register",
    "/api/v1/system/auth/refresh",
    "/api/v1/system/auth/me",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
    "/api/v1/health",
}


class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        if request.method not in AUDITED_METHODS or path in SKIP_PATHS or path.endswith("/health"):
            await self.app(scope, receive, send)
            return

        from app.modules.audit.service import (
            AUDIT_ACTION_MAP,
            SKIP_AUDIT_PATHS,
            parse_resource_from_path,
        )

        if path in SKIP_AUDIT_PATHS:
            await self.app(scope, receive, send)
            return

        response_status = 200
        original_send = send

        async def custom_send(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            await original_send(message)

        await self.app(scope, receive, custom_send)

        try:
            user_id = None
            username = None
            request_id = None

            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                try:
                    from uuid import UUID as UUIDType
                    from app.core.security import decode_token
                    token_data = decode_token(auth_header.split(" ")[1])
                    if token_data:
                        user_id_str = token_data.get("sub")
                        if user_id_str:
                            try:
                                user_id = UUIDType(user_id_str)
                            except ValueError:
                                user_id = None
                        username = token_data.get("username")
                except Exception:
                    pass

            request_id = request.headers.get("x-request-id")
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:512]

            action = AUDIT_ACTION_MAP.get(request.method, request.method.lower())
            resource_type = parse_resource_from_path(path)

            path_parts = path.strip("/").split("/")
            resource_id = None
            for i, part in enumerate(path_parts):
                if len(part) == 36 and "-" in part:
                    try:
                        from uuid import UUID as UUIDType
                        UUIDType(part)
                        resource_id = part
                        break
                    except ValueError:
                        pass

            audit_status = "success" if response_status < 400 else "failure"

            async with AsyncSessionLocal() as session:
                from app.modules.audit.service import AuditLogService
                service = AuditLogService(session)
                await service.create_log_from_request(
                    user_id=user_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    status=audit_status,
                )
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    await init_db()
    logger.info(f"{settings.app_name} started", version=settings.app_version)

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received", signal=sig)
        shutdown_event.set()

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    yield

    # Shutdown
    logger.info("Shutting down gracefully...")
    await event_bus.disconnect()
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="服务器运维知识助手平台",
    lifespan=lifespan,
)

# Middleware (LIFO order: last added = outermost = first executed)
app.add_middleware(AuditMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
)

# Exception handlers
app.add_exception_handler(OpsNexusException, opsnexus_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitException, opsnexus_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(system.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(asset.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")
app.include_router(outband.router, prefix="/api/v1")
app.include_router(autoops.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(netbox_router, prefix="/api/v1/integrations")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/api/v1/health")
async def health_check():
    """Global health check."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }
