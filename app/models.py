from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TransportMode(str, Enum):
    car_petrol = "car_petrol"
    car_diesel = "car_diesel"
    car_ev = "car_ev"
    bus = "bus"
    train = "train"
    flight_short = "flight_short"
    walk_cycle = "walk_cycle"


class DietType(str, Enum):
    meat_heavy = "meat_heavy"
    mixed = "mixed"
    vegetarian = "vegetarian"
    vegan = "vegan"


class HomeEnergy(BaseModel):
    electricity_kwh: float = Field(ge=0, le=5000, description="Monthly household electricity use.")
    natural_gas_therms: float = Field(0, ge=0, le=1000, description="Monthly natural gas usage.")
    renewable_percent: float = Field(0, ge=0, le=100, description="Renewable share of electricity.")
    household_size: int = Field(1, ge=1, le=12)


class TransportActivity(BaseModel):
    mode: TransportMode
    km_per_week: float = Field(ge=0, le=20000)


class Lifestyle(BaseModel):
    diet: DietType
    meals_out_per_week: int = Field(0, ge=0, le=35)
    new_items_per_month: int = Field(0, ge=0, le=200, description="Clothes, gadgets, and other new purchases.")
    waste_bags_per_week: int = Field(0, ge=0, le=50)


class UserProfile(BaseModel):
    name: str = Field("Friend", min_length=1, max_length=80)
    country: str = Field("India", min_length=2, max_length=80)
    goal: Literal["save_money", "reduce_emissions", "build_habits", "learn"] = "reduce_emissions"

    @field_validator("name", "country")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class FootprintRequest(BaseModel):
    profile: UserProfile
    home: HomeEnergy
    transport: list[TransportActivity] = Field(default_factory=list, max_length=12)
    lifestyle: Lifestyle


class CategoryResult(BaseModel):
    category: str
    monthly_kg: float
    yearly_kg: float
    explanation: str


class ActionItem(BaseModel):
    title: str
    impact_kg_month: float
    effort: Literal["low", "medium", "high"]
    why_it_matters: str


class FootprintResponse(BaseModel):
    total_monthly_kg: float
    total_yearly_tonnes: float
    category_results: list[CategoryResult]
    personalized_actions: list[ActionItem]
    insights: list[str]
    confidence_score: float = Field(ge=0, le=1)
    methodology: str
    storage_status: str
