from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KnowledgeQuery(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    brand: Optional[str] = Field(None, max_length=32)
    model: Optional[str] = Field(None, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    query_type: str = Field(default="semantic", pattern="^(semantic|structured|hybrid)$")
    conversation_id: Optional[UUID] = None
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSource(BaseModel):
    document_title: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    relevance_score: Optional[float] = None
    chunk_text: Optional[str] = None


class KnowledgeAnswer(BaseModel):
    answer: str
    sources: List[KnowledgeSource] = []
    query_type: str = "semantic"
    brand: Optional[str] = None
    confidence: Optional[float] = None
    conversation_id: Optional[UUID] = None
    message_id: Optional[UUID] = None
    latency_ms: Optional[int] = None


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    sources: Optional[List[KnowledgeSource]] = None
    query_type: Optional[str] = None
    brand: Optional[str] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return [KnowledgeSource(**item) if isinstance(item, dict) else item for item in v]
        return v


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    message_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=256)
    content: str = Field(..., min_length=1)
    source_type: str = Field(default="qa", max_length=32)
    brand: Optional[str] = Field(None, max_length=32)


class FavoriteResponse(BaseModel):
    id: UUID
    title: str
    content: str
    source_type: str
    brand: Optional[str] = None
    message_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    items: List[FavoriteResponse]
    total: int


class SELCodeQuery(BaseModel):
    brand: str = Field(..., max_length=32)
    event_code: Optional[str] = Field(None, max_length=16)
    severity: Optional[str] = Field(None, max_length=16)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class SELCodeResponse(BaseModel):
    id: UUID
    brand: str
    event_code: str
    sensor_type: Optional[str] = None
    severity: str
    description: str
    recommended_action: Optional[str] = None

    class Config:
        from_attributes = True


class FirmwareQuery(BaseModel):
    brand: str = Field(..., max_length=32)
    model: Optional[str] = Field(None, max_length=128)
    component: Optional[str] = Field(None, max_length=64)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class FirmwareResponse(BaseModel):
    id: UUID
    brand: str
    model: str
    component: str
    version: str
    release_date: Optional[datetime] = None
    criticality: str = "optional"
    release_notes: Optional[str] = None
    download_url: Optional[str] = None

    class Config:
        from_attributes = True
