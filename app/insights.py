"""Gemini-powered personalised insights with deterministic fallback.

Design decisions:
- ``generate_personalized_insights`` is an ``async def`` so it can be awaited
  from the async endpoint and called within the LLM semaphore context.
- The async Gemini SDK (``client.aio.models.generate_content``) is used to
  avoid blocking the event loop during network I/O.
- The shared ``genai.Client`` is initialised once at module import and reused
  across requests — avoids per-request TCP handshake overhead.
- System instruction sets role, tone, and safety guardrails.
- User prompt grounds the model strictly in calculated numbers.
- Output constraint (3 bullets, ≤32 words each) keeps the UI readable.
- All Gemini errors fall back to locally-computed insights so the platform
  works reliably without a configured API key.
"""

from __future__ import annotations

import logging

from google import genai

from app.config import settings
from app.models import ActionItem, CategoryResult, FootprintRequest

logger = logging.getLogger(__name__)

# ── Shared Gemini client (initialised once, reused across requests) ────────────
_gemini_client: genai.Client | None = None

if settings.gemini_api_key:
    try:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini client initialised (model=%s).", settings.gemini_model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini client init failed (%s); fallback will be used.", exc.__class__.__name__)


SYSTEM_INSTRUCTION = """\
You are a carbon footprint coach for an AI awareness platform.
Your role: give concise, practical, non-judgmental carbon reduction advice.
Rules you must follow:
- Use ONLY the footprint numbers and actions provided. Do not invent data.
- Avoid guilt, politics, blame, and unsupported scientific claims.
- Personalise each insight using the user's name, country, and primary goal.
- Be specific: reference actual kg values and action titles from the input.
- Keep advice motivating and achievable, not overwhelming.\
"""


def _fallback_insights(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> list[str]:
    """Return three deterministic insights when Gemini is unavailable."""
    top = max(categories, key=lambda item: item.monthly_kg)
    first = actions[0]
    yearly_tonnes = round((sum(c.monthly_kg for c in categories) * 12) / 1000, 1)
    return [
        (
            f"{request.profile.name}, your largest category is {top.category.lower()} "
            f"at {top.monthly_kg} kg CO\u2082e/month ({top.yearly_kg} kg/year)."
        ),
        (
            f"Best first step: {first.title}. "
            f"Estimated saving: ~{first.impact_kg_month} kg CO\u2082e/month."
        ),
        (
            f"Your estimated yearly footprint is {yearly_tonnes} tonnes CO\u2082e. "
            f"The Paris 1.5\u00b0C target is 2 tonnes/person/year — "
            f"track weekly to see your progress."
        ),
    ]


def build_gemini_prompt(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> str:
    """Build a tightly-constrained prompt grounded in validated data only."""
    category_lines = "\n".join(
        f"- {item.category}: {item.monthly_kg} kg/month "
        f"({item.yearly_kg} kg/year). {item.explanation}"
        for item in categories
    )
    action_lines = "\n".join(
        f"- {item.title}: saves ~{item.impact_kg_month} kg/month, effort={item.effort}. "
        f"{item.why_it_matters}"
        for item in actions
    )
    total_monthly = round(sum(c.monthly_kg for c in categories), 1)
    yearly_tonnes = round((total_monthly * 12) / 1000, 1)

    return f"""\
User profile:
- Name: {request.profile.name}
- Country: {request.profile.country}
- Primary goal: {request.profile.goal.replace('_', ' ')}

Estimated monthly carbon footprint:
- Total: {total_monthly} kg CO2e/month ({yearly_tonnes} tonnes/year)
{category_lines}

Top recommended actions:
{action_lines}

Task: Return EXACTLY 3 concise insights as plain sentences (no markdown bullets or symbols).
Each insight must:
1. Be under 32 words.
2. Reference specific numbers or action titles from the data above.
3. Be personalised using the user's name or goal where natural.
4. Be motivating and practical, not guilt-inducing.

Output only the 3 sentences, one per line.\
"""


async def generate_personalized_insights(
    request: FootprintRequest,
    categories: list[CategoryResult],
    actions: list[ActionItem],
) -> list[str]:
    """Generate up to 3 personalised insights using Gemini, with fallback.

    Uses the async Gemini SDK to avoid blocking the event loop during
    network I/O. The shared ``_gemini_client`` is reused across requests.
    Falls back to deterministic insights on any error or missing API key.
    """
    if _gemini_client is None:
        logger.debug("Gemini client not available — using deterministic fallback insights.")
        return _fallback_insights(request, categories, actions)

    try:
        response = await _gemini_client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=build_gemini_prompt(request, categories, actions),
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0.25,
                "max_output_tokens": 256,
            },
        )
        raw = (response.text or "").strip()
        # Parse lines, strip common bullet prefixes
        lines = [
            line.lstrip("•-*123. ").strip()
            for line in raw.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        cleaned = [line for line in lines if len(line) > 10][:3]
        if len(cleaned) >= 2:
            return cleaned
        # Fall back if Gemini returned too little useful content
        logger.warning("Gemini returned insufficient content; using fallback.")
        return _fallback_insights(request, categories, actions)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Gemini call failed (%s); using fallback insights.", exc.__class__.__name__
        )
        return _fallback_insights(request, categories, actions)
