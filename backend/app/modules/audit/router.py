import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.modules.audit.schemas import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStatsResponse,
    NotificationLogListResponse,
    NotificationLogResponse,
    NotificationRetryRequest,
    NotificationSendRequest,
    NotificationStatsResponse,
)
from app.modules.audit.service import AuditLogService, NotificationService
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.modules.system.models import User

router = APIRouter(prefix="/audit", tags=["Audit"])

require_audit_read = PermissionChecker("audit:log", "read")
require_audit_write = PermissionChecker("audit:log", "write")
require_notification_read = PermissionChecker("audit:log", "read")
require_notification_execute = PermissionChecker("audit:notification", "execute")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "module": "audit", "version": settings.app_version}


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_audit_read)],
)
async def list_audit_logs(
    user_id: Optional[UUID] = None,
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: Optional[str] = Query(None, pattern="^(success|failure)$"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    request_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = AuditLogService(db)
    items, total = await service.list_all(
        user_id=user_id, username=username, action=action,
        resource_type=resource_type, resource_id=resource_id,
        status=status, start_time=start_time, end_time=end_time,
        request_id=request_id, skip=skip, limit=limit,
    )
    return AuditLogListResponse(
        items=items, total=total, page=skip // limit + 1, page_size=limit,
    )


@router.get(
    "/logs/stats",
    response_model=AuditLogStatsResponse,
    dependencies=[Depends(require_audit_read)],
)
async def get_audit_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db=Depends(get_db),
):
    service = AuditLogService(db)
    return await service.get_stats(start_time, end_time)


@router.get(
    "/logs/export",
    dependencies=[Depends(require_audit_read)],
)
async def export_audit_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[UUID] = None,
    log_status: Optional[str] = None,
    export_format: str = Query("csv", pattern="^(csv|json)$"),
    db=Depends(get_db),
):
    service = AuditLogService(db)
    items, _ = await service.list_all(
        start_time=start_time, end_time=end_time,
        action=action, resource_type=resource_type,
        user_id=user_id, status=log_status,
        skip=0, limit=10000,
    )

    if export_format == "json":
        data = [
            {
                "id": str(item.id),
                "user_id": str(item.user_id) if item.user_id else None,
                "username": item.username,
                "action": item.action,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "resource_name": item.resource_name,
                "detail": item.detail,
                "ip_address": item.ip_address,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
        output = io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        return StreamingResponse(
            output,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"},
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "username", "action", "resource_type", "resource_id",
            "resource_name", "ip_address", "status", "created_at",
        ])
        for item in items:
            writer.writerow([
                str(item.id),
                item.username or "",
                item.action,
                item.resource_type,
                item.resource_id or "",
                item.resource_name or "",
                item.ip_address or "",
                item.status,
                item.created_at.isoformat() if item.created_at else "",
            ])
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"},
        )


@router.delete(
    "/logs/cleanup",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_audit_write)],
)
async def cleanup_audit_logs(
    retention_days: int = Query(180, ge=1, le=3650),
    db=Depends(get_db),
):
    service = AuditLogService(db)
    deleted = await service.cleanup(retention_days)
    return {"deleted": deleted, "retention_days": retention_days}


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogResponse,
    dependencies=[Depends(require_audit_read)],
)
async def get_audit_log(log_id: UUID, db=Depends(get_db)):
    service = AuditLogService(db)
    return await service.get_by_id(log_id)


@router.post(
    "/notifications/send",
    dependencies=[Depends(require_notification_execute)],
)
async def send_notification(
    data: NotificationSendRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = NotificationService(db)
    results = await service.send_notification(
        channel_ids=data.channel_ids,
        subject=data.subject,
        content=data.content,
        recipients=data.recipients,
        related_alert_id=data.related_alert_id,
    )
    sent_count = sum(1 for r in results if r.status == "sent")
    failed_count = sum(1 for r in results if r.status == "failed")
    return {
        "total": len(results),
        "sent": sent_count,
        "failed": failed_count,
    }


@router.get(
    "/notifications",
    response_model=NotificationLogListResponse,
    dependencies=[Depends(require_notification_read)],
)
async def list_notification_logs(
    channel_id: Optional[UUID] = None,
    channel_type: Optional[str] = Query(None, pattern="^(email|webhook|dingtalk|wecom|lark)$"),
    status: Optional[str] = Query(None, pattern="^(pending|sent|failed|retrying)$"),
    related_alert_id: Optional[UUID] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = NotificationService(db)
    items, total = await service.list_all(
        channel_id=channel_id, channel_type=channel_type,
        status=status, related_alert_id=related_alert_id,
        start_time=start_time, end_time=end_time,
        skip=skip, limit=limit,
    )
    return NotificationLogListResponse(
        items=items, total=total, page=skip // limit + 1, page_size=limit,
    )


@router.get(
    "/notifications/stats",
    response_model=NotificationStatsResponse,
    dependencies=[Depends(require_notification_read)],
)
async def get_notification_stats(db=Depends(get_db)):
    service = NotificationService(db)
    return await service.get_stats()


@router.get(
    "/notifications/{log_id}",
    response_model=NotificationLogResponse,
    dependencies=[Depends(require_notification_read)],
)
async def get_notification_log(log_id: UUID, db=Depends(get_db)):
    service = NotificationService(db)
    from app.core.exceptions import NotFoundException
    log = await service.repo.get_by_id(log_id)
    if not log:
        raise NotFoundException("NotificationLog", str(log_id))
    return log


@router.post(
    "/notifications/retry",
    dependencies=[Depends(require_notification_execute)],
)
async def retry_notifications(
    data: NotificationRetryRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = NotificationService(db)
    count = await service.retry_failed(data.log_ids)
    return {"retried": count}
