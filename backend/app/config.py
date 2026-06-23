from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # ─── App ──────────────────────────────────────────────
    app_name: str = Field(default="TITAN AI OS")
    app_env: str = Field(default="development")
    secret_key: str = Field(default="change-me-in-production")
    debug: bool = Field(default=True)

    # ─── Database ─────────────────────────────────────────
    database_url: str = Field(...)

    # ─── Redis ────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ─── Qdrant ───────────────────────────────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_api_key: str = Field(default="")

    # ─── LLM Providers ────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # ─── Tools ────────────────────────────────────────────
    tavily_api_key: str = Field(default="")
    resend_api_key: str = Field(default="")
    resend_from_email: str = Field(default="noreply@example.com")

    # ─── JWT ──────────────────────────────────────────────
    jwt_secret: str = Field(default="change-jwt-secret-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=30)

    # ─── CORS ─────────────────────────────────────────────
    allowed_origins: str = Field(default="http://localhost:3000")

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
