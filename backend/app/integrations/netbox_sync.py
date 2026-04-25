from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.netbox_client import NetBoxClient
from app.modules.asset.models import DataCenter, Server
from app.modules.asset.repository import DataCenterRepository, RackRepository, ServerRepository

logger = get_logger(__name__)

MANUFACTURER_MAP = {
    "dell": "Dell",
    "dell inc.": "Dell",
    "hpe": "HPE",
    "hewlett packard enterprise": "HPE",
    "hp": "HPE",
    "huawei": "Huawei",
    "lenovo": "Lenovo",
    "h3c": "H3C",
    "new h3c": "H3C",
    "inspur": "Inspur",
    "sugon": "Sugon",
    "xfusion": "xFusion",
}


class NetBoxSyncService:
    """Service for syncing asset data between OpsNexus and NetBox.

    Sync direction:
    - NetBox → OpsNexus: Import devices from NetBox as servers
    - OpsNexus → NetBox: Push server data to NetBox as devices

    NetBox is the Source of Truth for site/rack topology.
    OpsNexus is the Source of Truth for BMC credentials and real-time status.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
        self.rack_repo = RackRepository(session)
        self.dc_repo = DataCenterRepository(session)

    def _get_netbox_client(self) -> NetBoxClient:
        if not settings.netbox_api_url or not settings.netbox_api_token:
            raise ValueError("NetBox API URL and token must be configured")
        return NetBoxClient(
            api_url=settings.netbox_api_url,
            api_token=settings.netbox_api_token,
            timeout=settings.netbox_timeout,
            verify_ssl=settings.netbox_verify_ssl,
        )

    async def sync_from_netbox(self, site_id: Optional[int] = None) -> Dict[str, Any]:
        """Import devices from NetBox into OpsNexus.

        Creates or updates Server records based on NetBox device data.
        """
        result = {"imported": 0, "updated": 0, "skipped": 0, "errors": []}

        async with self._get_netbox_client() as client:
            devices = await client.get_devices(site_id=site_id)

            for device in devices:
                try:
                    serial = device.get("serial", "")
                    name = device.get("name", "")
                    if not serial and not name:
                        result["skipped"] += 1
                        continue

                    existing = None
                    if serial:
                        existing = await self.server_repo.get_by_serial(serial)
                    if not existing and name:
                        try:
                            existing = await self.server_repo.get_by_hostname(name)
                        except Exception:
                            pass

                    device_data = self._map_netbox_device_to_server(device)

                    if existing:
                        update_kwargs = {}
                        for key, value in device_data.items():
                            if value is not None and getattr(existing, key, None) != value:
                                update_kwargs[key] = value
                        if update_kwargs:
                            await self.server_repo.update(existing.id, **update_kwargs)
                            result["updated"] += 1
                        else:
                            result["skipped"] += 1
                    else:
                        server = Server(id=__import__("uuid").uuid4(), **device_data)
                        await self.server_repo.create(server)
                        result["imported"] += 1

                except Exception as e:
                    result["errors"].append({
                        "device": device.get("name", "unknown"),
                        "error": str(e),
                    })
                    logger.warning(f"Failed to sync NetBox device {device.get('name')}: {e}")

        logger.info(f"NetBox sync complete: {result}")
        return result

    async def sync_to_netbox(self, server_ids: Optional[List[UUID]] = None) -> Dict[str, Any]:
        """Push OpsNexus server data to NetBox.

        Creates or updates NetBox devices based on OpsNexus Server records.
        """
        result = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

        async with self._get_netbox_client() as client:
            if server_ids:
                servers = []
                for sid in server_ids:
                    server = await self.server_repo.get_by_id(sid)
                    if server:
                        servers.append(server)
            else:
                servers, _ = await self.server_repo.list_servers(0, 1000)

            for server in servers:
                try:
                    if not server.serial_number and not server.hostname:
                        result["skipped"] += 1
                        continue

                    existing = None
                    if server.serial_number:
                        existing = await client.get_device_by_serial(server.serial_number)
                    if not existing and server.hostname:
                        existing = await client.get_device_by_name(server.hostname)

                    device_data = self._map_server_to_netbox_device(server)

                    if existing:
                        device_id = existing.get("id")
                        await client.update_device(device_id, device_data)
                        result["updated"] += 1
                    else:
                        await client.create_device(device_data)
                        result["created"] += 1

                except Exception as e:
                    result["errors"].append({
                        "server": str(server.id),
                        "name": server.name,
                        "error": str(e),
                    })
                    logger.warning(f"Failed to push server {server.name} to NetBox: {e}")

        logger.info(f"NetBox push complete: {result}")
        return result

    async def sync_sites_from_netbox(self) -> Dict[str, Any]:
        """Import sites from NetBox as DataCenters in OpsNexus."""
        result = {"imported": 0, "updated": 0, "errors": []}

        async with self._get_netbox_client() as client:
            sites = await client.get_sites()

            for site in sites:
                try:
                    code = site.get("slug", site.get("name", "")).lower()
                    existing = await self.dc_repo.get_by_code(code)

                    site_data = {
                        "name": site.get("name", ""),
                        "code": code,
                        "location": site.get("physical_address", "") or site.get("description", ""),
                        "description": site.get("comments", ""),
                        "is_active": site.get("status", {}).get("value") == "active",
                    }

                    if existing:
                        update_kwargs = {k: v for k, v in site_data.items() if v is not None}
                        if update_kwargs:
                            await self.dc_repo.update(existing.id, **update_kwargs)
                            result["updated"] += 1
                    else:
                        dc = DataCenter(id=__import__("uuid").uuid4(), **site_data)
                        await self.dc_repo.create(dc)
                        result["imported"] += 1

                except Exception as e:
                    result["errors"].append({
                        "site": site.get("name", "unknown"),
                        "error": str(e),
                    })

        return result

    @staticmethod
    def _map_netbox_device_to_server(device: Dict[str, Any]) -> Dict[str, Any]:
        manufacturer = device.get("manufacturer", {}).get("name", "")
        brand = "generic"
        for key, mapped in MANUFACTURER_MAP.items():
            if key in manufacturer.lower():
                brand = mapped.lower()
                break

        device_type = device.get("device_type", {})
        model = device_type.get("model", "")

        rack_info = device.get("rack", {})
        rack_id = None
        if rack_info:
            rack_id = rack_info.get("id")

        return {
            "name": device.get("name", ""),
            "hostname": device.get("name", ""),
            "serial_number": device.get("serial", "") or None,
            "asset_tag": device.get("asset_tag", "") or None,
            "brand": brand,
            "model": model,
            "status": device.get("status", {}).get("value", "active"),
            "rack_id": rack_id,
            "rack_position": device.get("position"),
            "description": device.get("comments", ""),
        }

    @staticmethod
    def _map_server_to_netbox_device(server: Server) -> Dict[str, Any]:
        data = {
            "name": server.hostname or server.name,
            "serial": server.serial_number or "",
            "asset_tag": server.asset_tag or "",
        }

        if server.brand:
            manufacturer_name = MANUFACTURER_MAP.get(server.brand.lower(), server.brand.title())
            data["manufacturer"] = {"name": manufacturer_name}

        if server.model:
            data["device_type"] = {"model": server.model}

        if server.bmc_ip:
            data["primary_ip4"] = server.bmc_ip

        if server.rack_position:
            data["position"] = server.rack_position

        return data
