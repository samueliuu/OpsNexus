import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.modules.knowledge.models import (
    Conversation,
    ConversationMessage,
    FirmwareCompatibility,
    KnowledgeFavorite,
    SELEventCode,
)
from app.modules.knowledge.repository import (
    ConversationRepository,
    FavoriteRepository,
    FirmwareRepository,
    MessageRepository,
    SELCodeRepository,
)
from app.modules.knowledge.schemas import (
    ConversationCreate,
    ConversationUpdate,
    FavoriteCreate,
    KnowledgeAnswer,
    KnowledgeQuery,
    KnowledgeSource,
)


class RAGQueryService:
    """语义查询服务：负责 RAGFlow 调用、缓存管理和降级查询。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sel_repo = SELCodeRepository(session)
        self.firmware_repo = FirmwareRepository(session)

    async def semantic_query(self, data: KnowledgeQuery) -> KnowledgeAnswer:
        """执行语义查询，优先使用缓存，然后调用 RAGFlow 或降级查询。"""
        cache_key = f"knowledge:semantic:{hash(data.question + (data.brand or '') + (data.model or ''))}"
        cached = await Cache.get(cache_key)
        if cached:
            return KnowledgeAnswer(**cached)

        if settings.ragflow_api_key:
            answer = await self._call_ragflow(data)
        else:
            answer = await self._fallback_query(data)

        await Cache.set(cache_key, answer.model_dump(mode="json"), expire=settings.knowledge_cache_ttl)
        return answer

    async def _call_ragflow(self, data: KnowledgeQuery) -> KnowledgeAnswer:
        """调用 RAGFlow API 进行语义检索。"""
        dataset_id = self._get_dataset_id(data.brand, data.category)
        try:
            async with httpx.AsyncClient(timeout=settings.ragflow_timeout) as client:
                resp = await client.post(
                    f"{settings.ragflow_api_url}/api/v1/retrieval",
                    headers={"Authorization": f"Bearer {settings.ragflow_api_key}"},
                    json={
                        "question": data.question,
                        "dataset_ids": [dataset_id] if dataset_id else [],
                        "top_k": data.top_k,
                    },
                )
                resp.raise_for_status()
                result = resp.json()
                chunks = result.get("data", {}).get("chunks", [])
                sources = [
                    KnowledgeSource(
                        document_title=c.get("document_keyword", ""),
                        chunk_text=c.get("content", ""),
                        relevance_score=c.get("similarity", 0),
                    )
                    for c in chunks
                ]
                answer_text = "\n\n".join([c.get("content", "") for c in chunks[:3]]) if chunks else "未找到相关文档。"
                return KnowledgeAnswer(
                    answer=answer_text,
                    sources=sources,
                    query_type="semantic",
                    brand=data.brand,
                    confidence=chunks[0].get("similarity") if chunks else None,
                )
        except Exception:
            return await self._fallback_query(data)

    async def _fallback_query(self, data: KnowledgeQuery) -> KnowledgeAnswer:
        """RAGFlow 不可用时的降级查询，基于本地结构化数据进行关键词匹配。"""
        results = []
        if data.brand:
            sel_results, _ = await self.sel_repo.query(brand=data.brand, limit=5)
            for r in sel_results:
                if data.question.lower() in r.description.lower() or data.question.lower() in r.event_code.lower():
                    results.append(f"[SEL {r.event_code}] {r.description}\n建议: {r.recommended_action or '无'}")
            fw_results, _ = await self.firmware_repo.query(brand=data.brand, model=data.model, limit=5)
            for r in fw_results:
                results.append(f"[Firmware] {r.model} {r.component} v{r.version} ({r.criticality})")

        answer_text = "\n\n".join(results) if results else "暂未接入AI知识引擎，当前仅支持结构化数据查询。请尝试查询SEL事件码或固件信息。"
        return KnowledgeAnswer(
            answer=answer_text,
            sources=[],
            query_type="semantic",
            brand=data.brand,
        )

    def _get_dataset_id(self, brand: Optional[str], category: Optional[str]) -> Optional[str]:
        mapping = {
            "dell:troubleshooting": "dell-troubleshooting",
            "dell:user-manual": "dell-user-manual",
            "dell:api-reference": "dell-api-reference",
            "dell:sel-codes": "dell-sel-codes",
            "dell:firmware-matrix": "dell-firmware-matrix",
            "hpe:troubleshooting": "hpe-troubleshooting",
            "hpe:user-manual": "hpe-user-manual",
            "hpe:api-reference": "hpe-api-reference",
            "hpe:sel-codes": "hpe-sel-codes",
            "hpe:firmware-matrix": "hpe-firmware-matrix",
            "lenovo:troubleshooting": "lenovo-troubleshooting",
            "lenovo:user-manual": "lenovo-user-manual",
            "lenovo:sel-codes": "lenovo-sel-codes",
            "lenovo:firmware-matrix": "lenovo-firmware-matrix",
            "huawei:troubleshooting": "huawei-troubleshooting",
            "huawei:user-manual": "huawei-user-manual",
            "huawei:sel-codes": "huawei-sel-codes",
            "huawei:firmware-matrix": "huawei-firmware-matrix",
            "h3c:troubleshooting": "h3c-troubleshooting",
            "h3c:sel-codes": "h3c-sel-codes",
            "inspur:troubleshooting": "inspur-troubleshooting",
            "inspur:sel-codes": "inspur-sel-codes",
            "sugon:troubleshooting": "sugon-troubleshooting",
            "sugon:sel-codes": "sugon-sel-codes",
            "xfusion:troubleshooting": "xfusion-troubleshooting",
            "xfusion:sel-codes": "xfusion-sel-codes",
        }
        if brand and category:
            return mapping.get(f"{brand}:{category}")
        if brand:
            return mapping.get(f"{brand}:troubleshooting")
        return None


class StructuredQueryService:
    """结构化查询服务：负责 SEL 事件码和固件兼容性矩阵的查询。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sel_repo = SELCodeRepository(session)
        self.firmware_repo = FirmwareRepository(session)

    async def structured_query(self, data: KnowledgeQuery) -> KnowledgeAnswer:
        """执行结构化查询，从 SEL 事件码和固件兼容性表中检索数据。"""
        results = []
        if data.brand:
            sel_results, _ = await self.sel_repo.query(brand=data.brand, limit=5)
            results.extend([f"[SEL] {r.event_code}: {r.description}" for r in sel_results])
            fw_results, _ = await self.firmware_repo.query(brand=data.brand, model=data.model, limit=5)
            results.extend([f"[Firmware] {r.model} {r.component} v{r.version}" for r in fw_results])

        answer_text = "\n".join(results) if results else "未找到匹配的结构化数据，请尝试语义查询。"
        return KnowledgeAnswer(
            answer=answer_text,
            sources=[],
            query_type="structured",
            brand=data.brand,
        )

    async def query_sel_codes(
        self, brand: str, event_code: Optional[str] = None, severity: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[SELEventCode], int]:
        """查询 SEL 事件码。"""
        return await self.sel_repo.query(brand=brand, event_code=event_code, severity=severity, skip=skip, limit=limit)

    async def query_firmware_matrix(
        self, brand: str, model: Optional[str] = None, component: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[FirmwareCompatibility], int]:
        """查询固件兼容性矩阵。"""
        return await self.firmware_repo.query(brand=brand, model=model, component=component, skip=skip, limit=limit)


class KnowledgeService:
    """知识查询协调服务：负责查询路由和对话持久化。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.rag_service = RAGQueryService(session)
        self.structured_service = StructuredQueryService(session)

    async def query_sel_codes(
        self, brand: str, event_code: Optional[str] = None, severity: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[SELEventCode], int]:
        """委托给 StructuredQueryService 查询 SEL 事件码。"""
        return await self.structured_service.query_sel_codes(
            brand=brand, event_code=event_code, severity=severity, skip=skip, limit=limit
        )

    async def query_firmware_matrix(
        self, brand: str, model: Optional[str] = None, component: Optional[str] = None, skip: int = 0, limit: int = 20
    ) -> tuple[List[FirmwareCompatibility], int]:
        """委托给 StructuredQueryService 查询固件兼容性矩阵。"""
        return await self.structured_service.query_firmware_matrix(
            brand=brand, model=model, component=component, skip=skip, limit=limit
        )

    async def query(self, user_id: UUID, data: KnowledgeQuery) -> KnowledgeAnswer:
        """查询路由：根据 query_type 分发到语义查询、结构化查询或混合查询。"""
        start_time = datetime.now(timezone.utc)

        if data.query_type == "structured":
            answer = await self.structured_service.structured_query(data)
        elif data.query_type == "semantic":
            answer = await self.rag_service.semantic_query(data)
        else:
            answer = await self._hybrid_query(data)

        latency = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        answer.latency_ms = latency

        if data.conversation_id:
            await self._persist_conversation(user_id, data, answer, latency)

        return answer

    async def _hybrid_query(self, data: KnowledgeQuery) -> KnowledgeAnswer:
        """混合查询：组合语义查询和结构化查询的结果。"""
        semantic = await self.rag_service.semantic_query(data)
        structured = await self.structured_service.structured_query(data)
        combined = semantic.answer
        if structured.answer and "未找到" not in structured.answer:
            combined = f"{semantic.answer}\n\n--- 结构化数据 ---\n{structured.answer}"
        return KnowledgeAnswer(
            answer=combined,
            sources=semantic.sources,
            query_type="hybrid",
            brand=data.brand,
            confidence=semantic.confidence,
        )

    async def _persist_conversation(
        self, user_id: UUID, data: KnowledgeQuery, answer: KnowledgeAnswer, latency: int
    ) -> None:
        """将查询和回答持久化到对话消息中。"""
        conv_repo = ConversationRepository(self.session)
        conv = await conv_repo.get_by_id(data.conversation_id)
        if not conv or str(conv.user_id) != str(user_id):
            return

        msg_repo = MessageRepository(self.session)
        user_msg = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=data.conversation_id,
            role="user",
            content=data.question,
            query_type=data.query_type,
            brand=data.brand,
        )
        await msg_repo.create(user_msg)
        assistant_msg = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=data.conversation_id,
            role="assistant",
            content=answer.answer,
            sources=[s.model_dump() for s in answer.sources] if answer.sources else None,
            query_type=data.query_type,
            brand=data.brand,
            latency_ms=latency,
        )
        await msg_repo.create(assistant_msg)
        answer.message_id = assistant_msg.id
        answer.conversation_id = data.conversation_id


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)

    async def create(self, user_id: UUID, data: ConversationCreate) -> Conversation:
        conv = Conversation(id=uuid.uuid4(), user_id=user_id, title=data.title)
        return await self.repo.create(conv)

    async def get(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        conv = await self.repo.get_by_id(conversation_id)
        if not conv or str(conv.user_id) != str(user_id):
            raise NotFoundException("Conversation", str(conversation_id))
        return conv

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 20) -> tuple[List[Conversation], int]:
        return await self.repo.list_by_user(user_id, skip, limit)

    async def update(self, conversation_id: UUID, user_id: UUID, data: ConversationUpdate) -> Conversation:
        conv = await self.repo.get_by_id(conversation_id)
        if not conv or str(conv.user_id) != str(user_id):
            raise NotFoundException("Conversation", str(conversation_id))
        return await self.repo.update(conversation_id, title=data.title)

    async def delete(self, conversation_id: UUID, user_id: UUID) -> bool:
        conv = await self.repo.get_by_id(conversation_id)
        if not conv or str(conv.user_id) != str(user_id):
            raise NotFoundException("Conversation", str(conversation_id))
        return await self.repo.delete(conversation_id)


class FavoriteService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FavoriteRepository(session)

    async def create(self, user_id: UUID, data: FavoriteCreate) -> KnowledgeFavorite:
        fav = KnowledgeFavorite(
            id=uuid.uuid4(),
            user_id=user_id,
            message_id=data.message_id,
            title=data.title,
            content=data.content,
            source_type=data.source_type,
            brand=data.brand,
        )
        return await self.repo.create(fav)

    async def list_by_user(self, user_id: UUID, skip: int = 0, limit: int = 20) -> tuple[List[KnowledgeFavorite], int]:
        return await self.repo.list_by_user(user_id, skip, limit)

    async def delete(self, favorite_id: UUID, user_id: UUID) -> bool:
        """删除收藏，校验收藏归属当前用户，防止越权删除。"""
        fav = await self.repo.get_by_id(favorite_id)
        if not fav:
            raise NotFoundException("Favorite", str(favorite_id))
        if str(fav.user_id) != str(user_id):
            raise NotFoundException("Favorite", str(favorite_id))
        return await self.repo.delete(favorite_id)
