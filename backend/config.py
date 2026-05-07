"""Runtime settings for the open due diligence agent."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Due Diligence Agent Open"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8102
    cors_origins: str = "http://localhost:3000,http://localhost:5174"

    due_diligence_provider: str = "mock"
    due_diligence_model: str = "mock-diligence"
    due_diligence_risk_model: str = "mock-risk-reviewer"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5.5"
    openai_reasoning_effort: Optional[str] = "medium"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.1-pro-preview"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = ""

    storage_provider: str = "local"
    local_storage_dir: Path = Path("./storage")
    session_store: Path = Path("./storage/sessions.json")
    max_upload_mb: int = 100
    rag_storage_dir: Path = Path("./storage/rag")
    default_rag_source_dir: Optional[Path] = None
    local_embedding_dimensions: int = 384
    rag_chunk_words: int = 650
    rag_chunk_overlap_words: int = 80
    rag_top_k: int = 8

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def provider_key_available(self) -> bool:
        provider = self.due_diligence_provider.lower()
        if provider == "mock":
            return True
        if provider == "openai":
            return bool(self.openai_api_key)
        if provider == "anthropic":
            return bool(self.anthropic_api_key)
        if provider == "gemini":
            return bool(self.gemini_api_key or self.google_api_key)
        if provider == "openrouter":
            return bool(self.openrouter_api_key)
        return False

    def effective_model(self) -> str:
        provider = self.due_diligence_provider.lower()
        if provider == "openai":
            return self.openai_model
        if provider == "anthropic":
            return self.anthropic_model
        if provider in {"gemini", "google"}:
            return self.gemini_model
        if provider == "openrouter":
            return self.openrouter_model
        return self.due_diligence_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
