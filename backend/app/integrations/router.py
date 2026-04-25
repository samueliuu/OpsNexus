from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db as get_session
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.integrations.netbox_client import NetBoxClient
from app.integrations.netbox_sync import NetBoxSyncService

logger = get_logger(__name__)

router = APIRouter(prefix="/netbox", tags=["NetBox Integration"])


def _check_netbox_enabled():
    if not settings.netbox_sync_enabled:
        raise ValueError("NetBox integration is not enabled. Set NETBOX_SYNC_ENABLED=true to enable.")


@router.get("/status")
async def get_netbox_status(
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    async with NetBoxClient() as client:
        healthy = await client.health_check()
        return {
            "connected": healthy,
            "api_url": settings.netbox_api_url,
            "sync_enabled": settings.netbox_sync_enabled,
        }


@router.post("/sync/from-netbox")
async def sync_from_netbox(
    site_id: Optional[int] = Query(None, description="NetBox site ID to filter"),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    service = NetBoxSyncService(session)
    result = await service.sync_from_netbox(site_id=site_id)
    return result


@router.post("/sync/to-netbox")
async def sync_to_netbox(
    server_ids: Optional[List[UUID]] = Query(None, description="Server IDs to push"),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    service = NetBoxSyncService(session)
    result = await service.sync_to_netbox(server_ids=server_ids)
    return result


@router.post("/sync/sites")
async def sync_sites_from_netbox(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    service = NetBoxSyncService(session)
    result = await service.sync_sites_from_netbox()
    return result


@router.get("/sites")
async def list_netbox_sites(
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    async with NetBoxClient() as client:
        sites = await client.get_sites()
        return {"sites": sites}


@router.get("/devices")
async def list_netbox_devices(
    site_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user=Depends(get_current_user),
):
    _check_netbox_enabled()
    async with NetBoxClient() as client:
        devices = await client.get_devices(site_id=site_id, role=role, limit=limit)
        return {"devices": devices, "count": len(devices)}
