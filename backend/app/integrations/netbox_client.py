from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NetBoxClient:
    """Async client for NetBox DCIM API.

    Provides methods to query and sync server/asset data from NetBox.
    NetBox serves as the Source of Truth for asset inventory.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        self.api_url = (api_url or settings.netbox_api_url).rstrip("/")
        self.api_token = api_token or settings.netbox_api_token
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        if self._client:
            return

        self._client = httpx.AsyncClient(
            base_url=f"{self.api_url}/api",
            headers={
                "Authorization": f"Token {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
            verify=self.verify_ssl,
            follow_redirects=True,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        if not self._client:
            await self.connect()

        response = await self._client.request(method, path, **kwargs)

        if response.status_code == 401:
            raise PermissionError("NetBox API authentication failed")
        if response.status_code == 404:
            raise ValueError(f"NetBox resource not found: {path}")
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(f"NetBox API error: {response.status_code} - {response.text[:200]}")

        try:
            return response.json() if response.content else {}
        except Exception:
            return {}

    async def _get_paginated(self, path: str, params: Optional[Dict] = None, limit: int = 0) -> List[Dict[str, Any]]:
        results = []
        params = params or {}
        params["limit"] = 50
        offset = 0

        while True:
            params["offset"] = offset
            data = await self._request("GET", path, params=params)
            results.extend(data.get("results", []))

            if not data.get("next") or (limit and len(results) >= limit):
                break
            offset += 50

        return results[:limit] if limit else results

    async def health_check(self) -> bool:
        try:
            await self.connect()
            await self._request("GET", "/status/")
            return True
        except Exception as e:
            logger.warning(f"NetBox health check failed: {e}")
            return False

    async def get_sites(self) -> List[Dict[str, Any]]:
        return await self._get_paginated("/dcim/sites/")

    async def get_site(self, site_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/dcim/sites/{site_id}/")

    async def get_racks(self, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if site_id:
            params["site_id"] = site_id
        return await self._get_paginated("/dcim/racks/", params=params)

    async def get_devices(
        self,
        site_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 0,
    ) -> List[Dict[str, Any]]:
        params = {}
        if site_id:
            params["site_id"] = site_id
        if role:
            params["role"] = role
        if status:
            params["status"] = status
        return await self._get_paginated("/dcim/devices/", params=params, limit=limit)

    async def get_device(self, device_id: int) -> Dict[str, Any]:
        return await self._request("GET", f"/dcim/devices/{device_id}/")

    async def get_device_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        results = await self._get_paginated("/dcim/devices/", params={"name": name}, limit=1)
        return results[0] if results else None

    async def get_device_by_serial(self, serial: str) -> Optional[Dict[str, Any]]:
        results = await self._get_paginated("/dcim/devices/", params={"serial": serial}, limit=1)
        return results[0] if results else None

    async def get_manufacturers(self) -> List[Dict[str, Any]]:
        return await self._get_paginated("/dcim/manufacturers/")

    async def get_device_types(self, manufacturer_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if manufacturer_id:
            params["manufacturer_id"] = manufacturer_id
        return await self._get_paginated("/dcim/device-types/", params=params)

    async def get_interfaces(self, device_id: int) -> List[Dict[str, Any]]:
        return await self._get_paginated("/dcim/interfaces/", params={"device_id": device_id})

    async def get_ip_addresses(self, device_id: Optional[int] = None) -> List[Dict[str, Any]]:
        params = {}
        if device_id:
            params["device_id"] = device_id
        return await self._get_paginated("/ipam/ip-addresses/", params=params)

    async def create_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/dcim/devices/", json=data)

    async def update_device(self, device_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("PATCH", f"/dcim/devices/{device_id}/", json=data)

    async def get_tags(self) -> List[Dict[str, Any]]:
        return await self._get_paginated("/extras/tags/")

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
