from typing import AsyncGenerator, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.exceptions import AuthenticationException, AuthorizationException

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db=Depends(get_db),
):
    if not credentials:
        raise AuthenticationException("Authentication required")

    from app.modules.system.service import AuthService
    auth_service = AuthService(db)
    return await auth_service.get_current_user(credentials.credentials)


async def get_current_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise AuthorizationException("User is inactive")
    return current_user


class PermissionChecker:
    def __init__(self, resource: str, action: str):
        self.resource = resource
        self.action = action

    async def __call__(
        self,
        current_user=Depends(get_current_active_user),
        db=Depends(get_db),
    ):
        from app.modules.system.service import UserService
        user_service = UserService(db)
        if not await user_service.check_permission(current_user, self.resource, self.action):
            raise AuthorizationException(
                f"Permission denied: {self.resource}:{self.action}"
            )
        return current_user


require_user_read = PermissionChecker("system:user", "read")
require_user_write = PermissionChecker("system:user", "write")
require_role_read = PermissionChecker("system:role", "read")
require_role_write = PermissionChecker("system:role", "write")
require_config_read = PermissionChecker("system:config", "read")
require_config_write = PermissionChecker("system:config", "write")
