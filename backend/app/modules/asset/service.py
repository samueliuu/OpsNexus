import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from sqlalchemy.exc import IntegrityError
from app.core.security import encrypt_value
from app.modules.asset.models import BMCCredential, DataCenter, Rack, Server
from app.modules.asset.repository import (
    BMCCredentialRepository,
    DataCenterRepository,
    RackRepository,
    ServerRepository,
)
from app.modules.asset.schemas import (
    BMCCredentialCreate,
    BMCCredentialUpdate,
    DataCenterCreate,
    DataCenterUpdate,
    RackCreate,
    RackUpdate,
    ServerCreate,
    ServerFilter,
    ServerImportResult,
    ServerUpdate,
)


class DataCenterService:
    def __init__(self, session: AsyncSession):
        self.repo = DataCenterRepository(session)

    async def get_datacenter(self, dc_id: UUID) -> DataCenter:
        datacenter = await self.repo.get_by_id(dc_id)
        if not datacenter:
            raise NotFoundException("DataCenter", str(dc_id))
        return datacenter

    async def get_datacenter_by_code(self, code: str) -> DataCenter:
        datacenter = await self.repo.get_by_code(code)
        if not datacenter:
            raise NotFoundException("DataCenter", code)
        return datacenter

    async def list_datacenters(
        self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
    ) -> tuple[List[DataCenter], int]:
        return await self.repo.list_datacenters(skip, limit, is_active)

    async def create_datacenter(self, data: DataCenterCreate) -> DataCenter:
        datacenter = DataCenter(
            id=uuid.uuid4(),
            name=data.name,
            code=data.code,
            location=data.location,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            description=data.description,
            is_active=data.is_active,
        )
        try:
            return await self.repo.create(datacenter)
        except IntegrityError:
            raise ConflictException(f"DataCenter code '{data.code}' already exists")

    async def update_datacenter(self, dc_id: UUID, data: DataCenterUpdate) -> DataCenter:
        datacenter = await self.get_datacenter(dc_id)
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            return await self.repo.update(dc_id, **update_data)
        return datacenter

    async def delete_datacenter(self, dc_id: UUID) -> bool:
        await self.get_datacenter(dc_id)
        return await self.repo.delete(dc_id)


class RackService:
    def __init__(self, session: AsyncSession):
        self.repo = RackRepository(session)
        self.dc_repo = DataCenterRepository(session)

    async def get_rack(self, rack_id: UUID) -> Rack:
        rack = await self.repo.get_by_id(rack_id)
        if not rack:
            raise NotFoundException("Rack", str(rack_id))
        return rack

    async def list_racks(
        self,
        skip: int = 0,
        limit: int = 100,
        data_center_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Rack], int]:
        return await self.repo.list_racks(skip, limit, data_center_id, is_active)

    async def create_rack(self, data: RackCreate) -> Rack:
        # Verify data center exists
        datacenter = await self.dc_repo.get_by_id(data.data_center_id)
        if not datacenter:
            raise NotFoundException("DataCenter", str(data.data_center_id))

        rack = Rack(
            id=uuid.uuid4(),
            data_center_id=data.data_center_id,
            name=data.name,
            code=data.code,
            location=data.location,
            u_height=data.u_height,
            description=data.description,
            is_active=data.is_active,
        )
        return await self.repo.create(rack)

    async def update_rack(self, rack_id: UUID, data: RackUpdate) -> Rack:
        rack = await self.get_rack(rack_id)
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            return await self.repo.update(rack_id, **update_data)
        return rack

    async def delete_rack(self, rack_id: UUID) -> bool:
        await self.get_rack(rack_id)
        return await self.repo.delete(rack_id)


class ServerService:
    def __init__(self, session: AsyncSession):
        self.repo = ServerRepository(session)
        self.rack_repo = RackRepository(session)
        self.credential_repo = BMCCredentialRepository(session)

    async def get_server(self, server_id: UUID) -> Server:
        server = await self.repo.get_by_id(server_id)
        if not server:
            raise NotFoundException("Server", str(server_id))
        return server

    async def get_server_by_hostname(self, hostname: str) -> Server:
        server = await self.repo.get_by_hostname(hostname)
        if not server:
            raise NotFoundException("Server", hostname)
        return server

    async def list_servers(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[ServerFilter] = None,
    ) -> tuple[List[Server], int]:
        filter_dict = filters.model_dump(exclude_unset=True) if filters else {}
        return await self.repo.list_servers(skip, limit, **filter_dict)

    async def create_server(self, data: ServerCreate) -> Server:
        # Check hostname uniqueness if provided
        if data.hostname:
            existing = await self.repo.get_by_hostname(data.hostname)
            if existing:
                raise ConflictException(f"Hostname '{data.hostname}' already exists")

        # Check asset_tag uniqueness if provided
        if data.asset_tag:
            existing = await self.repo.get_by_asset_tag(data.asset_tag)
            if existing:
                raise ConflictException(f"Asset tag '{data.asset_tag}' already exists")

        # Check BMC IP uniqueness if provided
        bmc_ip = data.bmc_info.bmc_ip if data.bmc_info else None
        if bmc_ip:
            existing = await self.repo.get_by_bmc_ip(bmc_ip)
            if existing:
                raise ConflictException(f"BMC IP '{bmc_ip}' already exists")

        # Validate BMC credential requires BMC IP
        if data.bmc_credential and not bmc_ip:
            raise ValidationException("BMC IP is required when providing BMC credentials")

        # Verify rack exists if provided
        if data.rack_id:
            rack = await self.rack_repo.get_by_id(data.rack_id)
            if not rack:
                raise NotFoundException("Rack", str(data.rack_id))

        # Create server
        hardware = data.hardware_info.model_dump() if data.hardware_info else {}
        software = data.software_info.model_dump() if data.software_info else {}
        bmc = data.bmc_info.model_dump() if data.bmc_info else {}

        server = Server(
            id=uuid.uuid4(),
            name=data.name,
            hostname=data.hostname,
            serial_number=data.serial_number,
            asset_tag=data.asset_tag,
            brand=data.brand,
            model=data.model,
            server_type=data.server_type,
            status="active",
            rack_id=data.rack_id,
            rack_position=data.rack_position,
            rack_height=data.rack_height,
            owner_id=data.owner_id,
            department=data.department,
            description=data.description,
            # Hardware info
            cpu_model=hardware.get("cpu_model"),
            cpu_count=hardware.get("cpu_count", 0),
            cpu_cores_per_socket=hardware.get("cpu_cores_per_socket", 0),
            memory_gb=hardware.get("memory_gb", 0),
            disk_info=hardware.get("disk_info"),
            network_interfaces=hardware.get("network_interfaces"),
            # Software info
            os_name=software.get("os_name"),
            os_version=software.get("os_version"),
            # BMC info
            bmc_ip=bmc.get("bmc_ip"),
            bmc_mac=bmc.get("bmc_mac"),
            bmc_status=bmc.get("bmc_status", "unknown"),
            extra_data=data.metadata,
        )

        server = await self.repo.create(server)

        # Create BMC credential if provided
        if data.bmc_credential:
            credential = BMCCredential(
                id=uuid.uuid4(),
                server_id=server.id,
                username=data.bmc_credential.username,
                encrypted_password=encrypt_value(data.bmc_credential.password),
                encryption_key_id="default",
                protocol=data.bmc_credential.protocol,
                port=data.bmc_credential.port,
                is_default=True,
            )
            await self.credential_repo.create(credential)

        return server

    async def update_server(self, server_id: UUID, data: ServerUpdate) -> Server:
        server = await self.get_server(server_id)

        if data.hostname is not None and data.hostname != server.hostname:
            if data.hostname:
                existing = await self.repo.get_by_hostname(data.hostname)
                if existing:
                    raise ConflictException(f"Hostname '{data.hostname}' already exists")

        if data.asset_tag is not None and data.asset_tag != server.asset_tag:
            if data.asset_tag:
                existing = await self.repo.get_by_asset_tag(data.asset_tag)
                if existing:
                    raise ConflictException(f"Asset tag '{data.asset_tag}' already exists")

        if data.rack_id is not None and data.rack_id != server.rack_id:
            rack = await self.rack_repo.get_by_id(data.rack_id)
            if not rack:
                raise NotFoundException("Rack", str(data.rack_id))

        update_data = {}
        basic_fields = [
            "name", "hostname", "serial_number", "asset_tag", "rack_id", "rack_position",
            "rack_height", "owner_id", "department", "description", "metadata"
        ]
        for field in basic_fields:
            value = getattr(data, field, None)
            if value is not None:
                update_data[field] = value

        if data.hardware_info:
            hardware = data.hardware_info.model_dump(exclude_unset=True)
            if "cpu_model" in hardware:
                update_data["cpu_model"] = hardware["cpu_model"]
            if "cpu_count" in hardware:
                update_data["cpu_count"] = hardware["cpu_count"]
            if "cpu_cores_per_socket" in hardware:
                update_data["cpu_cores_per_socket"] = hardware["cpu_cores_per_socket"]
            if "memory_gb" in hardware:
                update_data["memory_gb"] = hardware["memory_gb"]
            if "disk_info" in hardware:
                update_data["disk_info"] = hardware["disk_info"]
            if "network_interfaces" in hardware:
                update_data["network_interfaces"] = hardware["network_interfaces"]

        if data.software_info:
            software = data.software_info.model_dump(exclude_unset=True)
            if "os_name" in software:
                update_data["os_name"] = software["os_name"]
            if "os_version" in software:
                update_data["os_version"] = software["os_version"]

        if data.bmc_info:
            bmc = data.bmc_info.model_dump(exclude_unset=True)
            if "bmc_ip" in bmc:
                new_bmc_ip = bmc["bmc_ip"]
                if new_bmc_ip and new_bmc_ip != server.bmc_ip:
                    existing = await self.repo.get_by_bmc_ip(new_bmc_ip)
                    if existing:
                        raise ConflictException(f"BMC IP '{new_bmc_ip}' already exists")
                update_data["bmc_ip"] = new_bmc_ip
            if "bmc_mac" in bmc:
                update_data["bmc_mac"] = bmc["bmc_mac"]
            if "bmc_status" in bmc:
                update_data["bmc_status"] = bmc["bmc_status"]

        if update_data:
            return await self.repo.update(server_id, **update_data)
        return server

    async def delete_server(self, server_id: UUID) -> bool:
        await self.get_server(server_id)
        # BMC credential will be deleted by cascade
        return await self.repo.delete(server_id)

    async def bulk_create_servers(
        self, data_list: List[ServerCreate]
    ) -> ServerImportResult:
        result = ServerImportResult(total=len(data_list), success=0, failed=0, errors=[])

        for data in data_list:
            try:
                await self.create_server(data)
                result.success += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({"server": data.name, "error": str(e)})

        return result

    async def bulk_update_servers(
        self, server_ids: List[UUID], updates: Dict[str, Any]
    ) -> int:
        allowed_fields = {
            "status", "department", "owner_id", "description",
            "rack_id", "rack_position", "rack_height",
        }
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered_updates:
            return 0
        return await self.repo.bulk_update(server_ids, **filtered_updates)

    async def bulk_delete_servers(self, server_ids: List[UUID]) -> int:
        return await self.repo.bulk_delete(server_ids)


class BMCCredentialService:
    def __init__(self, session: AsyncSession):
        self.repo = BMCCredentialRepository(session)
        self.server_repo = ServerRepository(session)

    async def get_credential(self, credential_id: UUID) -> BMCCredential:
        credential = await self.repo.get_by_id(credential_id)
        if not credential:
            raise NotFoundException("BMCCredential", str(credential_id))
        return credential

    async def get_credential_by_server(self, server_id: UUID) -> BMCCredential:
        credential = await self.repo.get_by_server_id(server_id)
        if not credential:
            raise NotFoundException("BMCCredential", f"server_id={server_id}")
        return credential

    async def create_or_update_credential(
        self, server_id: UUID, data: BMCCredentialCreate
    ) -> BMCCredential:
        # Verify server exists
        server = await self.server_repo.get_by_id(server_id)
        if not server:
            raise NotFoundException("Server", str(server_id))

        # Check if credential already exists
        existing = await self.repo.get_by_server_id(server_id)

        if existing:
            update_kwargs = {}
            if data.username is not None:
                update_kwargs["username"] = data.username
            if data.password is not None:
                update_kwargs["encrypted_password"] = encrypt_value(data.password)
            if data.protocol is not None:
                update_kwargs["protocol"] = data.protocol
            if data.port is not None:
                update_kwargs["port"] = data.port
            if update_kwargs:
                return await self.repo.update(existing.id, **update_kwargs)
            return existing
        else:
            if not data.password:
                raise ValidationException("Password is required when creating BMC credential")
            credential = BMCCredential(
                id=uuid.uuid4(),
                server_id=server_id,
                username=data.username,
                encrypted_password=encrypt_value(data.password),
                encryption_key_id="default",
                protocol=data.protocol,
                port=data.port,
                is_default=True,
            )
            return await self.repo.create(credential)

    async def update_credential(
        self, credential_id: UUID, data: BMCCredentialUpdate
    ) -> BMCCredential:
        credential = await self.get_credential(credential_id)
        update_data = data.model_dump(exclude_unset=True)

        # Hash password if provided
        if "password" in update_data:
            if update_data["password"] is not None:
                update_data["encrypted_password"] = encrypt_value(update_data.pop("password"))
            else:
                del update_data["password"]

        if update_data:
            return await self.repo.update(credential_id, **update_data)
        return credential

    async def delete_credential(self, credential_id: UUID) -> bool:
        await self.get_credential(credential_id)
        return await self.repo.delete(credential_id)
