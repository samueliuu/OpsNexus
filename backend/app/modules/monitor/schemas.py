from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MetricDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(..., max_length=128)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=32)
    metric_type: str = Field(..., pattern="^(gauge|counter|histogram)$")
    data_type: str = Field(default="float", pattern="^(float|int|bool)$")
    labels: Optional[List[str]] = None
    collection_method: str = Field(default="bmc", pattern="^(bmc|snmp|agent)$")
    default_interval: int = Field(default=60, ge=10, le=3600)
    is_active: bool = True


class MetricDefinitionUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=32)
    labels: Optional[List[str]] = None
    default_interval: Optional[int] = Field(None, ge=10, le=3600)
    is_active: Optional[bool] = None


class MetricDefinitionResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    unit: Optional[str]
    metric_type: str
    data_type: str
    labels: Optional[List[str]]
    collection_method: str
    default_interval: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MetricDefinitionListResponse(BaseModel):
    items: List[MetricDefinitionResponse]
    total: int
    page: int
    page_size: int


class MetricDataQuery(BaseModel):
    metric_name: str = Field(..., max_length=64)
    server_ids: Optional[List[UUID]] = None
    start_time: datetime
    end_time: datetime
    step: Optional[int] = Field(None, ge=10, description="Aggregation step in seconds")
    aggregation: Optional[str] = Field(None, pattern="^(avg|max|min|sum|last)$")
    labels: Optional[Dict[str, str]] = None


class MetricDataPoint(BaseModel):
    time: datetime
    server_id: UUID
    value: float
    labels: Optional[Dict[str, str]] = None


class MetricDataResponse(BaseModel):
    metric_name: str
    data_points: List[MetricDataPoint]
    total_points: int


class MetricDataWrite(BaseModel):
    server_id: UUID
    metric_name: str = Field(..., max_length=64)
    value: float
    labels: Optional[Dict[str, str]] = None
    timestamp: Optional[datetime] = None


class MetricDataBatchWrite(BaseModel):
    metrics: List[MetricDataWrite] = Field(..., min_length=1, max_length=1000)


class ServerMetricsSummary(BaseModel):
    server_id: UUID
    server_name: str
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_temperature: Optional[float] = None
    power_consumption: Optional[float] = None
    fan_speed_avg: Optional[float] = None
    last_collected_at: Optional[datetime] = None
    health_status: str = "unknown"


class DashboardMetricsResponse(BaseModel):
    total_servers: int
    online_servers: int
    alerting_servers: int
    critical_alerts: int
    warning_alerts: int
    server_summaries: List[ServerMetricsSummary]


class AlertRuleCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    metric_name: str = Field(..., max_length=64)
    condition: str = Field(..., pattern="^(gt|lt|eq|ne|ge|le)$")
    threshold: float
    duration: int = Field(default=60, ge=0, le=86400, description="Seconds to trigger")
    severity: str = Field(default="warning", pattern="^(critical|warning|info)$")
    target_filter: Optional[Dict[str, Any]] = Field(
        None, description="Server filter: {brand, model, data_center_id, status}"
    )
    notification_channels: Optional[List[UUID]] = Field(
        None, description="Notification channel IDs"
    )
    is_enabled: bool = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    condition: Optional[str] = Field(None, pattern="^(gt|lt|eq|ne|ge|le)$")
    threshold: Optional[float] = None
    duration: Optional[int] = Field(None, ge=0, le=86400)
    severity: Optional[str] = Field(None, pattern="^(critical|warning|info)$")
    target_filter: Optional[Dict[str, Any]] = None
    notification_channels: Optional[List[UUID]] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    metric_name: str
    condition: str
    threshold: float
    duration: int
    severity: str
    target_filter: Optional[Dict[str, Any]]
    notification_channels: Optional[List[UUID]]
    is_enabled: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("notification_channels", mode="before")
    @classmethod
    def parse_uuid_list(cls, v):
        if v is None:
            return None
        from uuid import UUID as UUIDType
        return [UUIDType(str(item)) for item in v]


class AlertRuleListResponse(BaseModel):
    items: List[AlertRuleResponse]
    total: int
    page: int
    page_size: int


class AlertEventResponse(BaseModel):
    id: UUID
    rule_id: UUID
    server_id: UUID
    severity: str
    status: str
    summary: str
    description: Optional[str]
    metric_value: Optional[float]
    triggered_at: datetime
    resolved_at: Optional[datetime]
    acknowledged_by: Optional[UUID]
    acknowledged_at: Optional[datetime]
    notification_sent: bool
    created_at: datetime

    rule_name: Optional[str] = None
    server_name: Optional[str] = None

    class Config:
        from_attributes = True


class AlertEventListResponse(BaseModel):
    items: List[AlertEventResponse]
    total: int
    page: int
    page_size: int


class AlertAcknowledgeRequest(BaseModel):
    event_ids: List[UUID] = Field(..., min_length=1)


class AlertSuppressRequest(BaseModel):
    event_ids: List[UUID] = Field(..., min_length=1)
    reason: Optional[str] = None


class AlertStatsResponse(BaseModel):
    total_events: int
    firing: int
    acknowledged: int
    resolved: int
    suppressed: int
    critical: int
    warning: int
    info: int
    by_metric: Dict[str, int]
    by_server: Dict[str, int]


class MetricCollectionTask(BaseModel):
    server_ids: Optional[List[UUID]] = Field(None, description="None = all servers")
    metric_names: Optional[List[str]] = Field(None, description="None = all active metrics")
    force: bool = Field(default=False, description="Force collection ignoring interval")


class MetricCollectionResult(BaseModel):
    collected_servers: int
    collected_metrics: int
    failed_servers: int
    errors: List[Dict[str, str]] = []
