import os

from google import genai

from app.models import ActionItem, CategoryResult, FootprintRequest


SYSTEM_INSTRUCTION = """You are a carbon footprint coach.
Give concise, practical, non-judgmental advice.
Avoid guilt, politics, and unsupported claims.
Personalize recommendations from the provided footprint numbers only."""


def _fallback_insights(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> list[str]:
    top = max(categories, key=lambda item: item.monthly_kg)
    first_action = actions[0]
    return [
        f"{request.profile.name}, your largest estimated category is {top.category.lower()} at {top.monthly_kg} kg CO2e per month.",
        f"Start with: {first_action.title}. Estimated saving: {first_action.impact_kg_month} kg CO2e per month.",
        "Track the same inputs weekly; trend direction is more useful than a single perfect number.",
    ]


def build_gemini_prompt(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> str:
    category_text = "\n".join(
        f"- {item.category}: {item.monthly_kg} kg/month ({item.explanation})"
        for item in categories
    )
    action_text = "\n".join(
        f"- {item.title}: saves about {item.impact_kg_month} kg/month, effort {item.effort}"
        for item in actions
    )
    return f"""
User: {request.profile.name}
Country: {request.profile.country}
Goal: {request.profile.goal}

Estimated monthly categories:
{category_text}

Candidate actions:
{action_text}

Return exactly 3 short bullet-style insights. Each insight must be under 28 words.
"""


def generate_personalized_insights(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> list[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_insights(request, categories, actions)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=build_gemini_prompt(request, categories, actions),
            config={"system_instruction": SYSTEM_INSTRUCTION, "temperature": 0.3},
        )
        text = response.text or ""
        lines = [line.strip("-• ").strip() for line in text.splitlines() if line.strip()]
        return lines[:3] or _fallback_insights(request, categories, actions)
    except Exception:
        return _fallback_insights(request, categories, actions)
