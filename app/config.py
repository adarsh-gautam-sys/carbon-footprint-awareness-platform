"""Centralised application configuration using pydantic-settings.

All environment variables are declared here with explicit types and defaults.
Import ``settings`` from this module instead of calling ``os.getenv`` directly.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Gemini AI ─────────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Google Cloud ──────────────────────────────────────────────────────────
    google_cloud_project: str = ""
    google_cloud_region: str = "us-central1"
    firestore_enabled: bool = False

    # ── Storage ───────────────────────────────────────────────────────────────
    local_data_dir: str = ""

    # ── Server ────────────────────────────────────────────────────────────────
    # Comma-separated allowed CORS origins.
    # Defaults to localhost dev ports — never "*" in any environment.
    allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
    ]
    port: int = 8080
    log_level: str = "INFO"

    # ── Concurrency ───────────────────────────────────────────────────────────
    # Maximum concurrent LLM calls — prevents 429 Resource Exhausted on free-tier keys.
    max_concurrent_llm_calls: int = 3

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_max_size: int = 256
    cache_ttl_seconds: int = 3600


settings = Settings()
