from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.autoops.schemas import (
    FirmwarePackageCreate,
    FirmwarePackageListResponse,
    FirmwarePackageResponse,
    TaskApprovalRequest,
    TaskDefinitionCreate,
    TaskDefinitionListResponse,
    TaskDefinitionResponse,
    TaskDefinitionUpdate,
    TaskInstanceCreate,
    TaskInstanceListResponse,
    TaskInstanceResponse,
    TaskStepLogResponse,
)
from app.modules.autoops.service import (
    FirmwarePackageService,
    TaskDefinitionService,
    TaskInstanceService,
)
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.modules.system.models import User

router = APIRouter(prefix="/autoops", tags=["AutoOps"])

require_task_read = PermissionChecker("autoops:task", "read")
require_task_write = PermissionChecker("autoops:task", "write")
require_task_execute = PermissionChecker("autoops:task", "execute")
require_task_approve = PermissionChecker("autoops:task", "approve")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "module": "autoops", "version": settings.app_version}


@router.post(
    "/tasks",
    response_model=TaskDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_task_write)],
)
async def create_task_definition(
    data: TaskDefinitionCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = TaskDefinitionService(db)
    return await service.create(
        created_by=current_user.id,
        name=data.name,
        description=data.description,
        task_type=data.task_type,
        target_filter=data.target_filter,
        steps=[s.model_dump() for s in data.steps],
        parameters=data.parameters,
        schedule=data.schedule,
        is_scheduled=data.is_scheduled,
        requires_approval=data.requires_approval,
        approver_roles=data.approver_roles,
        retry_policy=data.retry_policy,
        timeout_seconds=data.timeout_seconds,
        is_enabled=data.is_enabled,
    )


@router.get(
    "/tasks",
    response_model=TaskDefinitionListResponse,
    dependencies=[Depends(require_task_read)],
)
async def list_task_definitions(
    task_type: Optional[str] = Query(None, pattern="^(firmware_upgrade|inspection|config_deploy|custom)$"),
    is_enabled: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = TaskDefinitionService(db)
    items, total = await service.list_all(task_type=task_type, is_enabled=is_enabled, skip=skip, limit=limit)
    return TaskDefinitionListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDefinitionResponse,
    dependencies=[Depends(require_task_read)],
)
async def get_task_definition(task_id: UUID, db=Depends(get_db)):
    service = TaskDefinitionService(db)
    return await service.get_by_id(task_id)


@router.put(
    "/tasks/{task_id}",
    response_model=TaskDefinitionResponse,
    dependencies=[Depends(require_task_write)],
)
async def update_task_definition(task_id: UUID, data: TaskDefinitionUpdate, db=Depends(get_db)):
    service = TaskDefinitionService(db)
    update_data = data.model_dump(exclude_unset=True)
    if "steps" in update_data and update_data["steps"]:
        update_data["steps"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in update_data["steps"]]
    return await service.update(task_id, **update_data)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_task_write)],
)
async def delete_task_definition(task_id: UUID, db=Depends(get_db)):
    service = TaskDefinitionService(db)
    await service.delete(task_id)
    return None


@router.post(
    "/instances",
    response_model=TaskInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_task_execute)],
)
async def create_task_instance(
    data: TaskInstanceCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = TaskInstanceService(db)
    return await service.create_instance(
        created_by=current_user.id,
        data=data.model_dump(),
    )


@router.get(
    "/instances",
    response_model=TaskInstanceListResponse,
    dependencies=[Depends(require_task_read)],
)
async def list_task_instances(
    task_def_id: Optional[UUID] = None,
    status: Optional[str] = Query(None, pattern="^(pending|approved|running|paused|completed|failed|cancelled)$"),
    trigger_type: Optional[str] = Query(None, pattern="^(manual|scheduled|api)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = TaskInstanceService(db)
    items, total = await service.list_all(
        task_def_id=task_def_id, status=status, trigger_type=trigger_type,
        skip=skip, limit=limit,
    )
    return TaskInstanceListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get(
    "/instances/{instance_id}",
    response_model=TaskInstanceResponse,
    dependencies=[Depends(require_task_read)],
)
async def get_task_instance(instance_id: UUID, db=Depends(get_db)):
    service = TaskInstanceService(db)
    return await service.get_by_id(instance_id)


@router.post(
    "/instances/{instance_id}/approve",
    response_model=TaskInstanceResponse,
    dependencies=[Depends(require_task_approve)],
)
async def approve_task_instance(
    instance_id: UUID,
    data: TaskApprovalRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = TaskInstanceService(db)
    approver_roles = [str(r.id) for r in current_user.roles] if current_user.roles else []
    return await service.approve(instance_id, current_user.id, data.action, data.reason, approver_roles=approver_roles)


@router.post(
    "/instances/{instance_id}/cancel",
    response_model=TaskInstanceResponse,
    dependencies=[Depends(require_task_execute)],
)
async def cancel_task_instance(
    instance_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = TaskInstanceService(db)
    return await service.cancel(instance_id, cancelled_by=current_user.id)


@router.get(
    "/instances/{instance_id}/steps",
    response_model=list[TaskStepLogResponse],
    dependencies=[Depends(require_task_read)],
)
async def get_task_step_logs(instance_id: UUID, db=Depends(get_db)):
    service = TaskInstanceService(db)
    return await service.get_step_logs(instance_id)


@router.post(
    "/firmware",
    response_model=FirmwarePackageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_task_write)],
)
async def create_firmware_package(
    data: FirmwarePackageCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = FirmwarePackageService(db)
    return await service.create(
        uploaded_by=current_user.id,
        data=data.model_dump(),
    )


@router.get(
    "/firmware",
    response_model=FirmwarePackageListResponse,
    dependencies=[Depends(require_task_read)],
)
async def list_firmware_packages(
    brand: Optional[str] = None,
    component: Optional[str] = None,
    upload_status: Optional[str] = Query(None, pattern="^(pending|uploading|completed|verified|failed)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = FirmwarePackageService(db)
    items, total = await service.list_all(
        brand=brand, component=component, upload_status=upload_status,
        skip=skip, limit=limit,
    )
    return FirmwarePackageListResponse(items=items, total=total, page=skip // limit + 1, page_size=limit)


@router.get(
    "/firmware/{pkg_id}",
    response_model=FirmwarePackageResponse,
    dependencies=[Depends(require_task_read)],
)
async def get_firmware_package(pkg_id: UUID, db=Depends(get_db)):
    service = FirmwarePackageService(db)
    return await service.get_by_id(pkg_id)


@router.delete(
    "/firmware/{pkg_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_task_write)],
)
async def delete_firmware_package(pkg_id: UUID, db=Depends(get_db)):
    service = FirmwarePackageService(db)
    await service.delete(pkg_id)
    return None
