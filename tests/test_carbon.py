"""Unit tests for the carbon calculation and action generation engine."""

import pytest

from app.carbon import (
    ELECTRICITY_KG_PER_KWH,
    NATURAL_GAS_KG_PER_THERM,
    WEEKS_PER_MONTH,
    calculate_categories,
    calculate_confidence,
    calculate_home_kg,
    calculate_lifestyle_kg,
    calculate_transport_kg,
    generate_actions,
)
from app.models import FootprintRequest


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_request(**overrides) -> FootprintRequest:
    base = {
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
    base.update(overrides)
    return FootprintRequest.model_validate(base)


# ── calculate_categories ──────────────────────────────────────────────────────

def test_categories_returns_three_named_groups():
    categories = calculate_categories(make_request())

    assert [c.category for c in categories] == [
        "Home energy",
        "Transport",
        "Food and lifestyle",
    ]


def test_all_categories_have_positive_monthly_kg():
    categories = calculate_categories(make_request())
    for cat in categories:
        assert cat.monthly_kg >= 0


def test_yearly_kg_is_twelve_times_monthly():
    categories = calculate_categories(make_request())
    for cat in categories:
        assert abs(cat.yearly_kg - round(cat.monthly_kg * 12, 1)) < 0.5  # tolerance for double-rounding


def test_all_categories_have_explanation():
    categories = calculate_categories(make_request())
    for cat in categories:
        assert len(cat.explanation) > 10


# ── calculate_home_kg ─────────────────────────────────────────────────────────

def test_full_renewable_electricity_means_zero_electricity_emissions():
    req = make_request(home={
        "electricity_kwh": 300,
        "natural_gas_therms": 0,
        "renewable_percent": 100,
        "household_size": 1,
    })
    assert calculate_home_kg(req) == 0.0


def test_household_size_divides_emissions():
    req_1 = make_request(home={
        "electricity_kwh": 200,
        "natural_gas_therms": 0,
        "renewable_percent": 0,
        "household_size": 1,
    })
    req_2 = make_request(home={
        "electricity_kwh": 200,
        "natural_gas_therms": 0,
        "renewable_percent": 0,
        "household_size": 2,
    })
    assert abs(calculate_home_kg(req_1) - calculate_home_kg(req_2) * 2) < 0.01


def test_gas_adds_to_home_emissions():
    req_no_gas = make_request(home={
        "electricity_kwh": 100,
        "natural_gas_therms": 0,
        "renewable_percent": 0,
        "household_size": 1,
    })
    req_gas = make_request(home={
        "electricity_kwh": 100,
        "natural_gas_therms": 10,
        "renewable_percent": 0,
        "household_size": 1,
    })
    expected_gas = 10 * NATURAL_GAS_KG_PER_THERM
    assert abs(calculate_home_kg(req_gas) - calculate_home_kg(req_no_gas) - expected_gas) < 0.01


# ── calculate_transport_kg ────────────────────────────────────────────────────

def test_walking_cycling_has_zero_emissions():
    req = make_request(transport=[{"mode": "walk_cycle", "km_per_week": 9999}])
    assert calculate_transport_kg(req) == 0.0


def test_no_transport_means_zero():
    req = make_request(transport=[])
    assert calculate_transport_kg(req) == 0.0


def test_petrol_car_higher_than_train_same_distance():
    req_car   = make_request(transport=[{"mode": "car_petrol", "km_per_week": 100}])
    req_train = make_request(transport=[{"mode": "train",      "km_per_week": 100}])
    assert calculate_transport_kg(req_car) > calculate_transport_kg(req_train)


# ── calculate_lifestyle_kg ────────────────────────────────────────────────────

def test_vegan_diet_lower_than_meat_heavy():
    req_meat  = make_request(lifestyle={"diet": "meat_heavy", "meals_out_per_week": 0, "new_items_per_month": 0, "waste_bags_per_week": 0})
    req_vegan = make_request(lifestyle={"diet": "vegan",      "meals_out_per_week": 0, "new_items_per_month": 0, "waste_bags_per_week": 0})
    assert calculate_lifestyle_kg(req_meat) > calculate_lifestyle_kg(req_vegan)


def test_zero_lifestyle_extras_returns_just_diet():
    req = make_request(lifestyle={
        "diet": "vegan",
        "meals_out_per_week": 0,
        "new_items_per_month": 0,
        "waste_bags_per_week": 0,
    })
    from app.carbon import DIET_FACTORS_KG_PER_MONTH
    from app.models import DietType
    assert abs(calculate_lifestyle_kg(req) - DIET_FACTORS_KG_PER_MONTH[DietType.vegan]) < 0.01


# ── generate_actions ──────────────────────────────────────────────────────────

def test_car_user_gets_transport_action():
    req = make_request()
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    assert any("car trip" in a.title.lower() or "transport" in a.title.lower() for a in actions)


def test_actions_sorted_descending():
    req = make_request()
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    impacts = [a.impact_kg_month for a in actions]
    assert impacts == sorted(impacts, reverse=True)


def test_max_four_actions_returned():
    req = make_request(
        home={"electricity_kwh": 500, "natural_gas_therms": 20, "renewable_percent": 0, "household_size": 1},
        transport=[{"mode": "car_petrol", "km_per_week": 200}],
        lifestyle={"diet": "meat_heavy", "meals_out_per_week": 10, "new_items_per_month": 5, "waste_bags_per_week": 5},
    )
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    assert len(actions) <= 4


def test_low_impact_profile_gets_single_focused_goal():
    req = make_request(
        home={"electricity_kwh": 50, "natural_gas_therms": 0, "renewable_percent": 100, "household_size": 2},
        transport=[{"mode": "walk_cycle", "km_per_week": 20}],
        lifestyle={"diet": "vegan", "meals_out_per_week": 0, "new_items_per_month": 0, "waste_bags_per_week": 0},
    )
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    assert len(actions) == 1
    assert "10%" in actions[0].title


def test_effort_values_are_valid():
    req = make_request()
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    for action in actions:
        assert action.effort in {"low", "medium", "high"}


def test_all_actions_have_why_it_matters():
    req = make_request()
    categories = calculate_categories(req)
    actions = generate_actions(req, categories)
    for action in actions:
        assert len(action.why_it_matters) > 10


# ── calculate_confidence ──────────────────────────────────────────────────────

def test_confidence_score_in_bounds():
    req = make_request()
    score = calculate_confidence(req)
    assert 0.0 <= score <= 1.0


def test_confidence_higher_with_more_data():
    minimal = make_request(transport=[])
    detailed = make_request(
        home={"electricity_kwh": 200, "natural_gas_therms": 5, "renewable_percent": 25, "household_size": 3},
        transport=[{"mode": "car_petrol", "km_per_week": 80}],
    )
    assert calculate_confidence(detailed) >= calculate_confidence(minimal)


def test_confidence_capped_at_0_92():
    """Confidence must never reach 1.0 — inherent estimation uncertainty."""
    req = make_request(
        home={"electricity_kwh": 250, "natural_gas_therms": 8, "renewable_percent": 20, "household_size": 3},
        transport=[{"mode": "car_petrol", "km_per_week": 100}],
        lifestyle={"diet": "mixed", "meals_out_per_week": 3, "new_items_per_month": 2, "waste_bags_per_week": 2},
    )
    assert calculate_confidence(req) <= 0.92
