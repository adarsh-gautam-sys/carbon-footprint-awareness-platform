"""Integration tests for the /api/footprint endpoint."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Use a temp directory inside the project so Windows user-profile
# tmp_path permission errors (WinError 5) are avoided.
_TEST_DATA_DIR = Path(__file__).resolve().parent.parent / ".pytest_tmp_data"


@pytest.fixture(autouse=True)
def _setup_data_dir(monkeypatch):
    _TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCAL_DATA_DIR", str(_TEST_DATA_DIR))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield
    # Clean up JSONL to keep test directory tidy
    for f in _TEST_DATA_DIR.glob("*.jsonl"):
        f.unlink(missing_ok=True)


@pytest.fixture()
def client():
    return TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_PAYLOAD = {
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

def test_footprint_returns_structured_response(client):
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


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_serves_html(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


# ── Validation / edge cases ───────────────────────────────────────────────────

def test_missing_required_field_returns_422(client):
    bad_payload = {k: v for k, v in SAMPLE_PAYLOAD.items() if k != "home"}
    response = client.post("/api/footprint", json=bad_payload)
    assert response.status_code == 422


def test_electricity_above_limit_returns_422(client):
    payload = SAMPLE_PAYLOAD | {
        "home": SAMPLE_PAYLOAD["home"] | {"electricity_kwh": 99999}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


def test_invalid_diet_value_returns_422(client):
    payload = SAMPLE_PAYLOAD | {
        "lifestyle": SAMPLE_PAYLOAD["lifestyle"] | {"diet": "carnivore"}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


def test_name_trimmed_and_used_in_insights(client):
    payload = SAMPLE_PAYLOAD | {
        "profile": {"name": "  Priya  ", "country": "India", "goal": "learn"}
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200
    insights = response.json()["insights"]
    # Fallback insights should use the trimmed name
    assert any("Priya" in i for i in insights)


def test_zero_transport_handled(client):
    payload = SAMPLE_PAYLOAD | {"transport": []}
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200
    assert response.json()["total_monthly_kg"] > 0


def test_vegan_no_car_produces_focused_goal(client):
    """Very low impact profile should fall back to a focused goal action."""
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


def test_actions_sorted_descending_by_impact(client):
    response = client.post("/api/footprint", json=SAMPLE_PAYLOAD)
    actions = response.json()["personalized_actions"]
    impacts = [a["impact_kg_month"] for a in actions]
    assert impacts == sorted(impacts, reverse=True)


def test_max_transport_modes(client):
    """12 transport modes in the list should be accepted."""
    payload = SAMPLE_PAYLOAD | {
        "transport": [{"mode": "bus", "km_per_week": 10}] * 12
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 200


def test_too_many_transport_modes_returns_422(client):
    payload = SAMPLE_PAYLOAD | {
        "transport": [{"mode": "bus", "km_per_week": 1}] * 13
    }
    response = client.post("/api/footprint", json=payload)
    assert response.status_code == 422


def test_security_headers_are_present(client):
    response = client.get("/")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert "content-security-policy" in response.headers
    assert "referrer-policy" in response.headers

