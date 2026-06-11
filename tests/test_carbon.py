from app.carbon import calculate_categories, calculate_confidence, generate_actions
from app.models import FootprintRequest


def sample_request(**overrides):
    payload = {
        "profile": {"name": "Adarsh", "country": "India", "goal": "reduce_emissions"},
        "home": {
            "electricity_kwh": 220,
            "natural_gas_therms": 0,
            "renewable_percent": 10,
            "household_size": 2,
        },
        "transport": [{"mode": "car_petrol", "km_per_week": 100}],
        "lifestyle": {
            "diet": "mixed",
            "meals_out_per_week": 2,
            "new_items_per_month": 2,
            "waste_bags_per_week": 1,
        },
    }
    payload.update(overrides)
    return FootprintRequest.model_validate(payload)


def test_calculate_categories_returns_transparent_breakdown():
    categories = calculate_categories(sample_request())

    assert [item.category for item in categories] == [
        "Home energy",
        "Transport",
        "Food and lifestyle",
    ]
    assert sum(item.monthly_kg for item in categories) > 0
    assert all(item.explanation for item in categories)


def test_transport_action_is_generated_for_car_use():
    request = sample_request()
    categories = calculate_categories(request)
    actions = generate_actions(request, categories)

    assert any("car trip" in item.title for item in actions)
    assert actions[0].impact_kg_month >= actions[-1].impact_kg_month


def test_low_impact_profile_gets_focused_goal():
    request = sample_request(
        home={
            "electricity_kwh": 70,
            "natural_gas_therms": 0,
            "renewable_percent": 100,
            "household_size": 2,
        },
        transport=[{"mode": "walk_cycle", "km_per_week": 50}],
        lifestyle={
            "diet": "vegan",
            "meals_out_per_week": 0,
            "new_items_per_month": 0,
            "waste_bags_per_week": 0,
        },
    )
    categories = calculate_categories(request)
    actions = generate_actions(request, categories)

    assert len(actions) == 1
    assert "10% reduction goal" in actions[0].title


def test_confidence_score_stays_bounded():
    score = calculate_confidence(sample_request())

    assert 0 <= score <= 1
    assert score >= 0.8
