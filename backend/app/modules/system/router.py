from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.modules.system.models import User
from app.modules.system.schemas import (
    LoginRequest,
    LoginResponse,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    PermissionResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    SystemConfigCreate,
    SystemConfigResponse,
    SystemConfigUpdate,
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
    WebSocketTicketResponse,
)
from app.modules.system.service import (
    AuthService,
    NotificationChannelService,
    RoleService,
    SystemConfigService,
    UserService,
)

router = APIRouter(prefix="/system", tags=["System"])


# Auth endpoints
@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db=Depends(get_db)):
    """User login."""
    auth_service = AuthService(db)
    user, access_token, refresh_token = await auth_service.authenticate(request)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db=Depends(get_db)):
    """User self-registration."""
    auth_service = AuthService(db)
    user = await auth_service.register(request)
    return user


@router.post("/auth/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest, db=Depends(get_db)):
    """Refresh access token."""
    auth_service = AuthService(db)
    access_token, new_refresh_token = await auth_service.refresh_access_token(request.refresh_token)

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info."""
    return current_user


@router.post("/auth/ws-ticket", response_model=WebSocketTicketResponse)
async def create_ws_ticket(
    current_user: User = Depends(get_current_active_user), db=Depends(get_db)
):
    """Create WebSocket connection ticket."""
    auth_service = AuthService(db)
    ticket = await auth_service.generate_ws_ticket(current_user.id)
    return WebSocketTicketResponse(ticket=ticket, expires_in=30)


# User endpoints
@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(PermissionChecker("system:user", "read"))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db=Depends(get_db),
):
    """List users."""
    user_service = UserService(db)
    users, total = await user_service.list_users(skip, limit, search, is_active)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(PermissionChecker("system:user", "read"))],
)
async def get_user(user_id: UUID, db=Depends(get_db)):
    """Get user by ID."""
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    return user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker("system:user", "write"))],
)
async def create_user(user_data: UserCreate, db=Depends(get_db)):
    """Create new user."""
    user_service = UserService(db)
    user = await user_service.create_user(user_data)
    return user


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(PermissionChecker("system:user", "write"))],
)
async def update_user(user_id: UUID, user_data: UserUpdate, db=Depends(get_db)):
    """Update user."""
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_data)
    return user


@router.put("/users/{user_id}/password", dependencies=[Depends(get_current_active_user)])
async def update_password(
    user_id: UUID,
    password_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    if str(current_user.id) != str(user_id) and not current_user.is_superuser:
        from app.core.exceptions import AuthorizationException
        raise AuthorizationException("Can only change your own password")

    user_service = UserService(db)
    is_self = str(current_user.id) == str(user_id)
    await user_service.update_password(
        user_id, password_data.old_password, password_data.new_password,
        skip_old_password_verify=not is_self,
    )
    return {"message": "Password updated successfully"}


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker("system:user", "write"))],
)
async def delete_user(user_id: UUID, db=Depends(get_db)):
    """Delete user."""
    user_service = UserService(db)
    await user_service.delete_user(user_id)
    return None


# Role endpoints
@router.get(
    "/roles",
    response_model=RoleListResponse,
    dependencies=[Depends(PermissionChecker("system:role", "read"))],
)
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db=Depends(get_db),
):
    """List roles."""
    role_service = RoleService(db)
    roles, total = await role_service.list_roles(skip, limit)
    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(PermissionChecker("system:role", "read"))],
)
async def get_role(role_id: UUID, db=Depends(get_db)):
    """Get role by ID."""
    role_service = RoleService(db)
    role = await role_service.get_role(role_id)
    return role


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker("system:role", "write"))],
)
async def create_role(role_data: RoleCreate, db=Depends(get_db)):
    """Create new role."""
    role_service = RoleService(db)
    role = await role_service.create_role(role_data)
    return role


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(PermissionChecker("system:role", "write"))],
)
async def update_role(role_id: UUID, role_data: RoleUpdate, db=Depends(get_db)):
    """Update role."""
    role_service = RoleService(db)
    role = await role_service.update_role(role_id, role_data)
    return role


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker("system:role", "write"))],
)
async def delete_role(role_id: UUID, db=Depends(get_db)):
    """Delete role."""
    role_service = RoleService(db)
    await role_service.delete_role(role_id)
    return None


# Permission endpoints
@router.get(
    "/permissions",
    response_model=List[PermissionResponse],
    dependencies=[Depends(PermissionChecker("system:role", "read"))],
)
async def list_permissions(db=Depends(get_db)):
    from app.modules.system.service import PermissionService
    permission_service = PermissionService(db)
    permissions, _ = await permission_service.list_permissions()
    return permissions


# System config endpoints
@router.get(
    "/configs",
    response_model=List[SystemConfigResponse],
    dependencies=[Depends(PermissionChecker("system:config", "read"))],
)
async def list_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db=Depends(get_db),
):
    """List system configs."""
    config_service = SystemConfigService(db)
    configs, _ = await config_service.list_configs(skip, limit)
    return configs


@router.get(
    "/configs/{config_id}",
    response_model=SystemConfigResponse,
    dependencies=[Depends(PermissionChecker("system:config", "read"))],
)
async def get_config(config_id: UUID, db=Depends(get_db)):
    """Get config by ID."""
    config_service = SystemConfigService(db)
    config = await config_service.get_config(config_id)
    return config


@router.post(
    "/configs",
    response_model=SystemConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker("system:config", "write"))],
)
async def create_config(config_data: SystemConfigCreate, db=Depends(get_db)):
    """Create system config."""
    config_service = SystemConfigService(db)
    config = await config_service.create_config(config_data)
    return config


@router.put(
    "/configs/{config_id}",
    response_model=SystemConfigResponse,
    dependencies=[Depends(PermissionChecker("system:config", "write"))],
)
async def update_config(config_id: UUID, config_data: SystemConfigUpdate, db=Depends(get_db)):
    """Update system config."""
    config_service = SystemConfigService(db)
    config = await config_service.update_config(config_id, config_data)
    return config


@router.delete(
    "/configs/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker("system:config", "write"))],
)
async def delete_config(config_id: UUID, db=Depends(get_db)):
    """Delete system config."""
    config_service = SystemConfigService(db)
    await config_service.delete_config(config_id)
    return None


# Notification channel endpoints
@router.get(
    "/notification-channels",
    response_model=List[NotificationChannelResponse],
    dependencies=[Depends(PermissionChecker("system:channel", "read"))],
)
async def list_notification_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    is_enabled: Optional[bool] = None,
    db=Depends(get_db),
):
    channel_service = NotificationChannelService(db)
    channels, _ = await channel_service.list_channels(skip, limit, is_enabled)
    return channels


@router.get(
    "/notification-channels/{channel_id}",
    response_model=NotificationChannelResponse,
    dependencies=[Depends(PermissionChecker("system:channel", "read"))],
)
async def get_notification_channel(channel_id: UUID, db=Depends(get_db)):
    channel_service = NotificationChannelService(db)
    channel = await channel_service.get_channel(channel_id)
    return channel


@router.post(
    "/notification-channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker("system:channel", "write"))],
)
async def create_notification_channel(
    channel_data: NotificationChannelCreate, db=Depends(get_db)
):
    channel_service = NotificationChannelService(db)
    channel = await channel_service.create_channel(channel_data)
    return channel


@router.put(
    "/notification-channels/{channel_id}",
    response_model=NotificationChannelResponse,
    dependencies=[Depends(PermissionChecker("system:channel", "write"))],
)
async def update_notification_channel(
    channel_id: UUID, channel_data: NotificationChannelUpdate, db=Depends(get_db)
):
    channel_service = NotificationChannelService(db)
    channel = await channel_service.update_channel(channel_id, channel_data)
    return channel


@router.delete(
    "/notification-channels/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker("system:channel", "write"))],
)
async def delete_notification_channel(channel_id: UUID, db=Depends(get_db)):
    channel_service = NotificationChannelService(db)
    await channel_service.delete_channel(channel_id)
    return None


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "system",
        "version": settings.app_version,
    }
