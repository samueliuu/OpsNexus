import asyncio
from typing import Any, Dict, Optional

import httpx
import redfish as dmtf_redfish
from redfish.rest.v1 import InvalidCredentialsError, SessionCreationError

from app.adapters.base.types import BMCConnection
from app.core.exceptions import BMCAuthenticationException, BMCConnectionException
from app.core.logging import get_logger

logger = get_logger(__name__)

REDFISH_POWER_ACTIONS = {
    "on": "On",
    "off": "ForceOff",
    "graceful_off": "GracefulShutdown",
    "force_off": "ForceOff",
    "restart": "ForceRestart",
    "graceful_restart": "GracefulRestart",
    "force_restart": "ForceRestart",
    "nmi": "Nmi",
}

REDFISH_POWER_STATE_MAP = {
    "On": "on",
    "Off": "off",
    "PoweringOn": "powering_on",
    "PoweringOff": "powering_off",
    "Paused": "unknown",
}


class RedfishClient:
    """Redfish API client backed by DMTF python-redfish-library.

    Uses DMTF official library for session management, authentication,
    and retry logic. Async interface via asyncio.to_thread().
    Uses httpx AsyncClient with DMTF session token for concurrent operations.
    """

    def __init__(self, connection: BMCConnection):
        host = connection.host
        if host.startswith("https://"):
            host = host[len("https://"):]
        elif host.startswith("http://"):
            host = host[len("http://"):]

        self.base_url = f"https://{host}:{connection.port}"
        self.username = connection.username
        self.password = connection.password
        self.verify_ssl = connection.verify_ssl
        self.timeout = connection.timeout
        self._dmtf_client = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._auth_token: Optional[str] = None
        self._session_url: Optional[str] = None

    async def connect(self) -> None:
        if self._dmtf_client:
            await self.disconnect()

        try:
            ssl_kwargs = {}
            if not self.verify_ssl:
                ssl_kwargs["cafile"] = ""
                ssl_kwargs["capath"] = ""

            self._dmtf_client = await asyncio.to_thread(
                dmtf_redfish.redfish_client,
                base_url=self.base_url,
                username=self.username,
                password=self.password,
                default_prefix="/redfish/v1/",
                max_retry=3,
                timeout=self.timeout,
                check_connectivity=False,
                **ssl_kwargs,
            )

            if not self.verify_ssl:
                try:
                    import urllib3
                    from requests.adapters import HTTPAdapter

                    class NoVerifyAdapter(HTTPAdapter):
                        def init_poolmanager(self, *args, **kwargs):
                            kwargs["cert_reqs"] = "CERT_NONE"
                            kwargs["check_hostname"] = False
                            super().init_poolmanager(*args, **kwargs)

                    self._dmtf_client._conn.adapters["https://"] = NoVerifyAdapter()
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                except Exception as e:
                    logger.debug(f"Failed to disable SSL verification for DMTF client: {e}")

            await asyncio.to_thread(self._dmtf_client.login, auth="session")

            self._auth_token = self._dmtf_client.get_session_key()
            self._session_url = self._dmtf_client.get_session_location()

            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                verify=self.verify_ssl,
                timeout=self.timeout,
                follow_redirects=True,
            )

            logger.debug(
                f"Connected to BMC at {self.base_url}, "
                f"async channel={'active' if self._auth_token else 'unavailable'}"
            )

        except InvalidCredentialsError as e:
            raise BMCAuthenticationException(f"Invalid BMC credentials: {e}")
        except SessionCreationError as e:
            raise BMCAuthenticationException(f"BMC session creation failed: {e}")
        except (BMCAuthenticationException, BMCConnectionException):
            raise
        except Exception as e:
            raise BMCConnectionException(f"Failed to connect to BMC: {e}")

    async def disconnect(self) -> None:
        if self._dmtf_client:
            try:
                await asyncio.to_thread(self._dmtf_client.logout)
            except Exception as e:
                logger.warning(f"Failed to logout from BMC session: {e}")
            self._dmtf_client = None

        if self._async_client:
            try:
                await self._async_client.aclose()
            except Exception:
                pass
            self._async_client = None

        self._auth_token = None
        self._session_url = None

    async def get(self, path: str) -> Dict[str, Any]:
        if self._async_client and self._auth_token:
            return await self._async_get(path)
        return await self._dmtf_get(path)

    async def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._async_client and self._auth_token:
            return await self._async_post(path, data)
        return await self._dmtf_post(path, data)

    async def patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if self._async_client and self._auth_token:
            return await self._async_patch(path, data)
        return await self._dmtf_patch(path, data)

    async def _async_get(self, path: str) -> Dict[str, Any]:
        if not self._async_client:
            raise BMCConnectionException("Not connected")

        headers = {"X-Auth-Token": self._auth_token} if self._auth_token else {}
        response = await self._async_client.get(path, headers=headers)

        if response.status_code == 401:
            raise BMCAuthenticationException("Session expired")
        if response.status_code == 404:
            raise BMCConnectionException(f"Resource not found: {path}")
        if response.status_code not in (200, 202):
            raise BMCConnectionException(f"Redfish API error: {response.status_code}")

        try:
            return response.json()
        except Exception as e:
            raise BMCConnectionException(f"Invalid JSON response from {path}: {e}")

    async def _async_post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._async_client:
            raise BMCConnectionException("Not connected")

        headers = {"X-Auth-Token": self._auth_token} if self._auth_token else {}
        response = await self._async_client.post(path, json=data, headers=headers)

        if response.status_code == 401:
            raise BMCAuthenticationException("Session expired")
        if response.status_code == 404:
            raise BMCConnectionException(f"Resource not found: {path}")
        if response.status_code not in (200, 201, 202, 204):
            raise BMCConnectionException(
                f"Redfish POST error: {response.status_code} - {response.text[:200]}"
            )

        try:
            return response.json() if response.content else {}
        except Exception:
            return {}

    async def _async_patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._async_client:
            raise BMCConnectionException("Not connected")

        headers = {"X-Auth-Token": self._auth_token} if self._auth_token else {}
        response = await self._async_client.patch(path, json=data, headers=headers)

        if response.status_code == 401:
            raise BMCAuthenticationException("Session expired")
        if response.status_code == 404:
            raise BMCConnectionException(f"Resource not found: {path}")
        if response.status_code not in (200, 202, 204):
            raise BMCConnectionException(
                f"Redfish PATCH error: {response.status_code} - {response.text[:200]}"
            )

        try:
            return response.json() if response.content else {}
        except Exception:
            return {}

    async def _dmtf_get(self, path: str) -> Dict[str, Any]:
        if not self._dmtf_client:
            raise BMCConnectionException("Not connected")

        try:
            response = await asyncio.to_thread(self._dmtf_client.get, path)
            if response.status == 401:
                raise BMCAuthenticationException("Session expired")
            if response.status == 404:
                raise BMCConnectionException(f"Resource not found: {path}")
            if response.status not in (200, 202):
                raise BMCConnectionException(f"Redfish API error: {response.status}")
            return response.dict if hasattr(response, "dict") else {}
        except (BMCAuthenticationException, BMCConnectionException):
            raise
        except Exception as e:
            raise BMCConnectionException(f"DMTF Redfish GET error: {e}")

    async def _dmtf_post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._dmtf_client:
            raise BMCConnectionException("Not connected")

        try:
            response = await asyncio.to_thread(self._dmtf_client.post, path, body=data)
            if response.status == 401:
                raise BMCAuthenticationException("Session expired")
            if response.status == 404:
                raise BMCConnectionException(f"Resource not found: {path}")
            if response.status not in (200, 201, 202, 204):
                raise BMCConnectionException(f"Redfish POST error: {response.status}")
            return response.dict if hasattr(response, "dict") and response.dict else {}
        except (BMCAuthenticationException, BMCConnectionException):
            raise
        except Exception as e:
            raise BMCConnectionException(f"DMTF Redfish POST error: {e}")

    async def _dmtf_patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._dmtf_client:
            raise BMCConnectionException("Not connected")

        try:
            response = await asyncio.to_thread(self._dmtf_client.patch, path, body=data)
            if response.status == 401:
                raise BMCAuthenticationException("Session expired")
            if response.status == 404:
                raise BMCConnectionException(f"Resource not found: {path}")
            if response.status not in (200, 202, 204):
                raise BMCConnectionException(f"Redfish PATCH error: {response.status}")
            return response.dict if hasattr(response, "dict") and response.dict else {}
        except (BMCAuthenticationException, BMCConnectionException):
            raise
        except Exception as e:
            raise BMCConnectionException(f"DMTF Redfish PATCH error: {e}")
