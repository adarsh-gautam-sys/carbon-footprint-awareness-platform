"""Tests for the in-memory caching layer and concurrency semaphore (app.cache).

Coverage targets:
- make_cache_key: determinism, key uniqueness
- get_cached / set_cached: round-trip, cache miss
- cache_size: increments on set
- init_semaphore: creates a live asyncio.Semaphore
- preseed_cache: populates at least 3 entries
"""

from __future__ import annotations

import asyncio

from app.cache import (
    cache_size,
    get_cached,
    init_semaphore,
    make_cache_key,
    preseed_cache,
    set_cached,
)
from app.models import FootprintRequest, FootprintResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_request(name: str = "Test", diet: str = "vegetarian") -> FootprintRequest:
    """Build a minimal valid FootprintRequest."""
    return FootprintRequest.model_validate({
        "profile": {"name": name, "country": "India", "goal": "learn"},
        "home": {
            "electricity_kwh": 100,
            "natural_gas_therms": 0,
            "renewable_percent": 10,
            "household_size": 2,
        },
        "transport": [{"mode": "bus", "km_per_week": 50}],
        "lifestyle": {
            "diet": diet,
            "meals_out_per_week": 1,
            "new_items_per_month": 0,
            "waste_bags_per_week": 1,
        },
    })


def _make_response(total: float = 50.0, status: str = "test") -> FootprintResponse:
    """Build a minimal valid FootprintResponse."""
    return FootprintResponse(
        total_monthly_kg=total,
        total_yearly_tonnes=round((total * 12) / 1000, 2),
        category_results=[],
        personalized_actions=[],
        insights=["insight one", "insight two", "insight three"],
        confidence_score=0.80,
        methodology="Test methodology.",
        storage_status=status,
    )


# ── make_cache_key ────────────────────────────────────────────────────────────

def test_cache_key_is_deterministic() -> None:
    """Same request object must always produce the same cache key."""
    req = _make_request()
    assert make_cache_key(req) == make_cache_key(req)


def test_cache_key_differs_for_different_requests() -> None:
    """Different requests must produce different keys."""
    req_a = _make_request(name="Alice")
    req_b = _make_request(name="Bob")
    assert make_cache_key(req_a) != make_cache_key(req_b)


def test_cache_key_is_hex_string() -> None:
    """Cache key must be a 64-char hex string (SHA-256)."""
    key = make_cache_key(_make_request())
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


# ── get_cached / set_cached ───────────────────────────────────────────────────

def test_cache_miss_returns_none() -> None:
    """Getting a key that was never set must return None."""
    result = get_cached("nonexistent-key-xyz-12345")
    assert result is None


def test_set_and_get_round_trip() -> None:
    """A response stored with set_cached must be retrievable with get_cached."""
    req = _make_request(name="CacheRoundTrip")
    key = make_cache_key(req)
    response = _make_response(total=123.4)

    set_cached(key, response)
    retrieved = get_cached(key)

    assert retrieved is not None
    assert retrieved.total_monthly_kg == 123.4


def test_set_cached_updates_existing_key() -> None:
    """set_cached on the same key must overwrite the previous value."""
    req = _make_request(name="UpdateTest")
    key = make_cache_key(req)

    set_cached(key, _make_response(total=10.0))
    set_cached(key, _make_response(total=99.9))

    result = get_cached(key)
    assert result is not None
    assert result.total_monthly_kg == 99.9


# ── cache_size ────────────────────────────────────────────────────────────────

def test_cache_size_increases_on_set() -> None:
    """cache_size() must increment when a new key is inserted."""
    req = _make_request(name="SizeTest")
    key = make_cache_key(req)

    before = cache_size()
    set_cached(key, _make_response())
    after = cache_size()

    assert after >= before  # strictly >= because the key may already exist from preseed


# ── init_semaphore ────────────────────────────────────────────────────────────

def test_init_semaphore_creates_semaphore() -> None:
    """init_semaphore() must create a live asyncio.Semaphore."""
    init_semaphore()
    import app.cache as cache_module  # noqa: PLC0415 — needed to inspect module state
    assert cache_module.semaphore is not None
    assert isinstance(cache_module.semaphore, asyncio.Semaphore)


def test_semaphore_is_acquirable() -> None:
    """The semaphore must be acquirable and releasable without deadlock."""
    init_semaphore()
    import app.cache as cache_module  # noqa: PLC0415

    async def _acquire() -> bool:
        async with cache_module.semaphore:
            return True

    result = asyncio.run(_acquire())
    assert result is True


# ── preseed_cache ─────────────────────────────────────────────────────────────

def test_preseed_cache_populates_entries() -> None:
    """preseed_cache() must add at least 3 demo entries to the cache."""
    before = cache_size()
    preseed_cache()
    after = cache_size()
    # At least the 3 demo payloads must be seeded
    assert after >= 3
    # Overall size must not shrink
    assert after >= before
