from app.carbon import calculate_categories, generate_actions
from app.insights import generate_personalized_insights
from app.models import FootprintRequest


def test_fallback_insights_work_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = FootprintRequest.model_validate(
        {
            "profile": {"name": "Adarsh", "country": "India", "goal": "learn"},
            "home": {
                "electricity_kwh": 120,
                "natural_gas_therms": 0,
                "renewable_percent": 20,
                "household_size": 3,
            },
            "transport": [{"mode": "bus", "km_per_week": 80}],
            "lifestyle": {
                "diet": "vegetarian",
                "meals_out_per_week": 1,
                "new_items_per_month": 1,
                "waste_bags_per_week": 1,
            },
        }
    )
    categories = calculate_categories(request)
    actions = generate_actions(request, categories)

    insights = generate_personalized_insights(request, categories, actions)

    assert len(insights) == 3
    assert "Adarsh" in insights[0]
