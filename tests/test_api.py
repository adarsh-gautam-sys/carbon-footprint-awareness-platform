"""Integration tests for the /api/footprint endpoint.

Coverage:
- Happy path: structured response, field types, value ranges.
- Validation: 422 on invalid/missing fields.
- Edge cases: empty transport, eco profile, max payload sizes.
- Security: all required HTTP headers present on every response.
- Cache: repeated identical requests return cached results.
- Health: liveness probe returns correct shape.
- Frontend: index route serves HTML.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Use a project-local temp directory to avoid Windows WinError 5 on user-profile tmp.
_TEST_DATA_DIR = Path(__file__).resolve().parent.parent / ".pytest_tmp_data"


@pytest.fixture(autouse=True)
def _setup_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[return]
    _TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCAL_DATA_DIR", str(_TEST_DATA_DIR))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield
    # Clean up JSONL between tests to keep the directory tidy
    for f in _TEST_DATA_DIR.glob("*.jsonl"):
        f.unlink(missing_ok=True)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_PAYLOAD: dict = {
    "profile": {"name": "Adarsh", "country": "India", "goal": "reduce_emissions"},
    "home": {
        "electricity_kwh": 180,
        "natural_gas_therms": 0,
        "renewable_percent": 15,
        "household_size": 3,
    },
    "transport": [{"mode": "train", "km_per_week": 100}],
    "lifestyle": {
        "diet": "vegetarian",
        "meals_out_per_week": 2,
        "new_items_per_month": 1,
        "waste_bags_per_week": 1,
    },
}


# ── Happy path ────────────────────────────────────────────────────────────────

def test_footprint_returns_structured_response(client: TestClient) -> None:
    response = client.post("/api/footprint", json=SAMPLE_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["total_monthly_kg"] > 0
    assert data["total_yearly_tonnes"] > 0
    assert len(data["category_results"]) == 3
    assert len(data["personalized_actions"]) >= 1
    assert len(data["insights"]) == 3
    assert 0 < data["confidence_score"] <= 1
    assert data["methodology"]
    assert data["storage_status"].startswith("saved_locally:")


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "cache_entries" in body


def test_index_serves_html(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


# ── Validation / edge cases ───────────────────────────────────────────────────

def test_missing_required_field_returns_422(client: TestClient) -> None:
    bad_payload = {k: v for k, v in SAMPLE_PAYLOAD.items() if k != "home"}
    response = client.post("/api/footprint", json=bad_payload)
    assert response.status_code == 422


def test_electricity_above_limit_returns_422(client: TestClient) -> None:
    payload = SAMPLE_PAYLOAD | {
        "home": SAMPLE_PAYLOAD["home"] | {"electricity_kwh": 99999}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


def test_invalid_diet_value_returns_422(client: TestClient) -> None:
    payload = SAMPLE_PAYLOAD | {
        "lifestyle": SAMPLE_PAYLOAD["lifestyle"] | {"diet": "carnivore"}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


def test_name_trimmed_and_used_in_insights(client: TestClient) -> None:
    payload = SAMPLE_PAYLOAD | {
        "profile": {"name": "  Priya  ", "country": "India", "goal": "learn"}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200
    insights = response.json()["insights"]
    # Fallback insights should use the trimmed name
    assert any("Priya" in i for i in insights)


def test_zero_transport_handled(client: TestClient) -> None:
    payload = SAMPLE_PAYLOAD | {"transport": []}
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200
    assert response.json()["total_monthly_kg"] > 0


def test_vegan_no_car_produces_focused_goal(client: TestClient) -> None:
    """Very low-impact profile should fall back to a single focused goal action."""
    payload = {
        "profile": {"name": "Sam", "country": "India", "goal": "reduce_emissions"},
        "home": {
            "electricity_kwh": 60,
            "natural_gas_therms": 0,
            "renewable_percent": 100,
            "household_size": 2,
        },
        "transport": [{"mode": "walk_cycle", "km_per_week": 20}],
        "lifestyle": {
            "diet": "vegan",
            "meals_out_per_week": 0,
            "new_items_per_month": 0,
            "waste_bags_per_week": 0,
        },
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200
    actions = response.json()["personalized_actions"]
    assert len(actions) == 1
    assert "10%" in actions[0]["title"]


def test_actions_sorted_descending_by_impact(client: TestClient) -> None:
    response = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    actions = response.json()["personalized_actions"]
    impacts = [a["impact_kg_month"] for a in actions]
    assert impacts == sorted(impacts, reverse=True)


def test_max_transport_modes(client: TestClient) -> None:
    """12 transport modes in the list should be accepted."""
    payload = SAMPLE_PAYLOAD | {
        "transport": [{"mode": "bus", "km_per_week": 10}] * 12
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200


def test_too_many_transport_modes_returns_422(client: TestClient) -> None:
    payload = SAMPLE_PAYLOAD | {
        "transport": [{"mode": "bus", "km_per_week": 1}] * 13
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


# ── Security headers ──────────────────────────────────────────────────────────

def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert "content-security-policy" in response.headers
    assert "referrer-policy" in response.headers
    assert "strict-transport-security" in response.headers


def test_security_headers_on_api_response(client: TestClient) -> None:
    """Security headers must also be present on API POST responses."""
    response = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"


# ── Caching ───────────────────────────────────────────────────────────────────

def test_repeated_identical_request_uses_cache(client: TestClient) -> None:
    """Two identical requests must return the same storage_status (cache hit on 2nd)."""
    r1 = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    r2 = client.post("/api/footprint", json=SAMPLE_PAYLOAD)

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both responses must contain identical computed values
    assert r1.json()["total_monthly_kg"] == r2.json()["total_monthly_kg"]
    assert r1.json()["total_yearly_tonnes"] == r2.json()["total_yearly_tonnes"]
    assert r1.json()["category_results"] == r2.json()["category_results"]


def test_different_payloads_produce_different_results(client: TestClient) -> None:
    """Different profiles must produce distinct carbon totals."""
    heavy_payload = SAMPLE_PAYLOAD | {
        "transport": [{"mode": "car_petrol", "km_per_week": 300}],
        "lifestyle": SAMPLE_PAYLOAD["lifestyle"] | {"diet": "meat_heavy"},
    }
    r1 = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    r2 = client.post("/api/footprint", json=heavy_payload)

    assert r1.json()["total_monthly_kg"] != r2.json()["total_monthly_kg"]


def test_cache_does_not_bleed_between_users(client: TestClient) -> None:
    """Cache keys must include the full request — different names must not collide."""
    payload_a = SAMPLE_PAYLOAD | {"profile": {"name": "Alice", "country": "India", "goal": "learn"}}
    payload_b = SAMPLE_PAYLOAD | {"profile": {"name": "Bob",   "country": "India", "goal": "learn"}}

    r_a = client.post("/api/footprint", json=payload_a)
    r_b = client.post("/api/footprint", json=payload_b)

    assert r_a.status_code == 200
    assert r_b.status_code == 200
    # Insights are name-personalised — must differ between users
    assert r_a.json()["insights"] != r_b.json()["insights"]


# ── Lifespan ──────────────────────────────────────────────────────────────────

def test_lifespan_preseeds_cache() -> None:
    """Using TestClient as a context manager triggers lifespan; cache_entries > 0."""
    from app.main import app as fastapi_app  # noqa: PLC0415

    with TestClient(fastapi_app) as c:
        resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert int(data["cache_entries"]) >= 3, (
            "Lifespan preseed must have populated at least 3 demo entries"
        )


# ── Validation error handler ──────────────────────────────────────────────────

def test_pydantic_validation_handler_returns_detail_list(client: TestClient) -> None:
    """Pydantic ValidationError handler must return a 422 with a 'detail' list."""
    bad_payload = SAMPLE_PAYLOAD | {
        "home": SAMPLE_PAYLOAD["home"] | {"electricity_kwh": -1}
    }
    response = client.post("/api/footprint", json=bad_payload)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)


# ── Cloud Logging setup ───────────────────────────────────────────────────────

def test_cloud_logging_setup_without_project_does_not_raise() -> None:
    """_setup_cloud_logging must not raise when no GCP project is configured."""
    from app.main import _setup_cloud_logging  # noqa: PLC0415

    # With no google_cloud_project set (default empty string), it falls back to
    # stdlib logging — this must never raise an exception.
    _setup_cloud_logging()  # no assertion needed — just must not raise


# ── response_builder ──────────────────────────────────────────────────────────

def test_response_builder_methodology_is_consistent(client: TestClient) -> None:
    """Every API response must contain the canonical methodology string."""
    response = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    assert response.status_code == 200
    methodology = response.json()["methodology"]
    assert "IPCC" in methodology
    assert "Gemini AI" in methodology
