from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.config import settings
from app.modules.asset.schemas import (
    BMCCredentialCreate,
    BMCCredentialResponse,
    BMCCredentialUpdate,
    DataCenterCreate,
    DataCenterResponse,
    DataCenterUpdate,
    RackCreate,
    RackResponse,
    RackUpdate,
    ServerBulkCreate,
    ServerBulkDelete,
    ServerBulkUpdate,
    ServerCreate,
    ServerFilter,
    ServerImportResult,
    ServerListResponse,
    ServerResponse,
    ServerUpdate,
)
from app.modules.asset.service import (
    BMCCredentialService,
    DataCenterService,
    RackService,
    ServerService,
)
from app.modules.system.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)

router = APIRouter(prefix="/asset", tags=["Asset"])

require_dc_read = PermissionChecker("asset:datacenter", "read")
require_dc_write = PermissionChecker("asset:datacenter", "write")
require_server_read = PermissionChecker("asset:server", "read")
require_server_write = PermissionChecker("asset:server", "write")


@router.get("/datacenters", response_model=List[DataCenterResponse], dependencies=[Depends(require_dc_read)])
async def list_datacenters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    is_active: Optional[bool] = None,
    db=Depends(get_db),
):
    """List data centers."""
    service = DataCenterService(db)
    datacenters, _ = await service.list_datacenters(skip, limit, is_active)
    return datacenters


@router.get("/datacenters/{dc_id}", response_model=DataCenterResponse, dependencies=[Depends(require_dc_read)])
async def get_datacenter(dc_id: UUID, db=Depends(get_db)):
    """Get data center by ID."""
    service = DataCenterService(db)
    return await service.get_datacenter(dc_id)


@router.post(
    "/datacenters",
    response_model=DataCenterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_dc_write)],
)
async def create_datacenter(data: DataCenterCreate, db=Depends(get_db)):
    """Create data center."""
    service = DataCenterService(db)
    return await service.create_datacenter(data)


@router.put(
    "/datacenters/{dc_id}",
    response_model=DataCenterResponse,
    dependencies=[Depends(require_dc_write)],
)
async def update_datacenter(dc_id: UUID, data: DataCenterUpdate, db=Depends(get_db)):
    """Update data center."""
    service = DataCenterService(db)
    return await service.update_datacenter(dc_id, data)


@router.delete(
    "/datacenters/{dc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_dc_write)],
)
async def delete_datacenter(dc_id: UUID, db=Depends(get_db)):
    """Delete data center."""
    service = DataCenterService(db)
    await service.delete_datacenter(dc_id)
    return None


# Rack endpoints
@router.get("/racks", response_model=List[RackResponse], dependencies=[Depends(require_dc_read)])
async def list_racks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    data_center_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    db=Depends(get_db),
):
    """List racks."""
    service = RackService(db)
    racks, _ = await service.list_racks(skip, limit, data_center_id, is_active)
    return racks


@router.get("/racks/{rack_id}", response_model=RackResponse, dependencies=[Depends(require_dc_read)])
async def get_rack(rack_id: UUID, db=Depends(get_db)):
    """Get rack by ID."""
    service = RackService(db)
    return await service.get_rack(rack_id)


@router.post(
    "/racks",
    response_model=RackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker("asset:datacenter", "write"))],
)
async def create_rack(data: RackCreate, db=Depends(get_db)):
    """Create rack."""
    service = RackService(db)
    return await service.create_rack(data)


@router.put(
    "/racks/{rack_id}",
    response_model=RackResponse,
    dependencies=[Depends(PermissionChecker("asset:datacenter", "write"))],
)
async def update_rack(rack_id: UUID, data: RackUpdate, db=Depends(get_db)):
    """Update rack."""
    service = RackService(db)
    return await service.update_rack(rack_id, data)


@router.delete(
    "/racks/{rack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker("asset:datacenter", "write"))],
)
async def delete_rack(rack_id: UUID, db=Depends(get_db)):
    """Delete rack."""
    service = RackService(db)
    await service.delete_rack(rack_id)
    return None


# Server endpoints
@router.get("/servers", response_model=ServerListResponse, dependencies=[Depends(require_server_read)])
async def list_servers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    brand: Optional[str] = None,
    model: Optional[str] = None,
    status: Optional[str] = None,
    data_center_id: Optional[UUID] = None,
    rack_id: Optional[UUID] = None,
    bmc_status: Optional[str] = None,
    owner_id: Optional[UUID] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
    db=Depends(get_db),
):
    """List servers with filters."""
    service = ServerService(db)
    filters = ServerFilter(
        brand=brand,
        model=model,
        status=status,
        data_center_id=data_center_id,
        rack_id=rack_id,
        bmc_status=bmc_status,
        owner_id=owner_id,
        department=department,
        search=search,
    )
    servers, total = await service.list_servers(skip, limit, filters)
    return ServerListResponse(
        items=[ServerResponse.from_orm(s) for s in servers],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/servers/{server_id}", response_model=ServerResponse, dependencies=[Depends(require_server_read)])
async def get_server(server_id: UUID, db=Depends(get_db)):
    """Get server by ID."""
    service = ServerService(db)
    server = await service.get_server(server_id)
    return ServerResponse.from_orm(server)


@router.post(
    "/servers",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_server_write)],
)
async def create_server(data: ServerCreate, db=Depends(get_db)):
    """Create server."""
    service = ServerService(db)
    server = await service.create_server(data)
    return ServerResponse.from_orm(server)


# Server bulk operations (MUST be before {server_id} routes)
@router.post(
    "/servers/bulk",
    response_model=ServerImportResult,
    dependencies=[Depends(require_server_write)],
)
async def bulk_create_servers(data: ServerBulkCreate, db=Depends(get_db)):
    """Bulk create servers."""
    service = ServerService(db)
    return await service.bulk_create_servers(data.servers)


@router.put(
    "/servers/bulk",
    dependencies=[Depends(require_server_write)],
)
async def bulk_update_servers(data: ServerBulkUpdate, db=Depends(get_db)):
    """Bulk update servers."""
    service = ServerService(db)
    count = await service.bulk_update_servers(data.server_ids, data.updates)
    return {"updated": count}


@router.delete(
    "/servers/bulk",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_server_write)],
)
async def bulk_delete_servers(data: ServerBulkDelete, db=Depends(get_db)):
    """Bulk delete servers."""
    service = ServerService(db)
    count = await service.bulk_delete_servers(data.server_ids)
    return {"deleted": count}


@router.put(
    "/servers/{server_id}",
    response_model=ServerResponse,
    dependencies=[Depends(require_server_write)],
)
async def update_server(server_id: UUID, data: ServerUpdate, db=Depends(get_db)):
    """Update server."""
    service = ServerService(db)
    server = await service.update_server(server_id, data)
    return ServerResponse.from_orm(server)


@router.delete(
    "/servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_server_write)],
)
async def delete_server(server_id: UUID, db=Depends(get_db)):
    """Delete server."""
    service = ServerService(db)
    await service.delete_server(server_id)
    return None


# BMC Credential endpoints
@router.get("/servers/{server_id}/bmc-credential", response_model=BMCCredentialResponse, dependencies=[Depends(require_server_read)])
async def get_bmc_credential(server_id: UUID, db=Depends(get_db)):
    """Get BMC credential for server."""
    service = BMCCredentialService(db)
    credential = await service.get_credential_by_server(server_id)
    return credential


@router.put(
    "/servers/{server_id}/bmc-credential",
    response_model=BMCCredentialResponse,
    dependencies=[Depends(require_server_write)],
)
async def update_bmc_credential(
    server_id: UUID, data: BMCCredentialUpdate, db=Depends(get_db)
):
    """Create or update BMC credential."""
    service = BMCCredentialService(db)
    return await service.create_or_update_credential(server_id, data)


@router.delete(
    "/bmc-credentials/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_server_write)],
)
async def delete_bmc_credential(credential_id: UUID, db=Depends(get_db)):
    """Delete BMC credential."""
    service = BMCCredentialService(db)
    await service.delete_credential(credential_id)
    return None


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "asset",
        "version": settings.app_version,
    }
