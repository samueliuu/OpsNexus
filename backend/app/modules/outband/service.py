import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import AdapterRegistry, BMCConnection, PowerAction
from app.core.cache import Cache, DistributedLock, get_redis
from app.core.config import settings
from app.core.exceptions import (
    BMCConnectionException,
    NotFoundException,
    ValidationException,
)
from app.core.security import decrypt_value
from app.core.logging import get_logger
from app.modules.asset.models import BMCCredential, Server
from app.modules.asset.repository import BMCCredentialRepository, ServerRepository
from app.modules.outband.models import FirmwareInventory, KVMSession, SELLog

logger = get_logger(__name__)


class BMCService:
    """Core BMC communication service."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.server_repo = ServerRepository(session)
        self.credential_repo = BMCCredentialRepository(session)

    async def _get_adapter(self, server_id: UUID):
        """Get adapter instance for a server."""
        server = await self.server_repo.get_by_id(server_id)
        if not server:
            raise NotFoundException("Server", str(server_id))

        if not server.bmc_ip:
            raise ValidationException(f"Server '{server.name}' has no BMC IP configured")

        credential = await self.credential_repo.get_by_server_id(server_id)
        if not credential:
            raise ValidationException(f"Server '{server.name}' has no BMC credentials configured")

        connection = BMCConnection(
            host=server.bmc_ip,
            username=credential.username,
            password=decrypt_value(credential.encrypted_password),
            protocol=credential.protocol,
            port=credential.port,
            verify_ssl=False,
            timeout=settings.bmc_connect_timeout,
        )

        adapter = AdapterRegistry.create(server.brand, connection)
        return adapter, server

    async def test_connection(
        self, host: str, username: str, password: str, protocol: str = "redfish", port: int = 443
    ) -> Dict[str, Any]:
        connection = BMCConnection(
            host=host, username=username, password=password,
            protocol=protocol, port=port, verify_ssl=False,
        )

        client = None
        try:
            from app.adapters.base.redfish import RedfishClient
            client = RedfishClient(connection)
            await client.connect()

            system_data = await client.get("/redfish/v1/Systems")
            members = system_data.get("Members", [])
            if members:
                system_url = members[0].get("@odata.id", "")
                if system_url:
                    system = await client.get(system_url)
                    manufacturer = system.get("Manufacturer", "").lower()

                    brand_map = {
                        "dell": "dell", "hpe": "hpe", "hp": "hpe",
                        "lenovo": "lenovo", "huawei": "huawei", "inspur": "inspur",
                        "h3c": "h3c", "sugon": "sugon", "xfusion": "xfusion",
                    }
                    detected_brand = brand_map.get(manufacturer, "generic")

                    bmc_version = ""
                    try:
                        managers = await client.get("/redfish/v1/Managers")
                        mgr_members = managers.get("Members", [])
                        if mgr_members:
                            mgr_url = mgr_members[0].get("@odata.id", "")
                            if mgr_url:
                                manager_data = await client.get(mgr_url)
                                bmc_version = manager_data.get("FirmwareVersion", "")
                    except Exception:
                        pass

                    return {
                        "success": True,
                        "message": "Connection successful",
                        "detected_brand": detected_brand,
                        "manufacturer": system.get("Manufacturer", ""),
                        "model": system.get("Model", ""),
                        "serial_number": system.get("SerialNumber", ""),
                        "firmware_version": bmc_version,
                    }

            return {"success": True, "message": "Connection successful but no system data found"}

        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}
        finally:
            if client:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    async def get_system_info(self, server_id: UUID) -> Dict[str, Any]:
        """Get system info from BMC."""
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            info = await adapter.get_system_info()

            # Update server info in database
            update_data = {}
            if info.serial_number and not server.serial_number:
                update_data["serial_number"] = info.serial_number
            if info.model and server.model == "Unknown":
                update_data["model"] = info.model
            if info.hostname and not server.hostname:
                update_data["hostname"] = info.hostname
            if info.processor_model:
                update_data["cpu_model"] = info.processor_model
            if info.processor_count:
                update_data["cpu_count"] = info.processor_count
            if info.memory_total_gb:
                update_data["memory_gb"] = int(info.memory_total_gb)
            update_data["bmc_status"] = "online"

            if update_data:
                await self.server_repo.update(server_id, **update_data)

            return info

    async def get_power_state(self, server_id: UUID) -> Dict[str, Any]:
        """Get power state from BMC."""
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            power_state = await adapter.get_power_state()

            # Update BMC status
            await self.server_repo.update(server_id, bmc_status="online")

            return {
                "server_id": server_id,
                "power_state": power_state.value,
                "timestamp": datetime.now(timezone.utc),
            }

    async def set_power_action(self, server_id: UUID, action: str) -> Dict[str, Any]:
        try:
            power_action = PowerAction(action)
        except ValueError:
            raise ValidationException(f"Invalid power action: {action}")

        redis = await get_redis()
        lock = DistributedLock(redis, f"server_power:{server_id}", timeout=60)

        async with lock:
            adapter, server = await self._get_adapter(server_id)

            async with adapter:
                previous_state = await adapter.get_power_state()

                current_state = await adapter.set_power_action(power_action)

                await self.server_repo.update(server_id, bmc_status="online")

                return {
                    "server_id": server_id,
                    "action": action,
                    "previous_state": previous_state.value,
                    "current_state": current_state.value,
                    "timestamp": datetime.now(timezone.utc),
                }

    async def get_sensor_data(self, server_id: UUID) -> Dict[str, Any]:
        """Get sensor data from BMC."""
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            sensors = await adapter.get_sensor_data()

            # Update BMC status
            await self.server_repo.update(server_id, bmc_status="online")

            return {
                "server_id": server_id,
                "sensors": [
                    {
                        "name": s.name,
                        "reading": s.reading,
                        "unit": s.unit,
                        "status": s.status.value,
                        "sensor_type": s.sensor_type,
                        "lower_threshold_critical": s.lower_threshold_critical,
                        "upper_threshold_critical": s.upper_threshold_critical,
                    }
                    for s in sensors
                ],
                "timestamp": datetime.now(timezone.utc),
            }

    async def get_sel_logs(self, server_id: UUID, limit: int = 100) -> List[Dict[str, Any]]:
        if limit < 1:
            limit = 1
        elif limit > 500:
            limit = 500
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            entries = await adapter.get_sel_logs(limit)

            # Update BMC status
            await self.server_repo.update(server_id, bmc_status="online")

            return [
                {
                    "record_id": e.record_id,
                    "timestamp": e.timestamp,
                    "sensor_type": e.sensor_type,
                    "sensor_name": e.sensor_name,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "description": e.description,
                }
                for e in entries
            ]

    async def get_firmware_inventory(self, server_id: UUID) -> Dict[str, Any]:
        """Get firmware inventory from BMC."""
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            firmware_list = await adapter.get_firmware_inventory()

            # Update firmware inventory in database
            for fw in firmware_list:
                existing = await self.session.execute(
                    select(FirmwareInventory).where(
                        FirmwareInventory.server_id == server_id,
                        FirmwareInventory.component == fw.component,
                    )
                )
                existing_fw = existing.scalar_one_or_none()

                if existing_fw:
                    await self.session.execute(
                        update(FirmwareInventory)
                        .where(FirmwareInventory.id == existing_fw.id)
                        .values(
                            current_version=fw.current_version,
                            available_version=fw.available_version,
                            update_status=fw.update_status,
                            last_checked_at=datetime.now(timezone.utc),
                        )
                    )
                else:
                    new_fw = FirmwareInventory(
                        id=uuid.uuid4(),
                        server_id=server_id,
                        component=fw.component,
                        component_id=fw.component_id,
                        current_version=fw.current_version,
                        available_version=fw.available_version,
                        update_status=fw.update_status,
                    )
                    self.session.add(new_fw)

            await self.session.flush()

            # Update BMC status
            await self.server_repo.update(server_id, bmc_status="online")

            return {
                "server_id": server_id,
                "firmware": [
                    {
                        "component": f.component,
                        "current_version": f.current_version,
                        "available_version": f.available_version,
                        "update_status": f.update_status,
                        "component_id": f.component_id,
                    }
                    for f in firmware_list
                ],
                "timestamp": datetime.now(timezone.utc),
            }

    async def get_hardware_detail(self, server_id: UUID) -> Dict[str, Any]:
        """Get full hardware detail from BMC."""
        adapter, server = await self._get_adapter(server_id)

        async with adapter:
            system_info, processors, memory, network, storage, power, fans = await asyncio.gather(
                adapter.get_system_info(),
                adapter.get_processors(),
                adapter.get_memory(),
                adapter.get_network_adapters(),
                adapter.get_storage_controllers(),
                adapter.get_power_supplies(),
                adapter.get_fans(),
            )

            # Update BMC status
            await self.server_repo.update(server_id, bmc_status="online")

            return {
                "server_id": server_id,
                "system_info": {
                    "manufacturer": system_info.manufacturer,
                    "model": system_info.model,
                    "serial_number": system_info.serial_number,
                    "bios_version": system_info.bios_version,
                    "bmc_version": system_info.bmc_version,
                    "power_state": system_info.power_state.value,
                    "health": system_info.health.value,
                },
                "processors": [
                    {"id": p.id, "name": p.name, "model": p.model, "cores": p.cores,
                     "threads": p.threads, "speed_ghz": p.speed_ghz, "status": p.status.value}
                    for p in processors
                ],
                "memory": [
                    {"id": m.id, "name": m.name, "capacity_mb": m.capacity_mb,
                     "speed_mhz": m.speed_mhz, "type": m.type, "status": m.status.value,
                     "manufacturer": m.manufacturer}
                    for m in memory
                ],
                "network_adapters": [
                    {"id": n.id, "name": n.name, "mac_address": n.mac_address,
                     "link_status": n.link_status, "speed_mbps": n.speed_mbps}
                    for n in network
                ],
                "storage_controllers": [
                    {"id": s.id, "name": s.name, "status": s.status.value, "drives": s.drives}
                    for s in storage
                ],
                "power_supplies": [
                    {"id": p.id, "name": p.name, "status": p.status.value,
                     "output_watts": p.output_watts, "capacity_watts": p.capacity_watts}
                    for p in power
                ],
                "fans": [
                    {"id": f.id, "name": f.name, "status": f.status.value,
                     "reading_rpm": f.reading_rpm, "reading_percent": f.reading_percent}
                    for f in fans
                ],
                "timestamp": datetime.now(timezone.utc),
            }

    async def bulk_power_action(
        self, server_ids: List[UUID], action: str
    ) -> Dict[str, Any]:
        """Execute power action on multiple servers."""
        results = []
        success_count = 0
        failed_count = 0

        for server_id in server_ids:
            try:
                result = await self.set_power_action(server_id, action)
                results.append({"server_id": str(server_id), "status": "success", "result": result})
                success_count += 1
            except Exception as e:
                results.append({"server_id": str(server_id), "status": "failed", "error": str(e)})
                failed_count += 1

        return {
            "results": results,
            "success_count": success_count,
            "failed_count": failed_count,
        }


class SELLogService:
    """SEL log management service."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_sel_logs(
        self,
        server_id: Optional[UUID] = None,
        severity: Optional[str] = None,
        is_acknowledged: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[SELLog], int]:
        query = select(SELLog)
        count_query = select(func.count(SELLog.id))

        if server_id:
            query = query.where(SELLog.server_id == server_id)
            count_query = count_query.where(SELLog.server_id == server_id)
        if severity:
            query = query.where(SELLog.severity == severity)
            count_query = count_query.where(SELLog.severity == severity)
        if is_acknowledged is not None:
            query = query.where(SELLog.is_acknowledged == is_acknowledged)
            count_query = count_query.where(SELLog.is_acknowledged == is_acknowledged)

        query = query.order_by(SELLog.timestamp.desc())

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def acknowledge_entries(self, entry_ids: List[UUID], user_id: UUID) -> int:
        if not entry_ids:
            return 0
        result = await self.session.execute(
            update(SELLog)
            .where(SELLog.id.in_(entry_ids), SELLog.is_acknowledged == False)
            .values(is_acknowledged=True, acknowledged_by=user_id, acknowledged_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
        return result.rowcount


class KVMService:
    """KVM session management service."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_session(
        self, server_id: UUID, user_id: UUID, duration_minutes: int = 60
    ) -> KVMSession:
        server_result = await self.session.execute(
            select(Server).where(Server.id == server_id)
        )
        server = server_result.scalar_one_or_none()
        if not server:
            raise NotFoundException("Server", str(server_id))

        if duration_minutes < 5:
            duration_minutes = 5
        elif duration_minutes > 480:
            duration_minutes = 480

        result = await self.session.execute(
            select(KVMSession).where(
                KVMSession.server_id == server_id,
                KVMSession.status == "active",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.status = "terminated"
            existing.ended_at = datetime.now(timezone.utc)
            await Cache.delete(f"kvm_token:{existing.proxy_token}")

        proxy_token = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        kvm_session = KVMSession(
            id=uuid.uuid4(),
            server_id=server_id,
            user_id=user_id,
            proxy_token=proxy_token,
            status="active",
            started_at=now,
            expires_at=now + timedelta(minutes=duration_minutes),
        )
        self.session.add(kvm_session)
        await self.session.flush()
        await self.session.refresh(kvm_session)

        await Cache.set(
            f"kvm_token:{proxy_token}",
            str(kvm_session.id),
            expire=duration_minutes * 60,
        )

        return kvm_session

    async def terminate_session(self, session_id: UUID) -> bool:
        result = await self.session.execute(
            select(KVMSession).where(KVMSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundException("KVMSession", str(session_id))

        session.status = "terminated"
        session.ended_at = datetime.now(timezone.utc)

        # Remove from Redis
        await Cache.delete(f"kvm_token:{session.proxy_token}")

        await self.session.flush()
        return True

    async def list_sessions(
        self,
        server_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[KVMSession], int]:
        query = select(KVMSession)
        count_query = select(func.count(KVMSession.id))

        if server_id:
            query = query.where(KVMSession.server_id == server_id)
            count_query = count_query.where(KVMSession.server_id == server_id)
        if status:
            query = query.where(KVMSession.status == status)
            count_query = count_query.where(KVMSession.status == status)

        query = query.order_by(KVMSession.started_at.desc())

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def validate_proxy_token(self, proxy_token: str) -> Optional[KVMSession]:
        """Validate KVM proxy token."""
        session_id = await Cache.get(f"kvm_token:{proxy_token}")
        if not session_id:
            return None

        try:
            parsed_id = UUID(session_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid session ID in cache for token: {proxy_token}")
            await Cache.delete(f"kvm_token:{proxy_token}")
            return None

        result = await self.session.execute(
            select(KVMSession).where(KVMSession.id == parsed_id)
        )
        kvm_session = result.scalar_one_or_none()

        if not kvm_session or kvm_session.status != "active":
            return None

        if kvm_session.expires_at and kvm_session.expires_at < datetime.now(timezone.utc):
            kvm_session.status = "expired"
            await self.session.flush()
            await Cache.delete(f"kvm_token:{proxy_token}")
            return None

        return kvm_session
