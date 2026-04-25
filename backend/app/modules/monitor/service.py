import operator
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import AdapterRegistry, BMCConnection
from app.core.cache import Cache
from app.core.config import settings
from app.core.events import EventTypes, publish_event
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.core.security import decrypt_value
from app.modules.asset.models import BMCCredential, Server
from app.modules.monitor.models import AlertEvent, AlertRule, MetricData, MetricDefinition
from app.modules.monitor.repository import (
    AlertEventRepository,
    AlertRuleRepository,
    MetricDataRepository,
    MetricDefinitionRepository,
)
from app.modules.monitor.schemas import (
    AlertStatsResponse,
    DashboardMetricsResponse,
    MetricCollectionResult,
    ServerMetricsSummary,
)

logger = get_logger(__name__)

CONDITION_OPS = {
    "gt": operator.gt,
    "lt": operator.lt,
    "eq": operator.eq,
    "ne": operator.ne,
    "ge": operator.ge,
    "le": operator.le,
}


class MetricDefinitionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MetricDefinitionRepository(session)

    async def create(self, **kwargs) -> MetricDefinition:
        return await self.repo.create(**kwargs)

    async def update(self, metric_id: UUID, **kwargs) -> MetricDefinition:
        return await self.repo.update(metric_id, **kwargs)

    async def delete(self, metric_id: UUID) -> bool:
        return await self.repo.delete(metric_id)

    async def get_by_id(self, metric_id: UUID) -> MetricDefinition:
        metric = await self.repo.get_by_id(metric_id)
        if not metric:
            raise NotFoundException("MetricDefinition", str(metric_id))
        return metric

    async def list_all(self, **kwargs) -> Tuple[List[MetricDefinition], int]:
        return await self.repo.list_all(**kwargs)


class MetricDataService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MetricDataRepository(session)
        self.definition_repo = MetricDefinitionRepository(session)

    async def write_metric(self, server_id: UUID, metric_name: str, value: float,
                           labels: Optional[Dict] = None, timestamp: Optional[datetime] = None) -> MetricData:
        definition = await self.definition_repo.get_by_name(metric_name)
        if not definition:
            raise NotFoundException("MetricDefinition", f"name={metric_name}")
        if not definition.is_active:
            raise ValidationException(f"Metric '{metric_name}' is not active")

        return await self.repo.write(server_id, metric_name, value, labels, timestamp)

    async def write_batch(self, metrics: List[Dict[str, Any]]) -> int:
        return await self.repo.write_batch(metrics)

    async def query_range(self, **kwargs) -> List[MetricData]:
        return await self.repo.query_range(**kwargs)

    async def get_latest(self, metric_name: str, server_id: UUID) -> Optional[MetricData]:
        return await self.repo.get_latest(metric_name, server_id)

    async def cleanup_old_data(self, retention_days: int = 90) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return await self.repo.delete_before(cutoff)

    async def get_dashboard_metrics(self) -> DashboardMetricsResponse:
        servers_result = await self.session.execute(
            select(Server).where(Server.status == "active")
        )
        servers = servers_result.scalars().all()

        total_servers = len(servers)
        online_servers = sum(1 for s in servers if s.bmc_status == "online")
        server_ids = [s.id for s in servers]

        key_metrics = [
            "cpu_usage_percent", "memory_usage_percent",
            "cpu_temperature_celsius", "power_consumption_watts",
            "fan_speed_rpm_avg",
        ]
        latest_data = await self.repo.get_latest_for_servers(key_metrics, server_ids)

        server_summaries = []
        alerting_server_ids = set()

        alert_result = await self.session.execute(
            select(AlertEvent.server_id).where(AlertEvent.status == "firing")
        )
        for row in alert_result.all():
            alerting_server_ids.add(row[0])

        for server in servers:
            summary = ServerMetricsSummary(
                server_id=server.id,
                server_name=server.name,
                cpu_usage=latest_data.get("cpu_usage_percent", {}).get(server.id),
                memory_usage=latest_data.get("memory_usage_percent", {}).get(server.id),
                cpu_temperature=latest_data.get("cpu_temperature_celsius", {}).get(server.id),
                power_consumption=latest_data.get("power_consumption_watts", {}).get(server.id),
                fan_speed_avg=latest_data.get("fan_speed_rpm_avg", {}).get(server.id),
            )

            if server.id in alerting_server_ids:
                summary.health_status = "alerting"
            elif server.bmc_status == "online":
                summary.health_status = "healthy"
            elif server.bmc_status == "offline":
                summary.health_status = "offline"
            else:
                summary.health_status = "unknown"

            server_summaries.append(summary)

        critical_result = await self.session.execute(
            select(func.count(AlertEvent.id)).where(
                AlertEvent.status == "firing",
                AlertEvent.severity == "critical",
            )
        )
        critical_alerts = critical_result.scalar() or 0

        warning_result = await self.session.execute(
            select(func.count(AlertEvent.id)).where(
                AlertEvent.status == "firing",
                AlertEvent.severity == "warning",
            )
        )
        warning_alerts = warning_result.scalar() or 0

        return DashboardMetricsResponse(
            total_servers=total_servers,
            online_servers=online_servers,
            alerting_servers=len(alerting_server_ids),
            critical_alerts=critical_alerts,
            warning_alerts=warning_alerts,
            server_summaries=server_summaries,
        )


class MetricCollectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.metric_repo = MetricDataRepository(session)
        self.definition_repo = MetricDefinitionRepository(session)

    async def collect_from_server(self, server: Server, credential: BMCCredential,
                                  metric_names: Optional[List[str]] = None) -> Dict[str, Any]:
        connection = BMCConnection(
            host=server.bmc_ip,
            username=credential.username,
            password=decrypt_value(credential.encrypted_password),
            protocol=credential.protocol,
            port=credential.port,
            verify_ssl=False,
            timeout=settings.bmc_connect_timeout,
        )

        adapter = AdapterRegistry.create(server.brand, connection)
        collected = []
        errors = []

        try:
            async with adapter:
                sensors = await adapter.get_sensor_data()
                power_supplies = await adapter.get_power_supplies()
                fans = await adapter.get_fans()

                metrics_to_write = []

                for sensor in sensors:
                    if sensor.reading is None:
                        continue
                    metric_name = self._sensor_to_metric_name(sensor.sensor_type, sensor.name)
                    if metric_names and metric_name not in metric_names:
                        continue

                    metrics_to_write.append({
                        "server_id": server.id,
                        "metric_name": metric_name,
                        "value": float(sensor.reading),
                        "labels": {
                            "sensor_type": sensor.sensor_type,
                            "sensor_name": sensor.name,
                            "unit": sensor.unit or "",
                            "status": sensor.status.value,
                        },
                    })
                    collected.append(metric_name)

                if power_supplies and (not metric_names or "power_consumption_watts" in metric_names):
                    total_power = sum(
                        ps.output_watts or 0 for ps in power_supplies if ps.output_watts
                    )
                    if total_power > 0:
                        metrics_to_write.append({
                            "server_id": server.id,
                            "metric_name": "power_consumption_watts",
                            "value": total_power,
                            "labels": {"unit": "Watts"},
                        })
                        collected.append("power_consumption_watts")

                if fans and (not metric_names or "fan_speed_rpm_avg" in metric_names):
                    fan_speeds = [f.reading_rpm for f in fans if f.reading_rpm]
                    if fan_speeds:
                        avg_speed = sum(fan_speeds) / len(fan_speeds)
                        metrics_to_write.append({
                            "server_id": server.id,
                            "metric_name": "fan_speed_rpm_avg",
                            "value": avg_speed,
                            "labels": {"unit": "RPM", "fan_count": str(len(fan_speeds))},
                        })
                        collected.append("fan_speed_rpm_avg")

                if metrics_to_write:
                    await self.metric_repo.write_batch(metrics_to_write)

                server.bmc_status = "online"
                await self.session.flush()

        except Exception as e:
            logger.error(f"Failed to collect metrics from {server.name}: {e}")
            errors.append({"server": server.name, "error": str(e)})
            server.bmc_status = "error"
            await self.session.flush()

        return {
            "server_id": str(server.id),
            "collected": list(set(collected)),
            "error_count": len(errors),
            "errors": errors,
        }

    async def collect_batch(
        self,
        server_ids: Optional[List[UUID]] = None,
        metric_names: Optional[List[str]] = None,
        force: bool = False,
    ) -> MetricCollectionResult:
        query = select(Server).where(Server.status == "active")
        if server_ids:
            query = query.where(Server.id.in_(server_ids))

        servers_result = await self.session.execute(query)
        servers = servers_result.scalars().all()

        tasks = []
        task_servers = []

        for server in servers:
            if not server.bmc_ip:
                continue

            if not force:
                cache_key = f"metric_collected:{server.id}"
                last_collected = await Cache.get(cache_key)
                if last_collected:
                    continue

            cred_result = await self.session.execute(
                select(BMCCredential).where(BMCCredential.server_id == server.id)
            )
            credential = cred_result.scalar_one_or_none()
            if not credential:
                continue

            tasks.append(self.collect_from_server(server, credential, metric_names))
            task_servers.append(server)

        results = []
        for task in tasks:
            results.append(await task)

        collected_servers = 0
        collected_metrics = 0
        failed_servers = 0
        all_errors = []

        for server, result in zip(task_servers, results):
            if isinstance(result, Exception):
                failed_servers += 1
                all_errors.append({"server": server.name, "error": str(result)})
            elif result["error_count"] == 0:
                collected_servers += 1
                collected_metrics += len(result["collected"])
                await Cache.set(
                    f"metric_collected:{server.id}",
                    datetime.now(timezone.utc).isoformat(),
                    expire=60,
                )
            else:
                failed_servers += 1
                all_errors.extend(result["errors"])

        return MetricCollectionResult(
            collected_servers=collected_servers,
            collected_metrics=collected_metrics,
            failed_servers=failed_servers,
            errors=all_errors,
        )

    def _sensor_to_metric_name(self, sensor_type: str, sensor_name: str) -> str:
        type_map = {
            "Temperature": "temperature_celsius",
            "Fan": "fan_speed_rpm",
            "Voltage": "voltage_volts",
            "Current": "current_amps",
            "Power": "power_watts",
            "Memory": "memory_usage_percent",
            "CPU": "cpu_usage_percent",
            "Storage": "disk_usage_percent",
        }
        base = type_map.get(sensor_type, f"{sensor_type.lower()}_value")
        name_clean = sensor_name.lower().replace(" ", "_").replace("#", "")
        return f"{base}__{name_clean}"


class AlertRuleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AlertRuleRepository(session)

    async def create(self, created_by: UUID, **kwargs) -> AlertRule:
        return await self.repo.create(created_by=created_by, **kwargs)

    async def update(self, rule_id: UUID, **kwargs) -> AlertRule:
        return await self.repo.update(rule_id, **kwargs)

    async def delete(self, rule_id: UUID) -> bool:
        return await self.repo.delete(rule_id)

    async def get_by_id(self, rule_id: UUID) -> AlertRule:
        rule = await self.repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundException("AlertRule", str(rule_id))
        return rule

    async def list_all(self, **kwargs) -> Tuple[List[AlertRule], int]:
        return await self.repo.list_all(**kwargs)


class AlertEvaluationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rule_repo = AlertRuleRepository(session)
        self.event_repo = AlertEventRepository(session)
        self.metric_repo = MetricDataRepository(session)

    async def evaluate_all(self) -> Dict[str, int]:
        rules = await self.rule_repo.list_enabled()
        total_evaluated = 0
        new_firing = 0
        new_resolved = 0

        for rule in rules:
            try:
                result = await self._evaluate_rule(rule)
                total_evaluated += result.get("evaluated", 0)
                new_firing += result.get("firing", 0)
                new_resolved += result.get("resolved", 0)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")

        return {
            "rules_evaluated": len(rules),
            "total_evaluated": total_evaluated,
            "new_firing": new_firing,
            "new_resolved": new_resolved,
        }

    async def _evaluate_rule(self, rule: AlertRule) -> Dict[str, int]:
        target_servers = await self._get_target_servers(rule.target_filter)
        op_func = CONDITION_OPS.get(rule.condition)
        if not op_func:
            logger.warning(f"Unknown condition: {rule.condition}")
            return {"evaluated": 0, "firing": 0, "resolved": 0}

        if not target_servers:
            return {"evaluated": 0, "firing": 0, "resolved": 0}

        server_ids = [s.id for s in target_servers]
        server_map = {s.id: s for s in target_servers}

        latest_map = await self.metric_repo.get_latest_for_servers(
            [rule.metric_name], server_ids
        )
        metric_data = latest_map.get(rule.metric_name, {})

        firing_events = await self.event_repo.find_firing_by_rule(rule.id)
        firing_map = {fe.server_id: fe for fe in firing_events}

        firing_count = 0
        resolved_count = 0

        for server_id, value in metric_data.items():
            if value is None:
                continue

            server = server_map.get(server_id)
            if not server:
                continue

            is_breaching = op_func(value, rule.threshold)
            existing_event = firing_map.get(server_id)

            should_trigger = is_breaching
            if rule.duration > 0 and is_breaching and not existing_event:
                should_trigger = await self._check_duration(
                    rule.metric_name, server_id, rule.condition,
                    rule.threshold, rule.duration,
                )

            if should_trigger and not existing_event:
                event = await self.event_repo.create(
                    rule_id=rule.id,
                    server_id=server_id,
                    severity=rule.severity,
                    status="firing",
                    summary=f"{rule.name}: {rule.metric_name} {rule.condition} {rule.threshold}",
                    description=f"Current value: {value}, threshold: {rule.threshold}",
                    metric_value=value,
                )
                firing_count += 1

                await publish_event(EventTypes.ALERT_TRIGGERED, {
                    "event_id": str(event.id),
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "server_id": str(server_id),
                    "server_name": server.name,
                    "severity": rule.severity,
                    "metric_name": rule.metric_name,
                    "metric_value": value,
                    "threshold": rule.threshold,
                    "condition": rule.condition,
                })

            elif not is_breaching and existing_event:
                await self.event_repo.update(
                    existing_event.id,
                    status="resolved",
                    resolved_at=datetime.now(timezone.utc),
                )
                resolved_count += 1

                await publish_event(EventTypes.ALERT_RESOLVED, {
                    "event_id": str(existing_event.id),
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "server_id": str(server_id),
                    "server_name": server.name,
                    "metric_name": rule.metric_name,
                })

        return {
            "evaluated": len(target_servers),
            "firing": firing_count,
            "resolved": resolved_count,
        }

    async def _check_duration(
        self, metric_name: str, server_id: UUID,
        condition: str, threshold: float, duration_seconds: int,
    ) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)
        data_points = await self.metric_repo.query_range(
            metric_name=metric_name,
            server_ids=[server_id],
            start_time=cutoff,
            end_time=datetime.now(timezone.utc),
            limit=1000,
        )

        if not data_points:
            return False

        op_func = CONDITION_OPS[condition]
        breaching_count = sum(1 for dp in data_points if op_func(dp.value, threshold))
        return breaching_count >= len(data_points) * 0.8

    async def _get_target_servers(self, target_filter: Optional[Dict]) -> List[Server]:
        query = select(Server)

        status_filter = "active"
        if target_filter:
            status_filter = target_filter.get("status", "active")

        query = query.where(Server.status == status_filter)

        if target_filter:
            if "brand" in target_filter:
                query = query.where(Server.brand == target_filter["brand"])
            if "model" in target_filter:
                query = query.where(Server.model == target_filter["model"])
            if "data_center_id" in target_filter:
                try:
                    dc_id = UUID(str(target_filter["data_center_id"]))
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid data_center_id in target_filter: {target_filter['data_center_id']}")
                    return []
                from app.modules.asset.models import Rack
                query = query.join(Rack, Server.rack_id == Rack.id).where(
                    Rack.data_center_id == dc_id
                )

        result = await self.session.execute(query)
        return result.scalars().all()


class AlertEventService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AlertEventRepository(session)

    async def get_by_id(self, event_id: UUID) -> AlertEvent:
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise NotFoundException("AlertEvent", str(event_id))
        return event

    async def list_all(self, **kwargs) -> Tuple[List[AlertEvent], int]:
        return await self.repo.list_all(**kwargs)

    async def acknowledge(self, event_ids: List[UUID], user_id: UUID) -> int:
        count = 0
        events, _ = await self.repo.list_all(
            skip=0, limit=len(event_ids) * 2, status="firing"
        )
        firing_map = {e.id: e for e in events if e.id in set(event_ids) and e.status == "firing"}

        for event_id in event_ids:
            event = firing_map.get(event_id)
            if not event:
                event = await self.repo.get_by_id(event_id)
            if event and event.status == "firing":
                await self.repo.update(
                    event_id,
                    status="acknowledged",
                    acknowledged_by=user_id,
                    acknowledged_at=datetime.now(timezone.utc),
                )
                count += 1

                await publish_event(EventTypes.ALERT_ACKNOWLEDGED, {
                    "event_id": str(event_id),
                    "acknowledged_by": str(user_id),
                })
        return count

    async def suppress(self, event_ids: List[UUID], reason: Optional[str] = None) -> int:
        count = 0
        for event_id in event_ids:
            event = await self.repo.get_by_id(event_id)
            if event and event.status in ("firing", "acknowledged"):
                update_data = {"status": "suppressed"}
                if reason:
                    desc = event.description or ""
                    update_data["description"] = f"{desc}\n[Suppressed] {reason}".strip()
                await self.repo.update(event_id, **update_data)
                count += 1
        return count

    async def get_stats(self) -> AlertStatsResponse:
        stats = await self.repo.get_stats()
        return AlertStatsResponse(**stats)
