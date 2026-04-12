from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.monitor.schemas import (
    AlertAcknowledgeRequest,
    AlertEventListResponse,
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
    AlertStatsResponse,
    AlertSuppressRequest,
    DashboardMetricsResponse,
    MetricCollectionResult,
    MetricCollectionTask,
    MetricDataBatchWrite,
    MetricDataPoint,
    MetricDataQuery,
    MetricDataResponse,
    MetricDataWrite,
    MetricDefinitionCreate,
    MetricDefinitionListResponse,
    MetricDefinitionResponse,
    MetricDefinitionUpdate,
)
from app.modules.monitor.service import (
    AlertEvaluationService,
    AlertEventService,
    AlertRuleService,
    MetricCollectionService,
    MetricDataService,
    MetricDefinitionService,
)
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.modules.system.models import User

router = APIRouter(prefix="/monitor", tags=["Monitor"])

require_metric_read = PermissionChecker("monitor:metric", "read")
require_metric_write = PermissionChecker("monitor:metric", "write")
require_alert_read = PermissionChecker("monitor:alert", "read")
require_alert_write = PermissionChecker("monitor:alert", "write")
require_alert_execute = PermissionChecker("monitor:alert", "execute")
require_collection_execute = PermissionChecker("monitor:collect", "execute")


@router.get("/health")
async def health_check():
    return {"status": "healthy", "module": "monitor", "version": settings.app_version}


@router.get(
    "/dashboard",
    response_model=DashboardMetricsResponse,
    dependencies=[Depends(require_metric_read)],
)
async def get_dashboard_metrics(db=Depends(get_db)):
    service = MetricDataService(db)
    return await service.get_dashboard_metrics()


@router.post(
    "/definitions",
    response_model=MetricDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_metric_write)],
)
async def create_metric_definition(data: MetricDefinitionCreate, db=Depends(get_db)):
    service = MetricDefinitionService(db)
    metric = await service.create(**data.model_dump())
    return metric


@router.get(
    "/definitions",
    response_model=MetricDefinitionListResponse,
    dependencies=[Depends(require_metric_read)],
)
async def list_metric_definitions(
    metric_type: Optional[str] = Query(None, pattern="^(gauge|counter|histogram)$"),
    collection_method: Optional[str] = Query(None, pattern="^(bmc|snmp|agent)$"),
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = MetricDefinitionService(db)
    items, total = await service.list_all(
        metric_type=metric_type,
        collection_method=collection_method,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    return MetricDefinitionListResponse(
        items=items, total=total, page=skip // limit + 1, page_size=limit,
    )


@router.get(
    "/definitions/{metric_id}",
    response_model=MetricDefinitionResponse,
    dependencies=[Depends(require_metric_read)],
)
async def get_metric_definition(metric_id: UUID, db=Depends(get_db)):
    service = MetricDefinitionService(db)
    return await service.get_by_id(metric_id)


@router.put(
    "/definitions/{metric_id}",
    response_model=MetricDefinitionResponse,
    dependencies=[Depends(require_metric_write)],
)
async def update_metric_definition(
    metric_id: UUID, data: MetricDefinitionUpdate, db=Depends(get_db),
):
    service = MetricDefinitionService(db)
    return await service.update(metric_id, **data.model_dump(exclude_unset=True))


@router.delete(
    "/definitions/{metric_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_metric_write)],
)
async def delete_metric_definition(metric_id: UUID, db=Depends(get_db)):
    service = MetricDefinitionService(db)
    await service.delete(metric_id)
    return None


@router.post(
    "/data",
    dependencies=[Depends(require_metric_write)],
)
async def write_metric_data(data: MetricDataWrite, db=Depends(get_db)):
    service = MetricDataService(db)
    metric = await service.write_metric(
        server_id=data.server_id,
        metric_name=data.metric_name,
        value=data.value,
        labels=data.labels,
        timestamp=data.timestamp,
    )
    return {"status": "ok", "time": metric.time.isoformat()}


@router.post(
    "/data/batch",
    dependencies=[Depends(require_metric_write)],
)
async def write_metric_data_batch(data: MetricDataBatchWrite, db=Depends(get_db)):
    service = MetricDataService(db)
    metrics = [m.model_dump() for m in data.metrics]
    count = await service.write_batch(metrics)
    return {"status": "ok", "written": count}


@router.post(
    "/data/query",
    response_model=MetricDataResponse,
    dependencies=[Depends(require_metric_read)],
)
async def query_metric_data(data: MetricDataQuery, db=Depends(get_db)):
    service = MetricDataService(db)
    data_points = await service.query_range(
        metric_name=data.metric_name,
        server_ids=data.server_ids,
        start_time=data.start_time,
        end_time=data.end_time,
        labels=data.labels,
        step=data.step,
        aggregation=data.aggregation,
    )
    return MetricDataResponse(
        metric_name=data.metric_name,
        data_points=[
            MetricDataPoint(
                time=dp.time, server_id=dp.server_id, value=dp.value, labels=dp.labels,
            )
            for dp in data_points
        ],
        total_points=len(data_points),
    )


@router.get(
    "/data/latest/{metric_name}/{server_id}",
    dependencies=[Depends(require_metric_read)],
)
async def get_latest_metric(metric_name: str, server_id: UUID, db=Depends(get_db)):
    service = MetricDataService(db)
    latest = await service.get_latest(metric_name, server_id)
    if not latest:
        return {"metric_name": metric_name, "server_id": str(server_id), "value": None}
    return {
        "metric_name": latest.metric_name,
        "server_id": str(latest.server_id),
        "value": latest.value,
        "time": latest.time.isoformat(),
        "labels": latest.labels,
    }


@router.post(
    "/collect",
    response_model=MetricCollectionResult,
    dependencies=[Depends(require_collection_execute)],
)
async def collect_metrics(
    data: MetricCollectionTask,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = MetricCollectionService(db)
    return await service.collect_batch(
        server_ids=data.server_ids,
        metric_names=data.metric_names,
        force=data.force,
    )


@router.post(
    "/evaluate",
    dependencies=[Depends(require_collection_execute)],
)
async def evaluate_alerts(
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = AlertEvaluationService(db)
    result = await service.evaluate_all()
    return result


@router.post(
    "/rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_alert_write)],
)
async def create_alert_rule(
    data: AlertRuleCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = AlertRuleService(db)
    rule = await service.create(created_by=current_user.id, **data.model_dump())
    return rule


@router.get(
    "/rules",
    response_model=AlertRuleListResponse,
    dependencies=[Depends(require_alert_read)],
)
async def list_alert_rules(
    metric_name: Optional[str] = None,
    severity: Optional[str] = Query(None, pattern="^(critical|warning|info)$"),
    is_enabled: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = AlertRuleService(db)
    items, total = await service.list_all(
        metric_name=metric_name, severity=severity,
        is_enabled=is_enabled, skip=skip, limit=limit,
    )
    return AlertRuleListResponse(
        items=items, total=total, page=skip // limit + 1, page_size=limit,
    )


@router.get(
    "/rules/{rule_id}",
    response_model=AlertRuleResponse,
    dependencies=[Depends(require_alert_read)],
)
async def get_alert_rule(rule_id: UUID, db=Depends(get_db)):
    service = AlertRuleService(db)
    return await service.get_by_id(rule_id)


@router.put(
    "/rules/{rule_id}",
    response_model=AlertRuleResponse,
    dependencies=[Depends(require_alert_write)],
)
async def update_alert_rule(rule_id: UUID, data: AlertRuleUpdate, db=Depends(get_db)):
    service = AlertRuleService(db)
    return await service.update(rule_id, **data.model_dump(exclude_unset=True))


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_alert_write)],
)
async def delete_alert_rule(rule_id: UUID, db=Depends(get_db)):
    service = AlertRuleService(db)
    await service.delete(rule_id)
    return None


@router.get(
    "/events",
    response_model=AlertEventListResponse,
    dependencies=[Depends(require_alert_read)],
)
async def list_alert_events(
    rule_id: Optional[UUID] = None,
    server_id: Optional[UUID] = None,
    severity: Optional[str] = Query(None, pattern="^(critical|warning|info)$"),
    status: Optional[str] = Query(None, pattern="^(firing|acknowledged|resolved|suppressed)$"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db=Depends(get_db),
):
    service = AlertEventService(db)
    items, total = await service.list_all(
        rule_id=rule_id, server_id=server_id, severity=severity,
        status=status, start_time=start_time, end_time=end_time,
        skip=skip, limit=limit,
    )
    return AlertEventListResponse(
        items=items, total=total, page=skip // limit + 1, page_size=limit,
    )


@router.get(
    "/events/stats",
    response_model=AlertStatsResponse,
    dependencies=[Depends(require_alert_read)],
)
async def get_alert_stats(db=Depends(get_db)):
    service = AlertEventService(db)
    return await service.get_stats()


@router.get(
    "/events/{event_id}",
    response_model=AlertEventResponse,
    dependencies=[Depends(require_alert_read)],
)
async def get_alert_event(event_id: UUID, db=Depends(get_db)):
    service = AlertEventService(db)
    return await service.get_by_id(event_id)


@router.post(
    "/events/acknowledge",
    dependencies=[Depends(require_alert_execute)],
)
async def acknowledge_alerts(
    data: AlertAcknowledgeRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = AlertEventService(db)
    count = await service.acknowledge(data.event_ids, current_user.id)
    return {"acknowledged": count}


@router.post(
    "/events/suppress",
    dependencies=[Depends(require_alert_execute)],
)
async def suppress_alerts(
    data: AlertSuppressRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = AlertEventService(db)
    count = await service.suppress(data.event_ids, data.reason)
    return {"suppressed": count}


@router.delete(
    "/data/cleanup",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_metric_write)],
)
async def cleanup_old_metric_data(
    retention_days: int = Query(90, ge=1, le=3650),
    db=Depends(get_db),
):
    service = MetricDataService(db)
    deleted = await service.cleanup_old_data(retention_days)
    return {"deleted": deleted, "retention_days": retention_days}
