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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DataCenter(Base):
    __tablename__ = "data_centers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    contact_name: Mapped[Optional[str]] = mapped_column(String(64))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


    # Relationships
    racks: Mapped[List["Rack"]] = relationship("Rack", back_populates="data_center", lazy="selectin")


class Rack(Base):
    __tablename__ = "racks"
    __table_args__ = (UniqueConstraint("data_center_id", "code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    data_center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_centers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(128))
    u_height: Mapped[int] = mapped_column(Integer, default=42)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    data_center: Mapped["DataCenter"] = relationship("DataCenter", back_populates="racks")
    servers: Mapped[List["Server"]] = relationship("Server", back_populates="rack", lazy="selectin")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rack_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("racks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hostname: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    asset_tag: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    brand: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="active", index=True
    )  # active, inactive, maintenance, retired
    server_type: Mapped[str] = mapped_column(
        String(32), default="physical"
    )  # physical, virtual, blade
    cpu_model: Mapped[Optional[str]] = mapped_column(String(128))
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    cpu_cores_per_socket: Mapped[int] = mapped_column(Integer, default=0)
    memory_gb: Mapped[int] = mapped_column(Integer, default=0)
    disk_info: Mapped[Optional[dict]] = mapped_column(JSON)  # Disk configuration
    network_interfaces: Mapped[Optional[dict]] = mapped_column(JSON)  # NIC info
    os_name: Mapped[Optional[str]] = mapped_column(String(64))
    os_version: Mapped[Optional[str]] = mapped_column(String(64))
    bmc_ip: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    bmc_mac: Mapped[Optional[str]] = mapped_column(String(32))
    bmc_status: Mapped[str] = mapped_column(
        String(32), default="unknown"
    )  # online, offline, unknown, error
    bmc_unreachable: Mapped[bool] = mapped_column(Boolean, default=False)
    bmc_unreachable_since: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rack_position: Mapped[Optional[int]] = mapped_column(Integer)  # Starting U position
    rack_height: Mapped[int] = mapped_column(Integer, default=1)  # U height occupied
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    rack: Mapped[Optional["Rack"]] = relationship("Rack", back_populates="servers")
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="owned_servers", foreign_keys="Server.owner_id")
    bmc_credential: Mapped[Optional["BMCCredential"]] = relationship(
        "BMCCredential", back_populates="server", uselist=False
    )
    sel_logs: Mapped[List["SELLog"]] = relationship("SELLog", back_populates="server", lazy="selectin")
    firmware_inventory: Mapped[List["FirmwareInventory"]] = relationship("FirmwareInventory", back_populates="server", lazy="selectin")
    kvm_sessions: Mapped[List["KVMSession"]] = relationship("KVMSession", back_populates="server", lazy="selectin")
    alert_events: Mapped[List["AlertEvent"]] = relationship("AlertEvent", back_populates="server", lazy="selectin")
    task_step_logs: Mapped[List["TaskStepLog"]] = relationship("TaskStepLog", back_populates="server", lazy="selectin")


class BMCCredential(Base):
    __tablename__ = "bmc_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol: Mapped[str] = mapped_column(
        String(16), default="redfish"
    )  # redfish, ipmi, snmp
    port: Mapped[int] = mapped_column(Integer, default=443)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    server: Mapped["Server"] = relationship("Server", back_populates="bmc_credential")
