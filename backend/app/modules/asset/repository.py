from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.asset.models import BMCCredential, DataCenter, Rack, Server


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DataCenterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, dc_id: UUID) -> Optional[DataCenter]:
        result = await self.session.execute(
            select(DataCenter).where(DataCenter.id == dc_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[DataCenter]:
        result = await self.session.execute(
            select(DataCenter).where(DataCenter.code == code)
        )
        return result.scalar_one_or_none()

    async def list_datacenters(
        self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
    ) -> tuple[List[DataCenter], int]:
        query = select(DataCenter)
        count_query = select(func.count(DataCenter.id))

        if is_active is not None:
            query = query.where(DataCenter.is_active == is_active)
            count_query = count_query.where(DataCenter.is_active == is_active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, datacenter: DataCenter) -> DataCenter:
        self.session.add(datacenter)
        await self.session.flush()
        await self.session.refresh(datacenter)
        return datacenter

    async def update(self, dc_id: UUID, **kwargs) -> Optional[DataCenter]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(DataCenter).where(DataCenter.id == dc_id).values(**filtered)
            )
        return await self.get_by_id(dc_id)

    async def delete(self, dc_id: UUID) -> bool:
        datacenter = await self.get_by_id(dc_id)
        if datacenter:
            await self.session.delete(datacenter)
            return True
        return False


class RackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, rack_id: UUID) -> Optional[Rack]:
        result = await self.session.execute(
            select(Rack).where(Rack.id == rack_id).options(selectinload(Rack.data_center))
        )
        return result.scalar_one_or_none()

    async def list_racks(
        self,
        skip: int = 0,
        limit: int = 100,
        data_center_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Rack], int]:
        query = select(Rack).options(selectinload(Rack.data_center))
        count_query = select(func.count(Rack.id))

        if data_center_id:
            query = query.where(Rack.data_center_id == data_center_id)
            count_query = count_query.where(Rack.data_center_id == data_center_id)
        if is_active is not None:
            query = query.where(Rack.is_active == is_active)
            count_query = count_query.where(Rack.is_active == is_active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def create(self, rack: Rack) -> Rack:
        self.session.add(rack)
        await self.session.flush()
        await self.session.refresh(rack)
        return rack

    async def update(self, rack_id: UUID, **kwargs) -> Optional[Rack]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(Rack).where(Rack.id == rack_id).values(**filtered)
            )
        return await self.get_by_id(rack_id)

    async def delete(self, rack_id: UUID) -> bool:
        rack = await self.get_by_id(rack_id)
        if rack:
            await self.session.delete(rack)
            return True
        return False


class ServerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, server_id: UUID) -> Optional[Server]:
        result = await self.session.execute(
            select(Server)
            .where(Server.id == server_id)
            .options(selectinload(Server.rack).selectinload(Rack.data_center))
        )
        return result.scalar_one_or_none()

    async def get_by_hostname(self, hostname: str) -> Optional[Server]:
        result = await self.session.execute(
            select(Server).where(Server.hostname == hostname)
        )
        return result.scalar_one_or_none()

    async def get_by_serial_number(self, serial_number: str) -> Optional[Server]:
        result = await self.session.execute(
            select(Server).where(Server.serial_number == serial_number)
        )
        return result.scalar_one_or_none()

    async def get_by_asset_tag(self, asset_tag: str) -> Optional[Server]:
        result = await self.session.execute(
            select(Server).where(Server.asset_tag == asset_tag)
        )
        return result.scalar_one_or_none()

    async def get_by_bmc_ip(self, bmc_ip: str) -> Optional[Server]:
        result = await self.session.execute(
            select(Server).where(Server.bmc_ip == bmc_ip)
        )
        return result.scalar_one_or_none()

    async def list_servers(
        self,
        skip: int = 0,
        limit: int = 100,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
        data_center_id: Optional[UUID] = None,
        rack_id: Optional[UUID] = None,
        bmc_status: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Server], int]:
        query = select(Server).options(
            selectinload(Server.rack).selectinload(Rack.data_center)
        )

        # Apply filters
        filters = []
        if brand:
            filters.append(Server.brand == brand)
        if model:
            filters.append(Server.model == model)
        if status:
            filters.append(Server.status == status)
        if rack_id:
            filters.append(Server.rack_id == rack_id)
        if bmc_status:
            filters.append(Server.bmc_status == bmc_status)
        if owner_id:
            filters.append(Server.owner_id == owner_id)
        if department:
            filters.append(Server.department == department)

        if data_center_id:
            query = query.join(Rack).where(Rack.data_center_id == data_center_id)

        if search:
            search_safe = _escape_like(search)
            search_filter = or_(
                Server.name.ilike(f"%{search_safe}%", escape="\\"),
                Server.hostname.ilike(f"%{search_safe}%", escape="\\"),
                Server.serial_number.ilike(f"%{search_safe}%", escape="\\"),
                Server.asset_tag.ilike(f"%{search_safe}%", escape="\\"),
                Server.bmc_ip.ilike(f"%{search_safe}%", escape="\\"),
            )
            filters.append(search_filter)

        if filters:
            query = query.where(and_(*filters))

        count_query = select(func.count(Server.id))
        if data_center_id:
            count_query = count_query.join(Rack).where(Rack.data_center_id == data_center_id)
        if filters:
            count_query = count_query.where(and_(*filters))

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def create(self, server: Server) -> Server:
        self.session.add(server)
        await self.session.flush()
        await self.session.refresh(server)
        return server

    async def update(self, server_id: UUID, **kwargs) -> Optional[Server]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(Server).where(Server.id == server_id).values(**filtered)
            )
        return await self.get_by_id(server_id)

    async def delete(self, server_id: UUID) -> bool:
        server = await self.get_by_id(server_id)
        if server:
            await self.session.delete(server)
            return True
        return False

    async def bulk_create(self, servers: List[Server]) -> List[Server]:
        self.session.add_all(servers)
        await self.session.flush()
        for server in servers:
            await self.session.refresh(server)
        return servers

    async def bulk_update(self, server_ids: List[UUID], **kwargs) -> int:
        if not server_ids:
            return 0
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if not filtered:
            return 0
        result = await self.session.execute(
            update(Server).where(Server.id.in_(server_ids)).values(**filtered)
        )
        return result.rowcount

    async def bulk_delete(self, server_ids: List[UUID]) -> int:
        if not server_ids:
            return 0
        result = await self.session.execute(
            delete(Server).where(Server.id.in_(server_ids))
        )
        return result.rowcount


class BMCCredentialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, credential_id: UUID) -> Optional[BMCCredential]:
        result = await self.session.execute(
            select(BMCCredential).where(BMCCredential.id == credential_id)
        )
        return result.scalar_one_or_none()

    async def get_by_server_id(self, server_id: UUID) -> Optional[BMCCredential]:
        result = await self.session.execute(
            select(BMCCredential).where(BMCCredential.server_id == server_id)
        )
        return result.scalar_one_or_none()

    async def create(self, credential: BMCCredential) -> BMCCredential:
        self.session.add(credential)
        await self.session.flush()
        await self.session.refresh(credential)
        return credential

    async def update(self, credential_id: UUID, **kwargs) -> Optional[BMCCredential]:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self.session.execute(
                update(BMCCredential)
                .where(BMCCredential.id == credential_id)
                .values(**filtered)
            )
        return await self.get_by_id(credential_id)

    async def delete(self, credential_id: UUID) -> bool:
        credential = await self.get_by_id(credential_id)
        if credential:
            await self.session.delete(credential)
            return True
        return False

    async def delete_by_server_id(self, server_id: UUID) -> bool:
        credential = await self.get_by_server_id(server_id)
        if credential:
            await self.session.delete(credential)
            return True
        return False
