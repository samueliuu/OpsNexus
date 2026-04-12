from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# BMC Connection & Status
class BMCConnectionTest(BaseModel):
    host: str = Field(..., max_length=64)
    username: str = Field(..., max_length=64)
    password: str = Field(..., max_length=128)
    protocol: str = Field(default="redfish", pattern="^(redfish|ipmi|snmp)$")
    port: int = Field(default=443, ge=1, le=65535)


class BMCConnectionTestResponse(BaseModel):
    success: bool
    message: str
    firmware_version: Optional[str] = None
    detected_brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None


# System Info
class SystemInfoResponse(BaseModel):
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    sku: str = ""
    bios_version: str = ""
    bmc_version: str = ""
    bmc_ip: str = ""
    hostname: str = ""
    power_state: str = ""
    health: str = ""
    processor_count: int = 0
    processor_model: str = ""
    memory_total_gb: float = 0
    raw_data: Optional[Dict[str, Any]] = None


# Power Control
class PowerActionRequest(BaseModel):
    action: str = Field(..., pattern="^(on|off|graceful_off|force_off|restart|graceful_restart|force_restart|nmi)$")


class PowerStateResponse(BaseModel):
    server_id: UUID
    power_state: str
    timestamp: datetime


class PowerActionResponse(BaseModel):
    server_id: UUID
    action: str
    previous_state: str
    current_state: str
    timestamp: datetime


# Sensor Data
class SensorDataResponse(BaseModel):
    name: str
    reading: Optional[float] = None
    unit: str = ""
    status: str = ""
    sensor_type: str = ""
    lower_threshold_critical: Optional[float] = None
    upper_threshold_critical: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class SensorDataListResponse(BaseModel):
    server_id: UUID
    sensors: List[SensorDataResponse]
    timestamp: datetime


# SEL Log
class SELEntryResponse(BaseModel):
    id: UUID
    server_id: UUID
    record_id: int
    timestamp: datetime
    sensor_type: str
    sensor_name: str
    event_type: str
    severity: str
    description: str
    is_acknowledged: bool
    acknowledged_by: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    raw_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class SELLogListResponse(BaseModel):
    items: List[SELEntryResponse]
    total: int
    page: int
    page_size: int


class SELAcknowledgeRequest(BaseModel):
    entry_ids: List[UUID]


# Firmware
class FirmwareInfoResponse(BaseModel):
    component: str
    current_version: str = ""
    available_version: Optional[str] = ""
    update_status: str = "up_to_date"
    component_id: Optional[str] = ""
    raw_data: Optional[Dict[str, Any]] = None


class FirmwareInventoryResponse(BaseModel):
    server_id: UUID
    firmware: List[FirmwareInfoResponse]
    timestamp: datetime


# Hardware Detail
class ProcessorResponse(BaseModel):
    id: str
    name: str = ""
    model: str = ""
    cores: int = 0
    threads: int = 0
    speed_ghz: float = 0
    status: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class MemoryModuleResponse(BaseModel):
    id: str
    name: str = ""
    capacity_mb: int = 0
    speed_mhz: int = 0
    type: str = ""
    status: str = ""
    manufacturer: str = ""
    serial: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class NetworkAdapterResponse(BaseModel):
    id: str
    name: str = ""
    mac_address: str = ""
    link_status: str = "unknown"
    speed_mbps: int = 0
    raw_data: Optional[Dict[str, Any]] = None


class StorageControllerResponse(BaseModel):
    id: str
    name: str = ""
    model: str = ""
    firmware_version: str = ""
    status: str = ""
    drives: List[Dict[str, Any]] = []
    raw_data: Optional[Dict[str, Any]] = None


class PowerSupplyResponse(BaseModel):
    id: str
    name: str = ""
    status: str = ""
    input_watts: Optional[float] = None
    output_watts: Optional[float] = None
    capacity_watts: Optional[float] = None
    model: str = ""
    serial: str = ""
    raw_data: Optional[Dict[str, Any]] = None


class FanResponse(BaseModel):
    id: str
    name: str = ""
    status: str = ""
    reading_rpm: Optional[float] = None
    reading_percent: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class HardwareDetailResponse(BaseModel):
    server_id: UUID
    system_info: SystemInfoResponse
    processors: List[ProcessorResponse]
    memory: List[MemoryModuleResponse]
    network_adapters: List[NetworkAdapterResponse]
    storage_controllers: List[StorageControllerResponse]
    power_supplies: List[PowerSupplyResponse]
    fans: List[FanResponse]
    timestamp: datetime


# KVM
class KVMStartRequest(BaseModel):
    duration_minutes: int = Field(default=60, ge=5, le=480)


class KVMStartResponse(BaseModel):
    session_id: UUID
    proxy_token: str
    proxy_url: str
    expires_at: datetime


class KVMSessionResponse(BaseModel):
    id: UUID
    server_id: UUID
    user_id: Optional[UUID] = None
    status: str
    started_at: datetime
    expires_at: datetime
    ended_at: Optional[datetime]
    client_ip: Optional[str]

    class Config:
        from_attributes = True


# Bulk operations
class BulkPowerActionRequest(BaseModel):
    server_ids: List[UUID]
    action: str = Field(..., pattern="^(on|off|graceful_off|force_off|restart|graceful_restart|force_restart)$")


class BulkPowerActionResponse(BaseModel):
    results: List[Dict[str, Any]]
    success_count: int
    failed_count: int
