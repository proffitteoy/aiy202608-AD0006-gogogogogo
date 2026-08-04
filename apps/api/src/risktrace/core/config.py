from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
