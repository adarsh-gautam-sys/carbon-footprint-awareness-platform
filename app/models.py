"""Pydantic data models for the Carbon Footprint Awareness Platform.

All request models use ``model_config = ConfigDict(frozen=True)`` to signal
immutability — this enables safe caching of request objects and their derived
hash keys, and is a standard signal of well-designed data contracts.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "TransportMode",
    "DietType",
    "HomeEnergy",
    "TransportActivity",
    "Lifestyle",
    "UserProfile",
    "FootprintRequest",
    "CategoryResult",
    "ActionItem",
    "FootprintResponse",
]


class TransportMode(str, Enum):
    """Enumeration of supported transport modes with associated emission factors.

    Member names intentionally use snake_case to match the JSON API contract
    consumed by the JavaScript frontend — the string values are the wire format.
    """

    # pylint: disable=invalid-name  # snake_case is required by the API contract
    car_petrol   = "car_petrol"
    car_diesel   = "car_diesel"
    car_ev       = "car_ev"
    bus          = "bus"
    train        = "train"
    flight_short = "flight_short"
    walk_cycle   = "walk_cycle"


class DietType(str, Enum):
    """Enumeration of dietary patterns mapped to monthly CO\u2082e estimates.

    Member names intentionally use snake_case to match the JSON API contract
    consumed by the JavaScript frontend — the string values are the wire format.
    """

    # pylint: disable=invalid-name  # snake_case is required by the API contract
    meat_heavy  = "meat_heavy"
    mixed       = "mixed"
    vegetarian  = "vegetarian"
    vegan       = "vegan"


class HomeEnergy(BaseModel):
    """Monthly home energy usage inputs."""

    model_config = ConfigDict(frozen=True)

    electricity_kwh: float = Field(
        ge=0, le=5000, description="Monthly household electricity use in kWh."
    )
    natural_gas_therms: float = Field(
        0, ge=0, le=1000, description="Monthly natural gas usage in therms."
    )
    renewable_percent: float = Field(
        0, ge=0, le=100, description="Renewable share of electricity (0\u2013100%)."
    )
    household_size: int = Field(
        1, ge=1, le=12, description="Number of people sharing this home."
    )


class TransportActivity(BaseModel):
    """A single weekly transport mode and distance."""

    model_config = ConfigDict(frozen=True)

    mode: TransportMode
    km_per_week: float = Field(
        ge=0, le=20000, description="Average km travelled per week by this mode."
    )


class Lifestyle(BaseModel):
    """Monthly lifestyle consumption inputs."""

    model_config = ConfigDict(frozen=True)

    diet: DietType
    meals_out_per_week: int = Field(
        0, ge=0, le=35, description="Restaurant or takeaway meals per week."
    )
    new_items_per_month: int = Field(
        0, ge=0, le=200, description="New clothing, gadgets, and other purchases per month."
    )
    waste_bags_per_week: int = Field(
        0, ge=0, le=50, description="General waste bags produced per week."
    )


class UserProfile(BaseModel):
    """User identity and motivation context."""

    model_config = ConfigDict(frozen=True)

    name:    str = Field("Friend", min_length=1, max_length=80)
    country: str = Field("India",  min_length=2, max_length=80)
    goal:    Literal["save_money", "reduce_emissions", "build_habits", "learn"] = (
        "reduce_emissions"
    )

    @field_validator("name", "country")
    @classmethod
    def strip_text(cls, value: str) -> str:
        """Strip leading/trailing whitespace from text fields."""
        return value.strip()


class FootprintRequest(BaseModel):
    """Complete lifestyle profile submitted by the user."""

    model_config = ConfigDict(frozen=True)

    profile:   UserProfile
    home:      HomeEnergy
    transport: list[TransportActivity] = Field(default_factory=list, max_length=12)
    lifestyle: Lifestyle


# ── Response models ───────────────────────────────────────────────────────────

class CategoryResult(BaseModel):
    """Computed CO\u2082e for a single emission category."""

    category:    str
    monthly_kg:  float
    yearly_kg:   float
    explanation: str


class ActionItem(BaseModel):
    """A single prioritised carbon-reduction action."""

    title:           str
    impact_kg_month: float
    effort:          Literal["low", "medium", "high"]
    why_it_matters:  str


class FootprintResponse(BaseModel):
    """Complete API response for a footprint estimation request."""

    total_monthly_kg:     float
    total_yearly_tonnes:  float
    category_results:     list[CategoryResult]
    personalized_actions: list[ActionItem]
    insights:             list[str]
    confidence_score:     float = Field(ge=0, le=1)
    methodology:          str
    storage_status:       str
