import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    NotFoundException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.modules.system.models import (
    NotificationChannel,
    Permission,
    Role,
    SystemConfig,
    User,
)
from app.modules.system.repository import (
    NotificationChannelRepository,
    PermissionRepository,
    RoleRepository,
    SystemConfigRepository,
    UserRepository,
)
from app.modules.system.schemas import (
    LoginRequest,
    NotificationChannelCreate,
    NotificationChannelUpdate,
    RoleCreate,
    RoleUpdate,
    SystemConfigCreate,
    SystemConfigUpdate,
    UserCreate,
    UserUpdate,
    RegisterRequest,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)

    async def authenticate(self, login_data: LoginRequest) -> tuple[User, str, str]:
        """Authenticate user and return tokens."""
        user = await self.user_repo.get_by_username(login_data.username)
        if not user or not user.is_active:
            raise AuthenticationException("Invalid username or password")

        if not verify_password(login_data.password, user.password_hash):
            raise AuthenticationException("Invalid username or password")

        # Update last login
        await self.user_repo.update(user.id, last_login_at=datetime.now(timezone.utc))

        # Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"username": user.username, "is_superuser": user.is_superuser},
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> tuple:
        """Refresh access token and rotate refresh token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationException("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Invalid refresh token: missing subject")
        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise AuthenticationException("User not found or inactive")

        new_access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"username": user.username, "is_superuser": user.is_superuser},
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return new_access_token, new_refresh_token

    async def get_current_user(self, token: str) -> User:
        """Get current user from token."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise AuthenticationException("Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationException("Invalid token: missing subject")
        user = await self.user_repo.get_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise AuthenticationException("User not found or inactive")

        return user

    async def generate_ws_ticket(self, user_id: UUID) -> str:
        """Generate WebSocket connection ticket."""
        ticket = str(uuid.uuid4())
        await Cache.set(
            f"ws_ticket:{ticket}",
            str(user_id),
            expire=30,  # 30 seconds
        )
        return ticket

    async def validate_ws_ticket(self, ticket: str) -> Optional[UUID]:
        """Validate WebSocket ticket."""
        user_id = await Cache.get(f"ws_ticket:{ticket}")
        if user_id:
            await Cache.delete(f"ws_ticket:{ticket}")  # One-time use
            return UUID(user_id)
        return None

    async def register(self, data: RegisterRequest) -> User:
        """User self-registration."""
        existing = await self.user_repo.get_by_username(data.username)
        if existing:
            raise ConflictException(f"Username '{data.username}' already exists")

        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictException(f"Email '{data.email}' already exists")

        user = User(
            id=uuid.uuid4(),
            username=data.username,
            email=data.email,
            password_hash=get_password_hash(data.password),
            full_name=data.full_name,
            phone=data.phone,
            user_type=data.user_type,
            company=data.company,
            title=data.title,
            is_active=True,
            is_superuser=False,
        )

        return await self.user_repo.create(user)


class UserService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        return user

    async def get_user_by_username(self, username: str) -> User:
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise NotFoundException("User", username)
        return user

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[User], int]:
        return await self.user_repo.list_users(skip, limit, search, is_active)

    async def create_user(self, user_data: UserCreate) -> User:
        # Check username uniqueness
        existing = await self.user_repo.get_by_username(user_data.username)
        if existing:
            raise ConflictException(f"Username '{user_data.username}' already exists")

        # Check email uniqueness
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise ConflictException(f"Email '{user_data.email}' already exists")

        # Create user
        user = User(
            id=uuid.uuid4(),
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            department=user_data.department,
            is_active=user_data.is_active,
        )

        # Assign roles
        if user_data.role_ids:
            for role_id in user_data.role_ids:
                role = await self.role_repo.get_by_id(role_id)
                if not role:
                    raise NotFoundException("Role", str(role_id))
                user.roles.append(role)

        return await self.user_repo.create(user)

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        user = await self.get_user(user_id)

        if user_data.email and user_data.email != user.email:
            existing = await self.user_repo.get_by_email(user_data.email)
            if existing:
                raise ConflictException(f"Email '{user_data.email}' already exists")

        update_data = user_data.model_dump(exclude_unset=True, exclude={"role_ids"})
        if update_data:
            user = await self.user_repo.update(user_id, **update_data)

        # Update roles if provided
        if user_data.role_ids is not None:
            user.roles = []
            for role_id in user_data.role_ids:
                role = await self.role_repo.get_by_id(role_id)
                if not role:
                    raise NotFoundException("Role", str(role_id))
                user.roles.append(role)

        return user

    async def update_password(
        self, user_id: UUID, old_password: str, new_password: str,
        skip_old_password_verify: bool = False,
    ) -> User:
        user = await self.get_user(user_id)

        if not skip_old_password_verify:
            if not verify_password(old_password, user.password_hash):
                raise AuthenticationException("Invalid old password")

        return await self.user_repo.update(
            user_id,
            password_hash=get_password_hash(new_password),
            password_changed_at=datetime.now(timezone.utc),
        )

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.get_user(user_id)
        if user.is_superuser:
            raise AuthorizationException("Cannot delete superuser")
        return await self.user_repo.delete(user_id)

    async def check_permission(self, user: User, resource: str, action: str) -> bool:
        """Check if user has specific permission."""
        if user.is_superuser:
            return True

        required_code = f"{resource}:{action}"
        for role in user.roles:
            for permission in role.permissions:
                if permission.code == required_code:
                    return True
                if permission.code.endswith(":*"):
                    prefix = permission.code[:-1]
                    if required_code.startswith(prefix):
                        return True
        return False


class RoleService:
    def __init__(self, session: AsyncSession):
        self.role_repo = RoleRepository(session)
        self.permission_repo = PermissionRepository(session)

    async def get_role(self, role_id: UUID) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException("Role", str(role_id))
        return role

    async def list_roles(self, skip: int = 0, limit: int = 100) -> tuple[List[Role], int]:
        return await self.role_repo.list_roles(skip, limit)

    async def create_role(self, role_data: RoleCreate) -> Role:
        # Check code uniqueness
        existing = await self.role_repo.get_by_code(role_data.code)
        if existing:
            raise ConflictException(f"Role code '{role_data.code}' already exists")

        role = Role(
            id=uuid.uuid4(),
            name=role_data.name,
            code=role_data.code,
            description=role_data.description,
            data_scope=role_data.data_scope,
        )

        # Assign permissions
        if role_data.permission_ids:
            for perm_id in role_data.permission_ids:
                perm = await self.permission_repo.get_by_id(perm_id)
                if not perm:
                    raise NotFoundException("Permission", str(perm_id))
                role.permissions.append(perm)

        return await self.role_repo.create(role)

    async def update_role(self, role_id: UUID, role_data: RoleUpdate) -> Role:
        role = await self.get_role(role_id)

        if role.is_builtin:
            raise AuthorizationException("Cannot modify builtin role")

        update_data = role_data.model_dump(exclude_unset=True, exclude={"permission_ids"})
        if update_data:
            role = await self.role_repo.update(role_id, **update_data)

        # Update permissions if provided
        if role_data.permission_ids is not None:
            role.permissions = []
            for perm_id in role_data.permission_ids:
                perm = await self.permission_repo.get_by_id(perm_id)
                if not perm:
                    raise NotFoundException("Permission", str(perm_id))
                role.permissions.append(perm)

        return role

    async def delete_role(self, role_id: UUID) -> bool:
        role = await self.get_role(role_id)
        if role.is_builtin:
            raise AuthorizationException("Cannot delete builtin role")
        if role.users and len(role.users) > 0:
            raise ConflictException(f"Role '{role.name}' is still assigned to {len(role.users)} user(s). Please reassign users before deleting.")
        return await self.role_repo.delete(role_id)


class PermissionService:
    def __init__(self, session: AsyncSession):
        self.permission_repo = PermissionRepository(session)

    async def get_permission(self, permission_id: UUID) -> Permission:
        permission = await self.permission_repo.get_by_id(permission_id)
        if not permission:
            raise NotFoundException("Permission", str(permission_id))
        return permission

    async def list_permissions(
        self, skip: int = 0, limit: int = 100, resource: Optional[str] = None
    ) -> tuple[List[Permission], int]:
        return await self.permission_repo.list_permissions(skip, limit, resource)


class SystemConfigService:
    def __init__(self, session: AsyncSession):
        self.config_repo = SystemConfigRepository(session)

    async def get_config(self, config_id: UUID) -> SystemConfig:
        config = await self.config_repo.get_by_id(config_id)
        if not config:
            raise NotFoundException("SystemConfig", str(config_id))
        return config

    async def get_config_by_key(self, key: str) -> Optional[SystemConfig]:
        return await self.config_repo.get_by_key(key)

    async def get_config_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        config = await self.config_repo.get_by_key(key)
        return config.value if config else default

    async def list_configs(self, skip: int = 0, limit: int = 100) -> tuple[List[SystemConfig], int]:
        return await self.config_repo.list_configs(skip, limit)

    async def create_config(self, config_data: SystemConfigCreate) -> SystemConfig:
        # Check key uniqueness
        existing = await self.config_repo.get_by_key(config_data.key)
        if existing:
            raise ConflictException(f"Config key '{config_data.key}' already exists")

        config = SystemConfig(
            id=uuid.uuid4(),
            key=config_data.key,
            value=config_data.value,
            value_type=config_data.value_type,
            description=config_data.description,
            is_sensitive=config_data.is_sensitive,
        )
        return await self.config_repo.create(config)

    async def update_config(self, config_id: UUID, config_data: SystemConfigUpdate) -> SystemConfig:
        config = await self.get_config(config_id)
        update_data = config_data.model_dump(exclude_unset=True)
        return await self.config_repo.update(config_id, **update_data)

    async def delete_config(self, config_id: UUID) -> bool:
        return await self.config_repo.delete(config_id)


class NotificationChannelService:
    def __init__(self, session: AsyncSession):
        self.channel_repo = NotificationChannelRepository(session)

    async def get_channel(self, channel_id: UUID) -> NotificationChannel:
        channel = await self.channel_repo.get_by_id(channel_id)
        if not channel:
            raise NotFoundException("NotificationChannel", str(channel_id))
        return channel

    async def list_channels(
        self, skip: int = 0, limit: int = 100, is_enabled: Optional[bool] = None
    ) -> tuple[List[NotificationChannel], int]:
        return await self.channel_repo.list_channels(skip, limit, is_enabled)

    async def create_channel(self, channel_data: NotificationChannelCreate) -> NotificationChannel:
        channel = NotificationChannel(
            id=uuid.uuid4(),
            name=channel_data.name,
            channel_type=channel_data.channel_type,
            config=channel_data.config,
            is_enabled=channel_data.is_enabled,
        )
        return await self.channel_repo.create(channel)

    async def update_channel(
        self, channel_id: UUID, channel_data: NotificationChannelUpdate
    ) -> NotificationChannel:
        channel = await self.get_channel(channel_id)
        update_data = channel_data.model_dump(exclude_unset=True)
        if "config" in update_data and isinstance(update_data["config"], str):
            update_data["config"] = json.loads(update_data["config"])
        return await self.channel_repo.update(channel_id, **update_data)

    async def delete_channel(self, channel_id: UUID) -> bool:
        return await self.channel_repo.delete(channel_id)
