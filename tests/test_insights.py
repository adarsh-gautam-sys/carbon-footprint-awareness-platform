"""Tests for the Gemini insights adapter and deterministic fallback."""

import pytest

from app.carbon import calculate_categories, generate_actions
from app.insights import _fallback_insights, build_gemini_prompt, generate_personalized_insights
from app.models import FootprintRequest


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_request(name: str = "Adarsh") -> FootprintRequest:
    return FootprintRequest.model_validate({
        "profile": {"name": name, "country": "India", "goal": "learn"},
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
    })


# ── Fallback insights ─────────────────────────────────────────────────────────

def test_fallback_returns_three_insights(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    insights = generate_personalized_insights(req, cats, acts)

    assert len(insights) == 3
    assert all(isinstance(i, str) and len(i) > 5 for i in insights)


def test_fallback_first_insight_contains_name(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    req = make_request(name="Kavya")
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    insights = generate_personalized_insights(req, cats, acts)

    assert "Kavya" in insights[0]


def test_fallback_references_largest_category(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    insights = _fallback_insights(req, cats, acts)
    top = max(cats, key=lambda c: c.monthly_kg)

    assert top.category.lower() in insights[0].lower()


def test_fallback_third_insight_mentions_paris_target(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    insights = _fallback_insights(req, cats, acts)

    # Third insight should mention the 2 tonne Paris target
    assert "2" in insights[2] or "paris" in insights[2].lower() or "1.5" in insights[2]


# ── Prompt builder ────────────────────────────────────────────────────────────

def test_prompt_contains_name_country_goal():
    req = make_request(name="Raj")
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    prompt = build_gemini_prompt(req, cats, acts)

    assert "Raj" in prompt
    assert "India" in prompt
    assert "learn" in prompt


def test_prompt_contains_kg_values():
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    prompt = build_gemini_prompt(req, cats, acts)

    # Should include numeric totals
    assert "kg" in prompt
    assert "month" in prompt.lower()


def test_prompt_contains_all_three_categories():
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    prompt = build_gemini_prompt(req, cats, acts)

    for cat in cats:
        assert cat.category in prompt


# ── Gemini failure modes ──────────────────────────────────────────────────────

def test_invalid_api_key_falls_back_gracefully(monkeypatch):
    """Even with an invalid key, the function must return 3 insights, not raise."""
    monkeypatch.setenv("GEMINI_API_KEY", "invalid-key-for-testing")
    req = make_request()
    cats = calculate_categories(req)
    acts = generate_actions(req, cats)

    insights = generate_personalized_insights(req, cats, acts)

    assert len(insights) == 3
    assert all(len(i) > 5 for i in insights)
