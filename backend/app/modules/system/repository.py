from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.system.models import (
    NotificationChannel,
    Permission,
    Role,
    SystemConfig,
    User,
)


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[User], int]:
        query = select(User).options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
        count_query = select(func.count(User.id))

        if search:
            s = _escape_like(search)
            search_filter = (
                (User.username.ilike(f"%{s}%", escape="\\"))
                | (User.full_name.ilike(f"%{s}%", escape="\\"))
                | (User.email.ilike(f"%{s}%", escape="\\"))
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user_id: UUID, **kwargs) -> Optional[User]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(User).where(User.id == user_id).values(**filtered)
            )
        return await self.get_by_id(user_id)

    async def delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            await self.session.delete(user)
            return True
        return False


class RoleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Optional[Role]:
        result = await self.session.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions), selectinload(Role.users))
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Role]:
        result = await self.session.execute(
            select(Role).where(Role.code == code)
        )
        return result.scalar_one_or_none()

    async def list_roles(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[Role], int]:
        query = select(Role).options(selectinload(Role.permissions))

        total_result = await self.session.execute(select(func.count(Role.id)))
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, role: Role) -> Role:
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role

    async def update(self, role_id: UUID, **kwargs) -> Optional[Role]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(Role).where(Role.id == role_id).values(**filtered)
            )
        return await self.get_by_id(role_id)

    async def delete(self, role_id: UUID) -> bool:
        role = await self.get_by_id(role_id)
        if role and not role.is_builtin:
            await self.session.delete(role)
            return True
        return False


class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.code == code)
        )
        return result.scalar_one_or_none()

    async def list_permissions(
        self,
        skip: int = 0,
        limit: int = 100,
        resource: Optional[str] = None,
    ) -> tuple[List[Permission], int]:
        query = select(Permission)
        count_query = select(func.count(Permission.id))

        if resource:
            query = query.where(Permission.resource == resource)
            count_query = count_query.where(Permission.resource == resource)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, permission: Permission) -> Permission:
        self.session.add(permission)
        await self.session.flush()
        await self.session.refresh(permission)
        return permission


class SystemConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, config_id: UUID) -> Optional[SystemConfig]:
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Optional[SystemConfig]:
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def list_configs(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[SystemConfig], int]:
        query = select(SystemConfig)

        total_result = await self.session.execute(select(func.count(SystemConfig.id)))
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, config: SystemConfig) -> SystemConfig:
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def update(self, config_id: UUID, **kwargs) -> Optional[SystemConfig]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(SystemConfig).where(SystemConfig.id == config_id).values(**filtered)
            )
        return await self.get_by_id(config_id)

    async def delete(self, config_id: UUID) -> bool:
        config = await self.get_by_id(config_id)
        if config:
            await self.session.delete(config)
            return True
        return False


class NotificationChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, channel_id: UUID) -> Optional[NotificationChannel]:
        result = await self.session.execute(
            select(NotificationChannel).where(NotificationChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def list_channels(
        self, skip: int = 0, limit: int = 100, is_enabled: Optional[bool] = None
    ) -> tuple[List[NotificationChannel], int]:
        query = select(NotificationChannel)
        count_query = select(func.count(NotificationChannel.id))

        if is_enabled is not None:
            query = query.where(NotificationChannel.is_enabled == is_enabled)
            count_query = count_query.where(NotificationChannel.is_enabled == is_enabled)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, channel: NotificationChannel) -> NotificationChannel:
        self.session.add(channel)
        await self.session.flush()
        await self.session.refresh(channel)
        return channel

    async def update(self, channel_id: UUID, **kwargs) -> Optional[NotificationChannel]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(NotificationChannel)
                .where(NotificationChannel.id == channel_id)
                .values(**filtered)
            )
        return await self.get_by_id(channel_id)

    async def delete(self, channel_id: UUID) -> bool:
        channel = await self.get_by_id(channel_id)
        if channel:
            await self.session.delete(channel)
            return True
        return False
