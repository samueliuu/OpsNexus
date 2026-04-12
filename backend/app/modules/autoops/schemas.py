from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TaskStepConfig(BaseModel):
    step_number: int = Field(..., ge=1)
    step_name: str = Field(..., max_length=128)
    action: str = Field(..., max_length=64)
    parameters: Optional[Dict[str, Any]] = None
    timeout_seconds: int = Field(default=600, ge=10)
    on_failure: str = Field(default="abort", pattern="^(abort|skip|retry)$")


class TaskDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    task_type: str = Field(..., pattern="^(firmware_upgrade|inspection|config_deploy|custom)$")
    target_filter: Dict[str, Any]
    steps: List[TaskStepConfig] = Field(..., min_length=1)
    parameters: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = Field(None, max_length=64)
    is_scheduled: bool = False
    requires_approval: bool = False
    approver_roles: Optional[List[str]] = None
    retry_policy: Dict[str, Any] = Field(default={"max_retries": 3, "retry_delay_seconds": 60, "retry_delay_strategy": "exponential"})
    timeout_seconds: int = Field(default=3600, ge=60)
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.is_scheduled and not self.schedule:
            raise ValueError("schedule is required when is_scheduled is True")
        return self


class TaskDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    target_filter: Optional[Dict[str, Any]] = None
    steps: Optional[List[TaskStepConfig]] = None
    parameters: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = Field(None, max_length=64)
    is_scheduled: Optional[bool] = None
    requires_approval: Optional[bool] = None
    approver_roles: Optional[List[str]] = None
    retry_policy: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = Field(None, ge=60)
    is_enabled: Optional[bool] = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.is_scheduled is True and not self.schedule:
            raise ValueError("schedule is required when is_scheduled is True")
        return self


class TaskDefinitionResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    task_type: str
    target_filter: Dict[str, Any]
    steps: List[Any]
    parameters: Optional[Dict[str, Any]]
    schedule: Optional[str]
    is_scheduled: bool
    requires_approval: bool
    approver_roles: Optional[List[str]]
    retry_policy: Optional[Dict[str, Any]] = None
    timeout_seconds: int
    is_enabled: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskDefinitionListResponse(BaseModel):
    items: List[TaskDefinitionResponse]
    total: int
    page: int
    page_size: int


class TaskInstanceCreate(BaseModel):
    task_def_id: UUID
    trigger_type: str = Field(default="manual", pattern="^(manual|scheduled|api)$")
    parameters: Optional[Dict[str, Any]] = None


class TaskInstanceResponse(BaseModel):
    id: UUID
    task_def_id: UUID
    status: str
    trigger_type: str
    parameters: Optional[Dict[str, Any]]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: Optional[str]
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    task_name: Optional[str] = None

    class Config:
        from_attributes = True


class TaskInstanceListResponse(BaseModel):
    items: List[TaskInstanceResponse]
    total: int
    page: int
    page_size: int


class TaskApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: Optional[str] = None


class TaskStepLogResponse(BaseModel):
    id: UUID
    task_instance_id: UUID
    server_id: UUID
    step_number: int
    step_name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    output: Optional[str]
    error_message: Optional[str]
    created_at: datetime

    server_name: Optional[str] = None

    class Config:
        from_attributes = True


class FirmwarePackageCreate(BaseModel):
    filename: str = Field(..., max_length=255)
    brand: str = Field(..., max_length=32)
    component: str = Field(..., max_length=64)
    version: str = Field(..., max_length=64)
    file_size: int = Field(..., ge=1)
    file_hash: Optional[str] = Field(None, max_length=64)
    supported_models: Optional[List[str]] = None
    release_notes: Optional[str] = None


class FirmwarePackageResponse(BaseModel):
    id: UUID
    filename: str
    brand: str
    component: str
    version: str
    file_size: int
    file_hash: Optional[str]
    minio_bucket: str
    minio_key: str
    upload_status: str
    supported_models: Optional[List[str]]
    release_notes: Optional[str]
    uploaded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FirmwarePackageListResponse(BaseModel):
    items: List[FirmwarePackageResponse]
    total: int
    page: int
    page_size: int


class InspectionPolicyCreate(BaseModel):
    schedule: str = Field(..., max_length=64)
    target_filter: Dict[str, Any]
    check_items: List[str] = Field(..., min_length=1)


class InspectionPolicyResponse(BaseModel):
    id: UUID
    task_def_id: UUID
    schedule: str
    target_filter: Dict[str, Any]
    check_items: List[Any]
    enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
