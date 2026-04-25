from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.events import EventTypes, publish_event
from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.modules.asset.models import Server
from app.modules.autoops.models import (
    FirmwarePackage,
    TaskDefinition,
    TaskInstance,
    TaskStepLog,
)
from app.modules.autoops.repository import (
    FirmwarePackageRepository,
    TaskDefinitionRepository,
    TaskInstanceRepository,
    TaskStepLogRepository,
)

logger = get_logger(__name__)


class TaskDefinitionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TaskDefinitionRepository(session)

    async def create(self, created_by: UUID, **kwargs) -> TaskDefinition:
        return await self.repo.create(created_by=created_by, **kwargs)

    async def update(self, task_id: UUID, **kwargs) -> TaskDefinition:
        return await self.repo.update(task_id, **kwargs)

    async def delete(self, task_id: UUID) -> bool:
        return await self.repo.delete(task_id)

    async def get_by_id(self, task_id: UUID) -> TaskDefinition:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise NotFoundException("TaskDefinition", str(task_id))
        return task

    async def list_all(self, **kwargs) -> Tuple[List[TaskDefinition], int]:
        return await self.repo.list_all(**kwargs)


class TaskInstanceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TaskInstanceRepository(session)
        self.step_repo = TaskStepLogRepository(session)
        self.def_repo = TaskDefinitionRepository(session)

    async def create_instance(self, created_by: UUID, data: dict) -> TaskInstance:
        task_def = await self.def_repo.get_by_id(data["task_def_id"])
        if not task_def:
            raise NotFoundException("TaskDefinition", str(data["task_def_id"]))
        if not task_def.is_enabled:
            raise ValidationException("Task definition is not enabled")

        initial_status = "pending" if task_def.requires_approval else "approved"

        instance = await self.repo.create(
            task_def_id=data["task_def_id"],
            status=initial_status,
            trigger_type=data.get("trigger_type", "manual"),
            parameters=data.get("parameters"),
            created_by=created_by,
        )

        await publish_event(EventTypes.TASK_CREATED, {
            "instance_id": str(instance.id),
            "task_def_id": str(task_def.id),
            "task_name": task_def.name,
            "task_type": task_def.task_type,
            "requires_approval": task_def.requires_approval,
            "created_by": str(created_by),
        })

        if not task_def.requires_approval:
            await self._start_execution(instance.id, task_def)

        return instance

    async def approve(self, instance_id: UUID, approver_id: UUID, action: str, reason: Optional[str] = None, approver_roles: Optional[list] = None) -> TaskInstance:
        if action not in ("approve", "reject"):
            raise ValidationException(f"Invalid action: {action}. Must be 'approve' or 'reject'")

        instance = await self.repo.get_by_id(instance_id)
        if not instance:
            raise NotFoundException("TaskInstance", str(instance_id))
        if instance.status != "pending":
            raise ValidationException(f"Cannot approve task in status: {instance.status}")

        if instance.created_by and instance.created_by == approver_id:
            raise ValidationException("Cannot approve your own task")

        task_def = await self.def_repo.get_by_id(instance.task_def_id)
        if not task_def:
            raise ValidationException("Task definition not found")

        if task_def.approver_roles:
            if approver_roles is None:
                raise AuthorizationException("Approver roles are required for this task")
            if not any(str(r) in [str(ar) for ar in task_def.approver_roles] for r in approver_roles):
                raise AuthorizationException("You are not authorized to approve this task")

        if action == "approve":
            instance = await self.repo.update(
                instance_id,
                status="approved",
                approved_by=approver_id,
                approved_at=datetime.now(timezone.utc),
            )
            await self._start_execution(instance_id, task_def)
        else:
            instance = await self.repo.update(
                instance_id,
                status="cancelled",
                summary=f"Rejected: {reason or 'No reason provided'}",
            )

        await publish_event(EventTypes.TASK_APPROVED if action == "approve" else EventTypes.TASK_CANCELLED, {
            "instance_id": str(instance_id),
            "action": action,
            "approver_id": str(approver_id),
        })

        return instance

    async def cancel(self, instance_id: UUID, cancelled_by: Optional[UUID] = None) -> TaskInstance:
        instance = await self.repo.get_by_id(instance_id)
        if not instance:
            raise NotFoundException("TaskInstance", str(instance_id))
        if instance.status not in ("pending", "approved", "running"):
            raise ValidationException(f"Cannot cancel task in status: {instance.status}")

        update_data = {"status": "cancelled", "completed_at": datetime.now(timezone.utc)}
        if cancelled_by:
            update_data["summary"] = f"Cancelled by {cancelled_by}"

        instance = await self.repo.update(instance_id, **update_data)
        await publish_event(EventTypes.TASK_CANCELLED, {
            "instance_id": str(instance_id),
            "cancelled_by": str(cancelled_by) if cancelled_by else None,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        })
        return instance

    async def get_by_id(self, instance_id: UUID) -> TaskInstance:
        instance = await self.repo.get_by_id(instance_id)
        if not instance:
            raise NotFoundException("TaskInstance", str(instance_id))
        return instance

    async def list_all(self, **kwargs) -> Tuple[List[TaskInstance], int]:
        return await self.repo.list_all(**kwargs)

    async def get_step_logs(self, instance_id: UUID) -> List[TaskStepLog]:
        return await self.step_repo.list_by_instance(instance_id)

    async def _start_execution(self, instance_id: UUID, task_def: TaskDefinition):
        try:
            target_servers = await self._resolve_targets(task_def.target_filter)
            steps = task_def.steps if isinstance(task_def.steps, list) else []

            if not target_servers or not steps:
                await self.repo.update(
                    instance_id,
                    status="completed",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    summary=f"No {'targets' if not target_servers else 'steps'} to execute",
                )
                return

            await self.repo.update(instance_id, status="running", started_at=datetime.now(timezone.utc))

            for server in target_servers:
                for step_config in steps:
                    await self.step_repo.create(
                        task_instance_id=instance_id,
                        server_id=server.id,
                        step_number=step_config.get("step_number", 0),
                        step_name=step_config.get("step_name", ""),
                        status="pending",
                    )

            await publish_event(EventTypes.TASK_STARTED, {
                "instance_id": str(instance_id),
                "task_name": task_def.name,
                "target_count": len(target_servers),
                "step_count": len(steps),
            })
        except Exception as e:
            logger.error(f"Failed to start execution for instance {instance_id}: {e}")
            await self.repo.update(
                instance_id,
                status="failed",
                summary=f"Failed to start: {str(e)}",
                completed_at=datetime.now(timezone.utc),
            )

    async def _resolve_targets(self, target_filter: Optional[Dict]) -> List[Server]:
        query = select(Server).where(Server.status == "active")
        if target_filter:
            if target_filter.get("brand"):
                query = query.where(Server.brand == target_filter["brand"])
            if target_filter.get("model"):
                query = query.where(Server.model == target_filter["model"])
            if target_filter.get("server_ids"):
                try:
                    valid_uuids = [UUID(sid) for sid in target_filter["server_ids"]]
                except ValueError as e:
                    raise ValidationException(f"Invalid server ID in target_filter: {e}")
                if valid_uuids:
                    query = query.where(Server.id.in_(valid_uuids))
        result = await self.session.execute(query)
        return result.scalars().all()


class FirmwarePackageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FirmwarePackageRepository(session)

    async def create(self, uploaded_by: UUID, data: dict) -> FirmwarePackage:
        minio_bucket = settings.minio_bucket
        minio_key = f"firmware/{data['brand']}/{data['component']}/{data['version']}/{data['filename']}"

        return await self.repo.create(
            uploaded_by=uploaded_by,
            minio_bucket=minio_bucket,
            minio_key=minio_key,
            upload_status="pending",
            **data,
        )

    async def update(self, pkg_id: UUID, **kwargs) -> FirmwarePackage:
        return await self.repo.update(pkg_id, **kwargs)

    async def delete(self, pkg_id: UUID) -> bool:
        return await self.repo.delete(pkg_id)

    async def get_by_id(self, pkg_id: UUID) -> FirmwarePackage:
        pkg = await self.repo.get_by_id(pkg_id)
        if not pkg:
            raise NotFoundException("FirmwarePackage", str(pkg_id))
        return pkg

    async def list_all(self, **kwargs) -> Tuple[List[FirmwarePackage], int]:
        return await self.repo.list_all(**kwargs)
