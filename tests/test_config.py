"""Tests for environment variable loading via pydantic-settings (app.config).

These tests verify that:
- All required settings have sensible, secure defaults.
- Settings correctly read from environment variables.
- CORS origins never include a wildcard by default.
- Concurrency and cache limits are positive integers.
"""

from __future__ import annotations

import importlib

import pytest


# ── Default value assertions ──────────────────────────────────────────────────

def test_default_gemini_model() -> None:
    """Gemini model defaults to a known, fast model."""
    from app.config import settings
    assert settings.gemini_model == "gemini-2.0-flash"


def test_default_gemini_api_key_is_empty() -> None:
    """API key must default to empty string — never a hardcoded secret."""
    from app.config import settings
    assert settings.gemini_api_key == ""


def test_default_allowed_origins_never_wildcard() -> None:
    """CORS origins must never include '*' by default — security requirement."""
    from app.config import settings
    assert "*" not in settings.allowed_origins


def test_default_allowed_origins_are_localhost() -> None:
    """Default origins must be localhost development addresses."""
    from app.config import settings
    for origin in settings.allowed_origins:
        assert "localhost" in origin or "127.0.0.1" in origin, (
            f"Non-localhost origin '{origin}' found in defaults — use env var to add production origins."
        )


def test_default_firestore_disabled() -> None:
    """Firestore is disabled by default — local JSONL is the dev fallback."""
    from app.config import settings
    assert settings.firestore_enabled is False


def test_default_max_concurrent_llm_calls() -> None:
    """Semaphore limit must be a positive integer."""
    from app.config import settings
    assert settings.max_concurrent_llm_calls >= 1


def test_default_cache_max_size() -> None:
    """Cache max size must be a positive integer."""
    from app.config import settings
    assert settings.cache_max_size > 0


def test_default_cache_ttl_seconds() -> None:
    """Cache TTL must be positive."""
    from app.config import settings
    assert settings.cache_ttl_seconds > 0


def test_default_port() -> None:
    """Default port must match Cloud Run convention."""
    from app.config import settings
    assert settings.port == 8080


# ── Environment variable override ─────────────────────────────────────────────

def test_gemini_model_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    """GEMINI_MODEL env var must override the default."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    import app.config as cfg
    importlib.reload(cfg)
    assert cfg.Settings().gemini_model == "gemini-2.5-flash"
    # Restore original module state
    importlib.reload(cfg)


def test_allowed_origins_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    """ALLOWED_ORIGINS list env var must override the default list."""
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://my-app.run.app"]')
    import app.config as cfg
    importlib.reload(cfg)
    s = cfg.Settings()
    assert "https://my-app.run.app" in s.allowed_origins
    importlib.reload(cfg)


def test_firestore_enabled_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    """FIRESTORE_ENABLED=true must parse to boolean True."""
    monkeypatch.setenv("FIRESTORE_ENABLED", "true")
    import app.config as cfg
    importlib.reload(cfg)
    assert cfg.Settings().firestore_enabled is True
    importlib.reload(cfg)


def test_log_level_default() -> None:
    """Log level defaults to INFO."""
    from app.config import settings
    assert settings.log_level == "INFO"
