import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# Base schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr = Field(..., max_length=255)
    full_name: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    department: Optional[str] = Field(None, max_length=64)
    is_active: bool = True


class RoleBase(BaseModel):
    name: str = Field(..., max_length=64)
    code: str = Field(..., max_length=64)
    description: Optional[str] = None
    data_scope: str = Field(default="all", pattern="^(all|data_center|department|custom)$")


class PermissionBase(BaseModel):
    code: str = Field(..., max_length=128)
    name: str = Field(..., max_length=128)
    resource: str = Field(..., max_length=64)
    action: str = Field(..., max_length=32)
    description: Optional[str] = None


# Create schemas
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role_ids: List[UUID] = []


class RoleCreate(RoleBase):
    permission_ids: List[UUID] = []


class PermissionCreate(PermissionBase):
    pass


# Update schemas
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    department: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None
    role_ids: Optional[List[UUID]] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    data_scope: Optional[str] = Field(None, pattern="^(all|data_center|department|custom)$")
    permission_ids: Optional[List[UUID]] = None


# Response schemas
class PermissionResponse(PermissionBase):
    id: UUID
    is_builtin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RoleResponse(RoleBase):
    id: UUID
    is_builtin: bool
    permissions: List[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    id: UUID
    is_superuser: bool
    user_type: str = "owner"
    company: Optional[str] = None
    title: Optional[str] = None
    last_login_at: Optional[datetime]
    roles: List[RoleResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int
    page: int
    page_size: int


class PermissionListResponse(BaseModel):
    items: List[PermissionResponse]
    total: int
    page: int
    page_size: int


# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    user_type: str = Field(default="owner", pattern="^(owner|provider)$")
    company: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=64)


class RegisterResponse(BaseModel):
    id: UUID
    username: str
    email: str
    user_type: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# System config schemas
class SystemConfigBase(BaseModel):
    key: str = Field(..., max_length=128)
    value: str
    value_type: str = Field(default="string", pattern="^(string|int|bool|json)$")
    description: Optional[str] = None
    is_sensitive: bool = False


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class SystemConfigResponse(SystemConfigBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Notification channel schemas
class NotificationChannelBase(BaseModel):
    name: str = Field(..., max_length=64)
    channel_type: str = Field(..., pattern="^(email|webhook|dingtalk|wecom|lark)$")
    config: dict
    is_enabled: bool = True


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None

    @field_validator("config", mode="after")
    @classmethod
    def reject_null_config(cls, v):
        if v is None:
            raise ValueError("config cannot be null")
        return v


class NotificationChannelResponse(NotificationChannelBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


# WebSocket ticket schema
class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int
