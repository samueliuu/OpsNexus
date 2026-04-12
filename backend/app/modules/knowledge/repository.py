from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.knowledge.models import (
    Conversation,
    ConversationMessage,
    FirmwareCompatibility,
    KnowledgeFavorite,
    SELEventCode,
)


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 20) -> tuple[List[Conversation], int]:
        query = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        count_query = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def update(self, conversation_id: UUID, **kwargs) -> Optional[Conversation]:
        conv = await self.get_by_id(conversation_id)
        if conv:
            for key, value in kwargs.items():
                if hasattr(conv, key) and value is not None:
                    setattr(conv, key, value)
            await self.session.commit()
            await self.session.refresh(conv)
        return conv

    async def delete(self, conversation_id: UUID) -> bool:
        conv = await self.get_by_id(conversation_id)
        if conv:
            await self.session.delete(conv)
            await self.session.commit()
            return True
        return False


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: ConversationMessage) -> ConversationMessage:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, favorite: KnowledgeFavorite) -> KnowledgeFavorite:
        self.session.add(favorite)
        await self.session.commit()
        await self.session.refresh(favorite)
        return favorite

    async def get_by_id(self, favorite_id: UUID) -> Optional[KnowledgeFavorite]:
        result = await self.session.execute(
            select(KnowledgeFavorite).where(KnowledgeFavorite.id == favorite_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 20) -> tuple[List[KnowledgeFavorite], int]:
        query = select(KnowledgeFavorite).where(KnowledgeFavorite.user_id == user_id).order_by(KnowledgeFavorite.created_at.desc())
        count_query = select(func.count(KnowledgeFavorite.id)).where(KnowledgeFavorite.user_id == user_id)
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def delete(self, favorite_id: UUID) -> bool:
        result = await self.session.execute(select(KnowledgeFavorite).where(KnowledgeFavorite.id == favorite_id))
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.commit()
            return True
        return False


class SELCodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def query(
        self, brand: str, event_code: Optional[str] = None, severity: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[SELEventCode], int]:
        query = select(SELEventCode).where(SELEventCode.brand == brand)
        count_query = select(func.count(SELEventCode.id)).where(SELEventCode.brand == brand)
        if event_code:
            query = query.where(SELEventCode.event_code == event_code)
            count_query = count_query.where(SELEventCode.event_code == event_code)
        if severity:
            query = query.where(SELEventCode.severity == severity)
            count_query = count_query.where(SELEventCode.severity == severity)
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total


class FirmwareRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def query(
        self, brand: str, model: Optional[str] = None, component: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[FirmwareCompatibility], int]:
        query = select(FirmwareCompatibility).where(FirmwareCompatibility.brand == brand)
        count_query = select(func.count(FirmwareCompatibility.id)).where(FirmwareCompatibility.brand == brand)
        if model:
            query = query.where(FirmwareCompatibility.model == model)
            count_query = count_query.where(FirmwareCompatibility.model == model)
        if component:
            query = query.where(FirmwareCompatibility.component == component)
            count_query = count_query.where(FirmwareCompatibility.component == component)
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total
