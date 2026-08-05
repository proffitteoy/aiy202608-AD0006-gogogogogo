from functools import lru_cache
from uuid import UUID

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RISKTRACE_",
        extra="ignore",
    )

    app_name: str = "RiskTrace API"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    database_url: str = (
        "postgresql+asyncpg://risktrace:risktrace-local@localhost:5432/risktrace"
    )
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "risktrace"
    s3_secret_access_key: str = "risktrace-local-secret"
    s3_bucket: str = "risktrace"
    healthcheck_timeout_seconds: float = 2.0
    demo_tenant_id: UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    ingestion_api_token: SecretStr = SecretStr("")
    ingestion_tenant_id: UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    ingestion_allowed_providers: str = ""
    live_pull_api_base_url: str = "http://localhost:8000"
    live_pull_request_timeout_seconds: float = 10.0
    live_pull_license_scope: str = "internal_research"
    live_pull_tencent_symbols: str = "600519,000001,510300"
    live_pull_tencent_stream: str = "a-share-live"
    live_pull_cls_page_size: int = 20
    live_pull_cls_stream: str = "cls-telegraph"
    live_pull_snowball_cookie: SecretStr = SecretStr("")
    live_pull_snowball_scope: str = "day"
    live_pull_snowball_count: int = 20
    live_pull_snowball_stream: str = "xueqiu-hot-posts"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_small_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ingestion_allowed_provider_set(self) -> frozenset[str]:
        return frozenset(
            provider.strip()
            for provider in self.ingestion_allowed_providers.split(",")
            if provider.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
