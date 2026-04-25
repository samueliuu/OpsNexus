from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    environment: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False

    app_name: str = "衡驭OpsNexus智能服务器运维系统"
    app_version: str = "0.1.1"

    database_url: str = "postgresql+asyncpg://opsnexus:opsnexus_dev@localhost:5432/opsnexus"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True

    redis_url: str = "redis://localhost:6379/0"

    rabbitmq_url: str = "amqp://opsnexus:opsnexus_dev@localhost:5672/"

    minio_url: str = "http://localhost:9000"
    minio_access_key: str = "opsnexus"
    minio_secret_key: str = "opsnexus_dev"
    minio_bucket: str = "opsnexus"

    jwt_secret_key: str = "change-me-to-a-strong-random-key-in-production"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    encryption_key: Optional[str] = None

    bmc_connect_timeout: int = 10
    bmc_read_timeout: int = 30
    bmc_max_connections_per_host: int = 5
    bmc_allowed_networks: List[str] = []

    metric_collect_interval: int = 60
    metric_retention_days: int = 90
    audit_log_retention_days: int = 180

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    cors_origins: List[str] = ["http://localhost:3000", "http://localhost"]

    feature_autoops_enabled: bool = True
    feature_kvm_enabled: bool = True
    feature_websocket_enabled: bool = True
    feature_knowledge_service_enabled: bool = True

    ragflow_api_url: str = "http://localhost:9380"
    ragflow_api_key: str = ""
    ragflow_timeout: int = 30
    knowledge_cache_ttl: int = 300

    netbox_api_url: str = ""
    netbox_api_token: str = ""
    netbox_timeout: int = 30
    netbox_sync_enabled: bool = False
    netbox_verify_ssl: bool = True

    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if info.data.get("environment") == "production" and v == "change-me-to-a-strong-random-key-in-production":
            raise ValueError("JWT secret key must be changed in production environment")
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
