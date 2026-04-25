import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException
from app.core.logging import get_logger
from app.modules.monitor.models import AlertEvent, AlertRule, MetricData, MetricDefinition

logger = get_logger(__name__)


class MetricDefinitionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, metric_id: UUID) -> Optional[MetricDefinition]:
        result = await self.session.execute(
            select(MetricDefinition).where(MetricDefinition.id == metric_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[MetricDefinition]:
        result = await self.session.execute(
            select(MetricDefinition).where(MetricDefinition.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        metric_type: Optional[str] = None,
        collection_method: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[MetricDefinition], int]:
        query = select(MetricDefinition)
        count_query = select(func.count(MetricDefinition.id))

        if metric_type:
            query = query.where(MetricDefinition.metric_type == metric_type)
            count_query = count_query.where(MetricDefinition.metric_type == metric_type)
        if collection_method:
            query = query.where(MetricDefinition.collection_method == collection_method)
            count_query = count_query.where(MetricDefinition.collection_method == collection_method)
        if is_active is not None:
            query = query.where(MetricDefinition.is_active == is_active)
            count_query = count_query.where(MetricDefinition.is_active == is_active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(MetricDefinition.name).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def list_active_by_method(self, collection_method: str) -> List[MetricDefinition]:
        result = await self.session.execute(
            select(MetricDefinition).where(
                MetricDefinition.is_active.is_(True),
                MetricDefinition.collection_method == collection_method,
            ).order_by(MetricDefinition.name)
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> MetricDefinition:
        existing = await self.get_by_name(kwargs["name"])
        if existing:
            raise ConflictException(f"MetricDefinition name={kwargs['name']} already exists")

        metric = MetricDefinition(id=uuid.uuid4(), **kwargs)
        self.session.add(metric)
        await self.session.flush()
        await self.session.refresh(metric)
        return metric

    async def update(self, metric_id: UUID, **kwargs) -> MetricDefinition:
        metric = await self.get_by_id(metric_id)
        if not metric:
            raise NotFoundException("MetricDefinition", str(metric_id))

        for key, value in kwargs.items():
            if value is not None:
                setattr(metric, key, value)

        await self.session.flush()
        return await self.get_by_id(metric_id)

    async def delete(self, metric_id: UUID) -> bool:
        metric = await self.get_by_id(metric_id)
        if not metric:
            raise NotFoundException("MetricDefinition", str(metric_id))

        await self.session.delete(metric)
        await self.session.flush()
        return True


class MetricDataRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write(self, server_id: UUID, metric_name: str, value: float,
                    labels: Optional[Dict] = None, timestamp: Optional[datetime] = None) -> MetricData:
        data = MetricData(
            time=timestamp or datetime.now(timezone.utc),
            server_id=server_id,
            metric_name=metric_name,
            value=value,
            labels=labels,
        )
        self.session.add(data)
        await self.session.flush()
        return data

    async def write_batch(self, metrics: List[Dict[str, Any]]) -> int:
        objects = []
        for m in metrics:
            objects.append(MetricData(
                time=m.get("timestamp") or datetime.now(timezone.utc),
                server_id=m["server_id"],
                metric_name=m["metric_name"],
                value=m["value"],
                labels=m.get("labels"),
            ))
        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def query_range(
        self,
        metric_name: str,
        server_ids: Optional[List[UUID]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None,
        step: Optional[int] = None,
        aggregation: Optional[str] = None,
        skip: int = 0,
        limit: int = 10000,
    ) -> List[MetricData]:
        query = select(MetricData).where(MetricData.metric_name == metric_name)

        if server_ids:
            query = query.where(MetricData.server_id.in_(server_ids))
        if start_time:
            query = query.where(MetricData.time >= start_time)
        if end_time:
            query = query.where(MetricData.time <= end_time)
        if labels:
            query = query.where(MetricData.labels.contains(labels))

        query = query.order_by(MetricData.time.asc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest(
        self,
        metric_name: str,
        server_id: UUID,
    ) -> Optional[MetricData]:
        result = await self.session.execute(
            select(MetricData)
            .where(MetricData.metric_name == metric_name, MetricData.server_id == server_id)
            .order_by(desc(MetricData.time))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_servers(
        self,
        metric_names: List[str],
        server_ids: List[UUID],
    ) -> Dict[str, Dict[UUID, float]]:
        result_map: Dict[str, Dict[UUID, float]] = {name: {} for name in metric_names}

        if not server_ids or not metric_names:
            return result_map

        subq = (
            select(
                MetricData.metric_name,
                MetricData.server_id,
                MetricData.value,
                func.row_number()
                .over(
                    partition_by=[MetricData.metric_name, MetricData.server_id],
                    order_by=MetricData.time.desc(),
                )
                .label("rn"),
            )
            .where(
                MetricData.metric_name.in_(metric_names),
                MetricData.server_id.in_(server_ids),
            )
            .subquery()
        )

        stmt = select(subq.c.metric_name, subq.c.server_id, subq.c.value).where(
            subq.c.rn == 1
        )
        rows = await self.session.execute(stmt)

        for row in rows.all():
            metric_name, server_id, value = row[0], row[1], row[2]
            if metric_name in result_map and value is not None:
                result_map[metric_name][server_id] = value

        return result_map

    async def delete_before(self, before_time: datetime) -> int:
        result = await self.session.execute(
            delete(MetricData).where(MetricData.time < before_time)
        )
        await self.session.flush()
        return result.rowcount


class AlertRuleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, rule_id: UUID) -> Optional[AlertRule]:
        result = await self.session.execute(
            select(AlertRule).where(AlertRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        metric_name: Optional[str] = None,
        severity: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[AlertRule], int]:
        query = select(AlertRule)
        count_query = select(func.count(AlertRule.id))

        if metric_name:
            query = query.where(AlertRule.metric_name == metric_name)
            count_query = count_query.where(AlertRule.metric_name == metric_name)
        if severity:
            query = query.where(AlertRule.severity == severity)
            count_query = count_query.where(AlertRule.severity == severity)
        if is_enabled is not None:
            query = query.where(AlertRule.is_enabled == is_enabled)
            count_query = count_query.where(AlertRule.is_enabled == is_enabled)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(AlertRule.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def list_enabled(self) -> List[AlertRule]:
        result = await self.session.execute(
            select(AlertRule).where(AlertRule.is_enabled.is_(True))
            .order_by(AlertRule.name)
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> AlertRule:
        rule = AlertRule(id=uuid.uuid4(), **kwargs)
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def update(self, rule_id: UUID, **kwargs) -> AlertRule:
        rule = await self.get_by_id(rule_id)
        if not rule:
            raise NotFoundException("AlertRule", str(rule_id))

        for key, value in kwargs.items():
            if value is not None:
                setattr(rule, key, value)

        await self.session.flush()
        return await self.get_by_id(rule_id)

    async def delete(self, rule_id: UUID) -> bool:
        rule = await self.get_by_id(rule_id)
        if not rule:
            raise NotFoundException("AlertRule", str(rule_id))

        await self.session.delete(rule)
        await self.session.flush()
        return True


class AlertEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, event_id: UUID) -> Optional[AlertEvent]:
        result = await self.session.execute(
            select(AlertEvent).where(AlertEvent.id == event_id)
            .options(selectinload(AlertEvent.rule), selectinload(AlertEvent.server))
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        rule_id: Optional[UUID] = None,
        server_id: Optional[UUID] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[AlertEvent], int]:
        query = select(AlertEvent).options(
            selectinload(AlertEvent.rule), selectinload(AlertEvent.server)
        )
        count_query = select(func.count(AlertEvent.id))

        if rule_id:
            query = query.where(AlertEvent.rule_id == rule_id)
            count_query = count_query.where(AlertEvent.rule_id == rule_id)
        if server_id:
            query = query.where(AlertEvent.server_id == server_id)
            count_query = count_query.where(AlertEvent.server_id == server_id)
        if severity:
            query = query.where(AlertEvent.severity == severity)
            count_query = count_query.where(AlertEvent.severity == severity)
        if status:
            query = query.where(AlertEvent.status == status)
            count_query = count_query.where(AlertEvent.status == status)
        if start_time:
            query = query.where(AlertEvent.triggered_at >= start_time)
            count_query = count_query.where(AlertEvent.triggered_at >= start_time)
        if end_time:
            query = query.where(AlertEvent.triggered_at <= end_time)
            count_query = count_query.where(AlertEvent.triggered_at <= end_time)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(
            query.order_by(desc(AlertEvent.triggered_at)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def find_firing(self, rule_id: UUID, server_id: UUID) -> Optional[AlertEvent]:
        result = await self.session.execute(
            select(AlertEvent).where(
                AlertEvent.rule_id == rule_id,
                AlertEvent.server_id == server_id,
                AlertEvent.status == "firing",
            ).order_by(desc(AlertEvent.triggered_at)).limit(1)
        )
        return result.scalars().first()

    async def find_firing_by_rule(self, rule_id: UUID) -> List[AlertEvent]:
        result = await self.session.execute(
            select(AlertEvent).where(
                AlertEvent.rule_id == rule_id,
                AlertEvent.status == "firing",
            ).order_by(desc(AlertEvent.triggered_at))
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> AlertEvent:
        event = AlertEvent(id=uuid.uuid4(), **kwargs)
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def update(self, event_id: UUID, **kwargs) -> AlertEvent:
        event = await self.get_by_id(event_id)
        if not event:
            raise NotFoundException("AlertEvent", str(event_id))

        for key, value in kwargs.items():
            if value is not None:
                setattr(event, key, value)

        await self.session.flush()
        return await self.get_by_id(event_id)

    async def get_stats(self) -> Dict[str, Any]:
        status_result = await self.session.execute(
            select(AlertEvent.status, func.count(AlertEvent.id))
            .group_by(AlertEvent.status)
        )
        status_counts = {row[0]: row[1] for row in status_result.all()}

        severity_result = await self.session.execute(
            select(AlertEvent.severity, func.count(AlertEvent.id))
            .group_by(AlertEvent.severity)
        )
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        total_result = await self.session.execute(select(func.count(AlertEvent.id)))
        total = total_result.scalar() or 0

        by_metric_result = await self.session.execute(
            select(AlertRule.metric_name, func.count(AlertEvent.id))
            .join(AlertRule, AlertEvent.rule_id == AlertRule.id)
            .where(AlertEvent.status == "firing")
            .group_by(AlertRule.metric_name)
        )
        by_metric = {row[0]: row[1] for row in by_metric_result.all()}

        by_server_result = await self.session.execute(
            select(AlertEvent.server_id, func.count(AlertEvent.id))
            .where(AlertEvent.status == "firing")
            .group_by(AlertEvent.server_id)
            .limit(20)
        )
        by_server = {str(row[0]): row[1] for row in by_server_result.all()}

        return {
            "total_events": total,
            "firing": status_counts.get("firing", 0),
            "acknowledged": status_counts.get("acknowledged", 0),
            "resolved": status_counts.get("resolved", 0),
            "suppressed": status_counts.get("suppressed", 0),
            "critical": severity_counts.get("critical", 0),
            "warning": severity_counts.get("warning", 0),
            "info": severity_counts.get("info", 0),
            "by_metric": by_metric,
            "by_server": by_server,
        }
