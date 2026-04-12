import uuid
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.modules.autoops.models import (
    FirmwarePackage,
    InspectionPolicy,
    TaskDefinition,
    TaskInstance,
    TaskStepLog,
)

logger = get_logger(__name__)


class TaskDefinitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, task_id: UUID) -> Optional[TaskDefinition]:
        result = await self.session.execute(
            select(TaskDefinition).where(TaskDefinition.id == task_id)
            .options(selectinload(TaskDefinition.task_instances))
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        task_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[TaskDefinition], int]:
        query = select(TaskDefinition).order_by(desc(TaskDefinition.created_at))
        count_query = select(func.count(TaskDefinition.id))

        if task_type:
            query = query.where(TaskDefinition.task_type == task_type)
            count_query = count_query.where(TaskDefinition.task_type == task_type)
        if is_enabled is not None:
            query = query.where(TaskDefinition.is_enabled == is_enabled)
            count_query = count_query.where(TaskDefinition.is_enabled == is_enabled)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(TaskDefinition.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def create(self, **kwargs) -> TaskDefinition:
        task = TaskDefinition(id=uuid.uuid4(), **kwargs)
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update(self, task_id: UUID, **kwargs) -> TaskDefinition:
        task = await self.get_by_id(task_id)
        if not task:
            raise NotFoundException("TaskDefinition", str(task_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(task, key, value)
        await self.session.flush()
        return await self.get_by_id(task_id)

    async def delete(self, task_id: UUID) -> bool:
        task = await self.get_by_id(task_id)
        if not task:
            raise NotFoundException("TaskDefinition", str(task_id))
        await self.session.delete(task)
        await self.session.flush()
        return True


class TaskInstanceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, instance_id: UUID) -> Optional[TaskInstance]:
        result = await self.session.execute(
            select(TaskInstance).where(TaskInstance.id == instance_id)
            .options(selectinload(TaskInstance.task_definition), selectinload(TaskInstance.step_logs))
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        task_def_id: Optional[UUID] = None,
        status: Optional[str] = None,
        trigger_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[TaskInstance], int]:
        query = select(TaskInstance).options(selectinload(TaskInstance.task_definition))
        count_query = select(func.count(TaskInstance.id))

        if task_def_id:
            query = query.where(TaskInstance.task_def_id == task_def_id)
            count_query = count_query.where(TaskInstance.task_def_id == task_def_id)
        if status:
            query = query.where(TaskInstance.status == status)
            count_query = count_query.where(TaskInstance.status == status)
        if trigger_type:
            query = query.where(TaskInstance.trigger_type == trigger_type)
            count_query = count_query.where(TaskInstance.trigger_type == trigger_type)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(TaskInstance.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def create(self, **kwargs) -> TaskInstance:
        instance = TaskInstance(id=uuid.uuid4(), **kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance_id: UUID, **kwargs) -> TaskInstance:
        instance = await self.get_by_id(instance_id)
        if not instance:
            raise NotFoundException("TaskInstance", str(instance_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(instance, key, value)
        await self.session.flush()
        return await self.get_by_id(instance_id)


class TaskStepLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_instance(self, instance_id: UUID) -> List[TaskStepLog]:
        result = await self.session.execute(
            select(TaskStepLog)
            .where(TaskStepLog.task_instance_id == instance_id)
            .options(selectinload(TaskStepLog.server))
            .order_by(TaskStepLog.step_number, TaskStepLog.created_at)
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> TaskStepLog:
        log = TaskStepLog(id=uuid.uuid4(), **kwargs)
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def update(self, log_id: UUID, **kwargs) -> TaskStepLog:
        result = await self.session.execute(
            select(TaskStepLog).where(TaskStepLog.id == log_id)
            .options(selectinload(TaskStepLog.server))
        )
        log = result.scalar_one_or_none()
        if not log:
            raise NotFoundException("TaskStepLog", str(log_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(log, key, value)
        await self.session.flush()
        result = await self.session.execute(
            select(TaskStepLog).where(TaskStepLog.id == log_id)
            .options(selectinload(TaskStepLog.server))
        )
        return result.scalar_one()


class FirmwarePackageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, pkg_id: UUID) -> Optional[FirmwarePackage]:
        result = await self.session.execute(
            select(FirmwarePackage).where(FirmwarePackage.id == pkg_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        brand: Optional[str] = None,
        component: Optional[str] = None,
        upload_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[FirmwarePackage], int]:
        query = select(FirmwarePackage)
        count_query = select(func.count(FirmwarePackage.id))

        if brand:
            query = query.where(FirmwarePackage.brand == brand)
            count_query = count_query.where(FirmwarePackage.brand == brand)
        if component:
            query = query.where(FirmwarePackage.component == component)
            count_query = count_query.where(FirmwarePackage.component == component)
        if upload_status:
            query = query.where(FirmwarePackage.upload_status == upload_status)
            count_query = count_query.where(FirmwarePackage.upload_status == upload_status)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(FirmwarePackage.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def create(self, **kwargs) -> FirmwarePackage:
        pkg = FirmwarePackage(id=uuid.uuid4(), **kwargs)
        self.session.add(pkg)
        await self.session.flush()
        await self.session.refresh(pkg)
        return pkg

    async def update(self, pkg_id: UUID, **kwargs) -> FirmwarePackage:
        pkg = await self.get_by_id(pkg_id)
        if not pkg:
            raise NotFoundException("FirmwarePackage", str(pkg_id))
        for key, value in kwargs.items():
            if value is not None:
                setattr(pkg, key, value)
        await self.session.flush()
        await self.session.refresh(pkg)
        return pkg

    async def delete(self, pkg_id: UUID) -> bool:
        pkg = await self.get_by_id(pkg_id)
        if not pkg:
            raise NotFoundException("FirmwarePackage", str(pkg_id))
        await self.session.delete(pkg)
        await self.session.flush()
        return True
