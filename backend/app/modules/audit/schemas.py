from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditLogCreate(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = Field(None, max_length=64)
    action: str = Field(..., max_length=64)
    resource_type: str = Field(..., max_length=64)
    resource_id: Optional[str] = Field(None, max_length=64)
    resource_name: Optional[str] = Field(None, max_length=128)
    detail: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=512)
    request_id: Optional[str] = Field(None, max_length=64)
    status: str = Field(default="success", pattern="^(success|failure)$")
    error_message: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    username: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    resource_name: Optional[str]
    detail: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("ip_address", mode="before")
    @classmethod
    def coerce_ip_address(cls, v):
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogStatsResponse(BaseModel):
    total: int
    by_action: Dict[str, int]
    by_resource_type: Dict[str, int]
    by_status: Dict[str, int]
    by_user: Dict[str, int]
    recent_failures: int


class AuditLogExportRequest(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[UUID] = None
    status: Optional[str] = None
    format: str = Field(default="csv", pattern="^(csv|json)$")


class NotificationSendRequest(BaseModel):
    channel_ids: List[UUID] = Field(..., min_length=1)
    subject: Optional[str] = Field(None, max_length=255)
    content: str = Field(..., min_length=1)
    recipients: Optional[List[str]] = Field(None, description="Override channel default recipients")
    related_alert_id: Optional[UUID] = None


class NotificationLogResponse(BaseModel):
    id: UUID
    channel_id: UUID
    channel_type: str
    recipient: str
    subject: Optional[str]
    content: str
    status: str
    error_message: Optional[str]
    sent_at: Optional[datetime]
    retry_count: int
    related_alert_id: Optional[UUID]
    created_at: datetime

    channel_name: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationLogListResponse(BaseModel):
    items: List[NotificationLogResponse]
    total: int
    page: int
    page_size: int


class NotificationRetryRequest(BaseModel):
    log_ids: List[UUID] = Field(..., min_length=1)


class NotificationStatsResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_channel_type: Dict[str, int]
    recent_failed: int
