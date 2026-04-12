import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskDefinition(Base):
    __tablename__ = "task_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # firmware_upgrade, inspection, config_deploy, custom
    target_filter: Mapped[dict] = mapped_column(JSON, nullable=False)  # Server selection criteria
    steps: Mapped[list] = mapped_column(JSON, nullable=False)  # Task steps configuration
    parameters: Mapped[Optional[dict]] = mapped_column(JSON)  # Task parameters schema
    schedule: Mapped[Optional[str]] = mapped_column(String(64))  # Cron expression for scheduled tasks
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approver_roles: Mapped[Optional[list]] = mapped_column(JSON)  # Role IDs that can approve
    retry_policy: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "max_retries": 3,
            "retry_delay_seconds": 60,
            "retry_delay_strategy": "exponential",
        },
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    task_instances: Mapped[List["TaskInstance"]] = relationship("TaskInstance", back_populates="task_definition", lazy="selectin")


class TaskInstance(Base):
    __tablename__ = "task_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_def_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", index=True
    )  # pending, approved, running, paused, completed, failed, cancelled
    trigger_type: Mapped[str] = mapped_column(
        String(16), default="manual"
    )  # manual, scheduled, api
    parameters: Mapped[Optional[dict]] = mapped_column(JSON)  # Runtime parameters
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    summary: Mapped[Optional[str]] = mapped_column(Text)  # Execution summary
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    task_definition: Mapped["TaskDefinition"] = relationship("TaskDefinition", back_populates="task_instances")
    step_logs: Mapped[List["TaskStepLog"]] = relationship("TaskStepLog", back_populates="task_instance", lazy="selectin")

    @property
    def task_name(self) -> Optional[str]:
        return self.task_definition.name if self.task_definition else None


class TaskStepLog(Base):
    __tablename__ = "task_step_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_instances.id", ondelete="CASCADE"), nullable=False, index=True
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending, running, completed, failed, skipped
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[Optional[str]] = mapped_column(Text)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    task_instance: Mapped["TaskInstance"] = relationship("TaskInstance", back_populates="step_logs")
    server: Mapped["Server"] = relationship("Server", back_populates="task_step_logs")

    @property
    def server_name(self) -> Optional[str]:
        return self.server.name if self.server else None


class FirmwarePackage(Base):
    __tablename__ = "firmware_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(64), nullable=False)  # BIOS, BMC, RAID, etc.
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    minio_bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    minio_key: Mapped[str] = mapped_column(String(512), nullable=False)
    upload_status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending, uploading, completed, verified, failed
    supported_models: Mapped[Optional[list]] = mapped_column(JSON)  # List of supported server models
    release_notes: Mapped[Optional[str]] = mapped_column(Text)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class InspectionPolicy(Base):
    __tablename__ = "inspection_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_def_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_definitions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    schedule: Mapped[str] = mapped_column(String(64), nullable=False)  # Cron expression
    target_filter: Mapped[dict] = mapped_column(JSON, nullable=False)
    check_items: Mapped[list] = mapped_column(JSON, nullable=False)  # List of inspection items
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
