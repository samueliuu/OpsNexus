from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.outband.schemas import (
    BMCConnectionTest,
    BMCConnectionTestResponse,
    BulkPowerActionRequest,
    BulkPowerActionResponse,
    FirmwareInventoryResponse,
    HardwareDetailResponse,
    KVMStartRequest,
    KVMStartResponse,
    KVMSessionResponse,
    PowerActionRequest,
    PowerActionResponse,
    PowerStateResponse,
    SELAcknowledgeRequest,
    SELLogListResponse,
    SensorDataListResponse,
    SystemInfoResponse,
)
from app.modules.outband.service import BMCService, KVMService, SELLogService
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.modules.system.models import User

router = APIRouter(prefix="/outband", tags=["OutBand"])

require_info_read = PermissionChecker("outband:info", "read")
require_power_execute = PermissionChecker("outband:power", "execute")
require_kvm_execute = PermissionChecker("outband:kvm", "execute")
require_sel_read = PermissionChecker("outband:sel", "read")
require_sel_write = PermissionChecker("outband:sel", "write")


# BMC Connection Test
@router.post("/test-connection", response_model=BMCConnectionTestResponse, dependencies=[Depends(require_info_read)])
async def test_bmc_connection(data: BMCConnectionTest, db=Depends(get_db)):
    """Test BMC connection without saving credentials."""
    service = BMCService(db)
    result = await service.test_connection(
        host=data.host,
        username=data.username,
        password=data.password,
        protocol=data.protocol,
        port=data.port,
    )
    return BMCConnectionTestResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        firmware_version=result.get("firmware_version"),
        detected_brand=result.get("detected_brand"),
        manufacturer=result.get("manufacturer"),
        model=result.get("model"),
        serial_number=result.get("serial_number"),
    )


# System Info
@router.get(
    "/servers/{server_id}/system-info",
    response_model=SystemInfoResponse,
    dependencies=[Depends(require_info_read)],
)
async def get_system_info(server_id: UUID, db=Depends(get_db)):
    """Get system information from BMC."""
    service = BMCService(db)
    info = await service.get_system_info(server_id)
    return SystemInfoResponse(
        manufacturer=info.manufacturer,
        model=info.model,
        serial_number=info.serial_number,
        sku=info.sku,
        bios_version=info.bios_version,
        bmc_version=info.bmc_version,
        bmc_ip=info.bmc_ip,
        hostname=info.hostname,
        power_state=info.power_state.value,
        health=info.health.value,
        processor_count=info.processor_count,
        processor_model=info.processor_model,
        memory_total_gb=info.memory_total_gb,
    )


# Power Control
@router.get(
    "/servers/{server_id}/power",
    response_model=PowerStateResponse,
    dependencies=[Depends(require_info_read)],
)
async def get_power_state(server_id: UUID, db=Depends(get_db)):
    """Get server power state."""
    service = BMCService(db)
    return await service.get_power_state(server_id)


@router.post(
    "/servers/{server_id}/power",
    response_model=PowerActionResponse,
    dependencies=[Depends(require_power_execute)],
)
async def set_power_action(server_id: UUID, data: PowerActionRequest, db=Depends(get_db)):
    """Execute power action on server."""
    service = BMCService(db)
    return await service.set_power_action(server_id, data.action)


@router.post(
    "/servers/bulk-power",
    response_model=BulkPowerActionResponse,
    dependencies=[Depends(require_power_execute)],
)
async def bulk_power_action(data: BulkPowerActionRequest, db=Depends(get_db)):
    """Execute power action on multiple servers."""
    service = BMCService(db)
    return await service.bulk_power_action(data.server_ids, data.action)


# Sensor Data
@router.get(
    "/servers/{server_id}/sensors",
    response_model=SensorDataListResponse,
    dependencies=[Depends(require_info_read)],
)
async def get_sensor_data(server_id: UUID, db=Depends(get_db)):
    """Get sensor data from BMC."""
    service = BMCService(db)
    return await service.get_sensor_data(server_id)


# SEL Logs
@router.get("/sel-logs", response_model=SELLogListResponse, dependencies=[Depends(require_sel_read)])
async def list_sel_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    server_id: Optional[UUID] = None,
    severity: Optional[str] = None,
    is_acknowledged: Optional[bool] = None,
    db=Depends(get_db),
):
    """List SEL log entries."""
    service = SELLogService(db)
    entries, total = await service.list_sel_logs(
        server_id=server_id,
        severity=severity,
        is_acknowledged=is_acknowledged,
        skip=skip,
        limit=limit,
    )
    return SELLogListResponse(
        items=entries,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.post(
    "/sel-logs/acknowledge",
    dependencies=[Depends(require_sel_write)],
)
async def acknowledge_sel_entries(
    data: SELAcknowledgeRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    """Acknowledge SEL log entries."""
    service = SELLogService(db)
    count = await service.acknowledge_entries(data.entry_ids, current_user.id)
    return {"acknowledged": count}


# Firmware Inventory
@router.get(
    "/servers/{server_id}/firmware",
    response_model=FirmwareInventoryResponse,
    dependencies=[Depends(require_info_read)],
)
async def get_firmware_inventory(server_id: UUID, db=Depends(get_db)):
    """Get firmware inventory from BMC."""
    service = BMCService(db)
    return await service.get_firmware_inventory(server_id)


# Hardware Detail
@router.get(
    "/servers/{server_id}/hardware",
    response_model=HardwareDetailResponse,
    dependencies=[Depends(require_info_read)],
)
async def get_hardware_detail(server_id: UUID, db=Depends(get_db)):
    """Get full hardware detail from BMC."""
    service = BMCService(db)
    return await service.get_hardware_detail(server_id)


# KVM Sessions
@router.post(
    "/servers/{server_id}/kvm",
    response_model=KVMStartResponse,
    dependencies=[Depends(require_kvm_execute)],
)
async def start_kvm_session(
    server_id: UUID,
    data: KVMStartRequest,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    """Start KVM session."""
    service = KVMService(db)
    session = await service.start_session(
        server_id=server_id,
        user_id=current_user.id,
        duration_minutes=data.duration_minutes,
    )
    return KVMStartResponse(
        session_id=session.id,
        proxy_token=session.proxy_token,
        proxy_url=f"/api/v1/outband/kvm-proxy/{session.proxy_token}",
        expires_at=session.expires_at,
    )


@router.delete(
    "/kvm/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_kvm_execute)],
)
async def terminate_kvm_session(session_id: UUID, db=Depends(get_db)):
    """Terminate KVM session."""
    service = KVMService(db)
    await service.terminate_session(session_id)
    return None


@router.get("/kvm-sessions", response_model=List[KVMSessionResponse], dependencies=[Depends(require_kvm_execute)])
async def list_kvm_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    server_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db=Depends(get_db),
):
    """List KVM sessions."""
    service = KVMService(db)
    sessions, _ = await service.list_sessions(server_id, status, skip, limit)
    return sessions


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "outband",
        "version": settings.app_version,
    }
