from fastapi.testclient import TestClient

from app.main import app


def test_footprint_endpoint_returns_structured_response(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    client = TestClient(app)

    response = client.post(
        "/api/footprint",
        json={
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
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_monthly_kg"] > 0
    assert len(data["category_results"]) == 3
    assert len(data["personalized_actions"]) >= 1
    assert data["storage_status"].startswith("saved_locally:")
