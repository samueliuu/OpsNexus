from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# DataCenter schemas
class DataCenterBase(BaseModel):
    name: str = Field(..., max_length=128)
    code: str = Field(..., max_length=64)
    location: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=64)
    contact_phone: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = None
    is_active: bool = True


class DataCenterCreate(DataCenterBase):
    pass


class DataCenterUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    location: Optional[str] = Field(None, max_length=255)
    contact_name: Optional[str] = Field(None, max_length=64)
    contact_phone: Optional[str] = Field(None, max_length=32)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DataCenterResponse(DataCenterBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Rack schemas
class RackBase(BaseModel):
    data_center_id: UUID
    name: str = Field(..., max_length=64)
    code: str = Field(..., max_length=64)
    location: Optional[str] = Field(None, max_length=128)
    u_height: int = Field(default=42, ge=1, le=60)
    description: Optional[str] = None
    is_active: bool = True


class RackCreate(RackBase):
    pass


class RackUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    location: Optional[str] = Field(None, max_length=128)
    u_height: Optional[int] = Field(None, ge=1, le=60)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RackResponse(RackBase):
    id: UUID
    data_center: Optional[DataCenterResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# BMC Credential schemas
class BMCCredentialBase(BaseModel):
    username: str = Field(..., max_length=64)
    protocol: str = Field(default="redfish", pattern="^(redfish|ipmi|snmp)$")
    port: int = Field(default=443, ge=1, le=65535)


class BMCCredentialCreate(BMCCredentialBase):
    password: str = Field(..., min_length=1, max_length=128)


class BMCCredentialUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=64)
    password: Optional[str] = Field(None, min_length=1, max_length=128)
    protocol: Optional[str] = Field(None, pattern="^(redfish|ipmi|snmp)$")
    port: Optional[int] = Field(None, ge=1, le=65535)


class BMCCredentialResponse(BMCCredentialBase):
    id: UUID
    server_id: UUID
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Server schemas
class ServerBase(BaseModel):
    name: str = Field(..., max_length=128)
    hostname: Optional[str] = Field(None, max_length=128)
    serial_number: Optional[str] = Field(None, max_length=64)
    asset_tag: Optional[str] = Field(None, max_length=64)
    brand: str = Field(..., max_length=32)
    model: str = Field(..., max_length=64)
    server_type: str = Field(default="physical", pattern="^(physical|virtual|blade)$")
    rack_id: Optional[UUID] = None
    rack_position: Optional[int] = Field(None, ge=1, le=60)
    rack_height: int = Field(default=1, ge=1, le=10)
    owner_id: Optional[UUID] = None
    department: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None


class ServerHardwareInfo(BaseModel):
    cpu_model: Optional[str] = Field(None, max_length=128)
    cpu_count: int = Field(default=0, ge=0)
    cpu_cores_per_socket: int = Field(default=0, ge=0)
    memory_gb: int = Field(default=0, ge=0)
    disk_info: Optional[Dict[str, Any]] = None
    network_interfaces: Optional[List[Dict[str, Any]]] = None


class ServerSoftwareInfo(BaseModel):
    os_name: Optional[str] = Field(None, max_length=64)
    os_version: Optional[str] = Field(None, max_length=64)


class ServerBMCInfo(BaseModel):
    bmc_ip: Optional[str] = Field(None, max_length=64)
    bmc_mac: Optional[str] = Field(None, max_length=32)
    bmc_status: str = Field(default="unknown", pattern="^(online|offline|unknown|error)$")
    bmc_unreachable: bool = False
    bmc_unreachable_since: Optional[datetime] = None


class ServerCreate(ServerBase):
    hardware_info: Optional[ServerHardwareInfo] = None
    software_info: Optional[ServerSoftwareInfo] = None
    bmc_info: Optional[ServerBMCInfo] = None
    bmc_credential: Optional[BMCCredentialCreate] = None
    metadata: Optional[Dict[str, Any]] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    hostname: Optional[str] = Field(None, max_length=128)
    serial_number: Optional[str] = Field(None, max_length=64)
    asset_tag: Optional[str] = Field(None, max_length=64)
    rack_id: Optional[UUID] = None
    rack_position: Optional[int] = Field(None, ge=1, le=60)
    rack_height: Optional[int] = Field(None, ge=1, le=10)
    owner_id: Optional[UUID] = None
    department: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    hardware_info: Optional[ServerHardwareInfo] = None
    software_info: Optional[ServerSoftwareInfo] = None
    bmc_info: Optional[ServerBMCInfo] = None
    metadata: Optional[Dict[str, Any]] = None


class ServerResponse(ServerBase):
    id: UUID
    status: str
    hardware_info: ServerHardwareInfo
    software_info: ServerSoftwareInfo
    bmc_info: ServerBMCInfo
    rack: Optional[RackResponse] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle nested hardware/software/bmc info."""
        data = {
            "id": obj.id,
            "name": obj.name,
            "hostname": obj.hostname,
            "serial_number": obj.serial_number,
            "asset_tag": obj.asset_tag,
            "brand": obj.brand,
            "model": obj.model,
            "server_type": obj.server_type,
            "status": obj.status,
            "rack_id": obj.rack_id,
            "rack_position": obj.rack_position,
            "rack_height": obj.rack_height,
            "owner_id": obj.owner_id,
            "department": obj.department,
            "description": obj.description,
            "metadata": obj.extra_data,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "rack": obj.rack,
            "hardware_info": {
                "cpu_model": obj.cpu_model,
                "cpu_count": obj.cpu_count,
                "cpu_cores_per_socket": obj.cpu_cores_per_socket,
                "memory_gb": obj.memory_gb,
                "disk_info": obj.disk_info,
                "network_interfaces": obj.network_interfaces,
            },
            "software_info": {
                "os_name": obj.os_name,
                "os_version": obj.os_version,
            },
            "bmc_info": {
                "bmc_ip": obj.bmc_ip,
                "bmc_mac": obj.bmc_mac,
                "bmc_status": obj.bmc_status,
                "bmc_unreachable": obj.bmc_unreachable,
                "bmc_unreachable_since": obj.bmc_unreachable_since,
            },
        }
        return cls(**data)


class ServerListResponse(BaseModel):
    items: List[ServerResponse]
    total: int
    page: int
    page_size: int


class ServerFilter(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    status: Optional[str] = None
    data_center_id: Optional[UUID] = None
    rack_id: Optional[UUID] = None
    bmc_status: Optional[str] = None
    owner_id: Optional[UUID] = None
    department: Optional[str] = None
    search: Optional[str] = None


# Server bulk operations
class ServerBulkCreate(BaseModel):
    servers: List[ServerCreate]


class ServerBulkUpdate(BaseModel):
    server_ids: List[UUID]
    updates: Dict[str, Any]


class ServerBulkDelete(BaseModel):
    server_ids: List[UUID]


# Server import/export
class ServerImportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[Dict[str, str]]


class ServerExportRequest(BaseModel):
    server_ids: Optional[List[UUID]] = None
    filters: Optional[ServerFilter] = None
