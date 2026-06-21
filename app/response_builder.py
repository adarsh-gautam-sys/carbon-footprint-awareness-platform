"""Shared factory for building ``FootprintResponse`` objects.

Both ``app.main`` (live endpoint) and ``app.cache`` (pre-seed) construct
``FootprintResponse`` instances with identical fields and the same
methodology string. Centralising this construction here eliminates
duplication and ensures the methodology text is always consistent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import (
    ActionItem,
    CategoryResult,
    FootprintResponse,
)

#: Methodology note appended to every response so users and evaluators
#: can audit the emission factor sources and calculation approach.
METHODOLOGY = (
    "CO\u2082e estimates use IPCC/EPA-aligned emission factors. "
    "Electricity is scaled by renewable share and split across household members. "
    "Transport factors are applied per km per week. "
    "Diet, meals out, purchases, and waste are combined into monthly lifestyle impact. "
    "Gemini AI personalises insight phrasing; it does not alter the numbers."
)


@dataclass(frozen=True, slots=True)
class ResponseComponents:
    """Typed container for all computed components needed to build a response.

    Using a dataclass avoids exceeding the pylint too-many-arguments limit
    while keeping the call sites explicit and keyword-safe.
    """

    total_monthly: float
    categories: list[CategoryResult]
    actions: list[ActionItem]
    insights: list[str]
    confidence_score: float
    storage_status: str


def build_footprint_response(components: ResponseComponents) -> FootprintResponse:
    """Construct a ``FootprintResponse`` from computed *components*.

    Args:
        components: A ``ResponseComponents`` dataclass with all required fields.

    Returns:
        A fully populated ``FootprintResponse`` ready to be returned from
        the API endpoint or stored in the TTL cache.
    """
    return FootprintResponse(
        total_monthly_kg=components.total_monthly,
        total_yearly_tonnes=round((components.total_monthly * 12) / 1000, 2),
        category_results=components.categories,
        personalized_actions=components.actions,
        insights=components.insights,
        confidence_score=components.confidence_score,
        methodology=METHODOLOGY,
        storage_status=components.storage_status,
    )
