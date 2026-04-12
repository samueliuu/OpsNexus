import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.modules.audit.models import AuditLog, NotificationLog

logger = get_logger(__name__)


class AuditLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> AuditLog:
        log = AuditLog(id=uuid.uuid4(), **kwargs)
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        user_id: Optional[UUID] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        request_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        if username:
            u = _escape_like(username)
            query = query.where(AuditLog.username.ilike(f"%{u}%", escape="\\"))
            count_query = count_query.where(AuditLog.username.ilike(f"%{u}%", escape="\\"))
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
            count_query = count_query.where(AuditLog.resource_id == resource_id)
        if status:
            query = query.where(AuditLog.status == status)
            count_query = count_query.where(AuditLog.status == status)
        if start_time:
            query = query.where(AuditLog.created_at >= start_time)
            count_query = count_query.where(AuditLog.created_at >= start_time)
        if end_time:
            query = query.where(AuditLog.created_at <= end_time)
            count_query = count_query.where(AuditLog.created_at <= end_time)
        if request_id:
            query = query.where(AuditLog.request_id == request_id)
            count_query = count_query.where(AuditLog.request_id == request_id)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def get_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        base_filter = True
        if start_time:
            base_filter = and_(base_filter, AuditLog.created_at >= start_time)
        if end_time:
            base_filter = and_(base_filter, AuditLog.created_at <= end_time)

        total_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(base_filter)
        )
        total = total_result.scalar() or 0

        by_action_result = await self.session.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(base_filter)
            .group_by(AuditLog.action)
            .order_by(desc(func.count(AuditLog.id)))
            .limit(20)
        )
        by_action = {row[0]: row[1] for row in by_action_result.all()}

        by_resource_result = await self.session.execute(
            select(AuditLog.resource_type, func.count(AuditLog.id))
            .where(base_filter)
            .group_by(AuditLog.resource_type)
            .order_by(desc(func.count(AuditLog.id)))
        )
        by_resource_type = {row[0]: row[1] for row in by_resource_result.all()}

        by_status_result = await self.session.execute(
            select(AuditLog.status, func.count(AuditLog.id))
            .where(base_filter)
            .group_by(AuditLog.status)
        )
        by_status = {row[0]: row[1] for row in by_status_result.all()}

        by_user_result = await self.session.execute(
            select(AuditLog.username, func.count(AuditLog.id))
            .where(base_filter, AuditLog.username.isnot(None))
            .group_by(AuditLog.username)
            .order_by(desc(func.count(AuditLog.id)))
            .limit(20)
        )
        by_user = {row[0] or "anonymous": row[1] for row in by_user_result.all()}

        recent_failures_result = await self.session.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.status == "failure",
                AuditLog.created_at >= datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
            )
        )
        recent_failures = recent_failures_result.scalar() or 0

        return {
            "total": total,
            "by_action": by_action,
            "by_resource_type": by_resource_type,
            "by_status": by_status,
            "by_user": by_user,
            "recent_failures": recent_failures,
        }

    async def delete_before(self, before_time: datetime) -> int:
        result = await self.session.execute(
            delete(AuditLog).where(AuditLog.created_at < before_time)
        )
        await self.session.flush()
        return result.rowcount


class NotificationLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> NotificationLog:
        log = NotificationLog(id=uuid.uuid4(), **kwargs)
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_by_id(self, log_id: UUID) -> Optional[NotificationLog]:
        result = await self.session.execute(
            select(NotificationLog).where(NotificationLog.id == log_id)
            .options(selectinload(NotificationLog.channel))
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        channel_id: Optional[UUID] = None,
        channel_type: Optional[str] = None,
        status: Optional[str] = None,
        related_alert_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[NotificationLog], int]:
        query = select(NotificationLog)
        count_query = select(func.count(NotificationLog.id))

        if channel_id:
            query = query.where(NotificationLog.channel_id == channel_id)
            count_query = count_query.where(NotificationLog.channel_id == channel_id)
        if channel_type:
            query = query.where(NotificationLog.channel_type == channel_type)
            count_query = count_query.where(NotificationLog.channel_type == channel_type)
        if status:
            query = query.where(NotificationLog.status == status)
            count_query = count_query.where(NotificationLog.status == status)
        if related_alert_id:
            query = query.where(NotificationLog.related_alert_id == related_alert_id)
            count_query = count_query.where(NotificationLog.related_alert_id == related_alert_id)
        if start_time:
            query = query.where(NotificationLog.created_at >= start_time)
            count_query = count_query.where(NotificationLog.created_at >= start_time)
        if end_time:
            query = query.where(NotificationLog.created_at <= end_time)
            count_query = count_query.where(NotificationLog.created_at <= end_time)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(NotificationLog.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def update(self, log_id: UUID, **kwargs) -> NotificationLog:
        log = await self.get_by_id(log_id)
        if not log:
            raise NotFoundException("NotificationLog", str(log_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(log, key, value)
        await self.session.flush()
        return await self.get_by_id(log_id)

    async def get_failed_for_retry(self, max_retries: int = 3) -> List[NotificationLog]:
        result = await self.session.execute(
            select(NotificationLog).where(
                NotificationLog.status == "failed",
                NotificationLog.retry_count < max_retries,
            ).order_by(NotificationLog.created_at)
        )
        return result.scalars().all()

    async def get_stats(self) -> Dict[str, Any]:
        total_result = await self.session.execute(
            select(func.count(NotificationLog.id))
        )
        total = total_result.scalar() or 0

        by_status_result = await self.session.execute(
            select(NotificationLog.status, func.count(NotificationLog.id))
            .group_by(NotificationLog.status)
        )
        by_status = {row[0]: row[1] for row in by_status_result.all()}

        by_channel_result = await self.session.execute(
            select(NotificationLog.channel_type, func.count(NotificationLog.id))
            .group_by(NotificationLog.channel_type)
        )
        by_channel_type = {row[0]: row[1] for row in by_channel_result.all()}

        recent_failed_result = await self.session.execute(
            select(func.count(NotificationLog.id)).where(
                NotificationLog.status == "failed",
                NotificationLog.created_at >= datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),
            )
        )
        recent_failed = recent_failed_result.scalar() or 0

        return {
            "total": total,
            "by_status": by_status,
            "by_channel_type": by_channel_type,
            "recent_failed": recent_failed,
        }
