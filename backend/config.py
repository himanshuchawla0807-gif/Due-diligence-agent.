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
    host: str = "127.0.0.1"
    port: int = 8102
    cors_origins: str = "http://localhost:3000,http://localhost:5174"

    due_diligence_provider: str = "gemini"
    due_diligence_model: str = "gemini-3.8-flash"
    due_diligence_risk_model: str = "gemini-3.8-flash"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5.5"
    openai_reasoning_effort: Optional[str] = "medium"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-haiku-latest"
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.8-flash"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = ""

    storage_provider: str = "local"
    local_storage_dir: Path = Path("./storage")
    session_store: Path = Path("./storage/sessions.json")
    max_upload_mb: int = 100
    rag_storage_dir: Path = Path("./storage/rag")
    default_rag_source_dir: Optional[Path] = None
    local_embedding_provider: str = "auto"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    local_embedding_dimensions: int = 384
    local_embedding_batch_size: int = 32
    rag_chunk_words: int = 420
    rag_chunk_overlap_words: int = 80
    rag_top_k: int = 12
    rag_report_top_k: int = 64
    rag_file_query_limit: int = 60
    due_diligence_multi_pass: bool = True
    due_diligence_domain_top_k: int = 18
    due_diligence_max_findings: int = 80
    auth_mode: str = "local"
    firebase_project_id: Optional[str] = None
    max_upload_files: int = 50
    max_upload_total_mb: int = 200
    analysis_concurrency: int = 3
    analysis_timeout_seconds: float = 180.0
    provider_timeout_seconds: float = 60.0
    max_prompt_characters: int = 100000

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
