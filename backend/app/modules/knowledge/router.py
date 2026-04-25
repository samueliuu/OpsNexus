from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_active_user, get_db
from app.modules.knowledge.schemas import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    FavoriteCreate,
    FavoriteListResponse,
    FavoriteResponse,
    FirmwareResponse,
    KnowledgeAnswer,
    KnowledgeQuery,
    SELCodeResponse,
)
from app.modules.knowledge.service import (
    ConversationService,
    FavoriteService,
    KnowledgeService,
)
from app.modules.system.models import User

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.post("/query", response_model=KnowledgeAnswer)
async def knowledge_query(
    data: KnowledgeQuery,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    return await service.query(current_user.id, data)


@router.get("/sel-codes", response_model=List[SELCodeResponse])
async def query_sel_codes(
    brand: str = Query(..., max_length=32),
    event_code: Optional[str] = Query(None, max_length=16),
    severity: Optional[str] = Query(None, max_length=16),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    results, _ = await service.query_sel_codes(brand=brand, event_code=event_code, severity=severity, skip=skip, limit=limit)
    return results


@router.get("/firmware-matrix", response_model=List[FirmwareResponse])
async def query_firmware_matrix(
    brand: str = Query(..., max_length=32),
    model: Optional[str] = Query(None, max_length=128),
    component: Optional[str] = Query(None, max_length=64),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = KnowledgeService(db)
    results, _ = await service.query_firmware_matrix(brand=brand, model=model, component=component, skip=skip, limit=limit)
    return results


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = ConversationService(db)
    return await service.create(current_user.id, data)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = ConversationService(db)
    items, total = await service.list_by_user(current_user.id, skip, limit)
    return ConversationListResponse(items=items, total=total)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = ConversationService(db)
    return await service.get(conversation_id, current_user.id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = ConversationService(db)
    return await service.update(conversation_id, current_user.id, data)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = ConversationService(db)
    await service.delete(conversation_id, current_user.id)
    return None


@router.post("/favorites", response_model=FavoriteResponse, status_code=201)
async def create_favorite(
    data: FavoriteCreate,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = FavoriteService(db)
    return await service.create(current_user.id, data)


@router.get("/favorites", response_model=FavoriteListResponse)
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = FavoriteService(db)
    items, total = await service.list_by_user(current_user.id, skip, limit)
    return FavoriteListResponse(items=items, total=total)


@router.delete("/favorites/{favorite_id}", status_code=204)
async def delete_favorite(
    favorite_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db=Depends(get_db),
):
    service = FavoriteService(db)
    await service.delete(favorite_id, current_user.id)
    return None


@router.get("/health")
async def knowledge_health():
    return {"status": "healthy", "module": "knowledge"}
