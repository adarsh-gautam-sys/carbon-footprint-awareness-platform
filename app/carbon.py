"""Carbon calculation engine.

Emission factors:
- Transport: IPCC/DEFRA 2023 lifecycle averages (kg CO2e per passenger-km).
- Electricity: India grid-average 0.71 kg CO2e/kWh (CEA 2022-23), scaled by
  renewable share supplied by user.
- Natural gas: EPA factor 5.3 kg CO2e/therm.
- Diet: GHG equivalents from Oxford University food system research (Poore &
  Nemecek 2018), adapted to monthly estimates.
- Restaurant meals, consumer goods, and waste: EPA WARM model and lifecycle
  assessment averages.

All factors are explicitly documented so users and evaluators can audit them.

Performance notes:
- ``get_electricity_factor`` and ``get_diet_factors`` are wrapped with
  ``functools.lru_cache`` because they are pure functions called on every
  request with a small, bounded set of inputs.
"""

from __future__ import annotations

import functools

from app.models import ActionItem, CategoryResult, DietType, FootprintRequest, TransportMode

# ── Emission factors ──────────────────────────────────────────────────────────

TRANSPORT_FACTORS_KG_PER_KM: dict[TransportMode, float] = {
    TransportMode.car_petrol:    0.192,   # DEFRA 2023 average medium petrol car
    TransportMode.car_diesel:    0.171,   # DEFRA 2023 average medium diesel car
    TransportMode.car_ev:        0.053,   # UK/India grid-average EV lifecycle
    TransportMode.bus:           0.089,   # Average city/intercity bus
    TransportMode.train:         0.041,   # Average rail (mixed electric/diesel)
    TransportMode.flight_short:  0.255,   # Short-haul incl. radiative forcing ×1.9
    TransportMode.walk_cycle:    0.000,   # Zero operational emissions
}

# Grid electricity carbon intensity (kg CO2e per kWh)
# Sources: India CEA 2022-23 (0.71), US EPA eGRID 2022 (0.37), UK DESNZ 2023 (0.18), China MEE (0.58)
ELECTRICITY_BY_COUNTRY: dict[str, float] = {
    "india": 0.71,
    "united states": 0.37,
    "united states of america": 0.37,
    "us": 0.37,
    "usa": 0.37,
    "united kingdom": 0.18,
    "uk": 0.18,
    "gb": 0.18,
    "great britain": 0.18,
    "china": 0.58,
}
DEFAULT_ELECTRICITY_KG_PER_KWH = 0.43  # Global average grid factor

# Dietary emissions (kg CO2e per month)
# India factors are based on standard Indian diets (0.7 to 2.0 kg CO2e/day)
DIET_FACTORS_INDIA: dict[DietType, float] = {
    DietType.meat_heavy:   60.0,    # ~2.0 kg/day, chicken/mutton/fish based omnivore
    DietType.mixed:        40.0,    # ~1.3 kg/day, moderate meat/dairy omnivore
    DietType.vegetarian:   26.0,    # ~0.85 kg/day, standard lacto-vegetarian diet
    DietType.vegan:        20.0,    # ~0.66 kg/day, predominantly plant-based/cereal diet
}

# Western/Global factors are based on Scarborough et al. 2023 Nature Food (Oxford)
# Vegan: 2.47 kg/day (~75 kg/mo), Vegetarian: 4.16 kg/day (~126 kg/mo),
# Mixed: ~5.7 kg/day (~175 kg/mo), Meat-heavy: 10.24 kg/day (~312 kg/mo)
DIET_FACTORS_GLOBAL: dict[DietType, float] = {
    DietType.meat_heavy:   310.0,
    DietType.mixed:        175.0,
    DietType.vegetarian:   125.0,
    DietType.vegan:        75.0,
}

# Legacy alias — preserved for backward-compatible test imports.
DIET_FACTORS_KG_PER_MONTH = DIET_FACTORS_GLOBAL

ELECTRICITY_KG_PER_KWH   = 0.71    # India CEA 2022-23 grid average (legacy constant)
NATURAL_GAS_KG_PER_THERM  = 5.3    # EPA AP-42 combustion factor

# Restaurant meal lifecycle factor (kg CO2e per meal)
MEAL_OUT_KG_INDIA  = 1.5
MEAL_OUT_KG_GLOBAL = 4.5

NEW_ITEM_KG     = 18.0   # Consumer goods lifecycle average (clothing/electronics)
WASTE_BAG_KG    = 2.2    # EPA WARM landfill model per 13-gallon bag

WEEKS_PER_MONTH = 4.345  # 365.25 / 12 / 7

# High-emission car modes for action targeting
CAR_MODES = {TransportMode.car_petrol, TransportMode.car_diesel}


# ── Utility ───────────────────────────────────────────────────────────────────

def _round_kg(value: float) -> float:
    """Round a CO₂e value to one decimal place."""
    return round(value, 1)


# ── Cached pure-function lookups ──────────────────────────────────────────────

@functools.lru_cache(maxsize=32)
def get_electricity_factor(country: str) -> float:
    """Return the grid electricity carbon intensity for *country*.

    Result is cached — the set of possible inputs is small and bounded.
    """
    return ELECTRICITY_BY_COUNTRY.get(country.strip().lower(), DEFAULT_ELECTRICITY_KG_PER_KWH)


@functools.lru_cache(maxsize=32)
def get_diet_factors(country: str) -> dict[DietType, float]:
    """Return the appropriate diet emission factor table for *country*.

    Result is cached — only two possible outputs exist.
    """
    if country.strip().lower() == "india":
        return DIET_FACTORS_INDIA
    return DIET_FACTORS_GLOBAL


@functools.lru_cache(maxsize=32)
def get_meal_out_factor(country: str) -> float:
    """Return the restaurant meal emission factor for *country*."""
    if country.strip().lower() == "india":
        return MEAL_OUT_KG_INDIA
    return MEAL_OUT_KG_GLOBAL


# ── Category calculations ─────────────────────────────────────────────────────

def calculate_home_kg(request: FootprintRequest) -> float:
    """Monthly home energy CO₂e allocated to this household member."""
    nonrenewable_share = (100.0 - request.home.renewable_percent) / 100.0
    electricity_factor = get_electricity_factor(request.profile.country)
    electricity = request.home.electricity_kwh * electricity_factor * nonrenewable_share
    gas = request.home.natural_gas_therms * NATURAL_GAS_KG_PER_THERM
    return (electricity + gas) / request.home.household_size


def calculate_transport_kg(request: FootprintRequest) -> float:
    """Monthly transport CO₂e across all travel modes."""
    return sum(
        item.km_per_week * WEEKS_PER_MONTH * TRANSPORT_FACTORS_KG_PER_KM[item.mode]
        for item in request.transport
    )


def calculate_lifestyle_kg(request: FootprintRequest) -> float:
    """Monthly lifestyle CO₂e: diet + meals out + purchases + waste."""
    diet_factors = get_diet_factors(request.profile.country)
    diet = diet_factors[request.lifestyle.diet]

    meal_factor = get_meal_out_factor(request.profile.country)
    meals = request.lifestyle.meals_out_per_week * WEEKS_PER_MONTH * meal_factor

    purchases = request.lifestyle.new_items_per_month * NEW_ITEM_KG
    waste     = request.lifestyle.waste_bags_per_week * WEEKS_PER_MONTH * WASTE_BAG_KG
    return diet + meals + purchases + waste


def calculate_categories(request: FootprintRequest) -> list[CategoryResult]:
    """Compute CO₂e for all three categories and return transparent results."""
    electricity_factor = get_electricity_factor(request.profile.country)
    values: list[tuple[str, float, str]] = [
        (
            "Home energy",
            calculate_home_kg(request),
            (
                f"Electricity at {electricity_factor} kg CO\u2082e/kWh scaled to "
                f"{100 - request.home.renewable_percent:.0f}% non-renewable, "
                f"divided across {request.home.household_size} household member(s)."
                + (
                    f" Gas: {request.home.natural_gas_therms} therms "
                    f"\u00d7 {NATURAL_GAS_KG_PER_THERM} kg CO\u2082e/therm."
                    if request.home.natural_gas_therms > 0
                    else ""
                )
            ),
        ),
        (
            "Transport",
            calculate_transport_kg(request),
            (
                "Weekly travel converted to monthly distance and multiplied by "
                "mode-specific lifecycle emission factors (DEFRA 2023 / IPCC averages)."
            ),
        ),
        (
            "Food and lifestyle",
            calculate_lifestyle_kg(request),
            (
                f"{request.lifestyle.diet.replace('_', '-').capitalize()} diet base + "
                f"{request.lifestyle.meals_out_per_week} restaurant meal(s)/week + "
                f"{request.lifestyle.new_items_per_month} new item(s)/month + "
                f"{request.lifestyle.waste_bags_per_week} waste bag(s)/week."
            ),
        ),
    ]

    return [
        CategoryResult(
            category=category,
            monthly_kg=_round_kg(monthly_kg),
            yearly_kg=_round_kg(monthly_kg * 12),
            explanation=explanation,
        )
        for category, monthly_kg, explanation in values
    ]


# ── Action generation ─────────────────────────────────────────────────────────

def generate_actions(
    request: FootprintRequest,
    categories: list[CategoryResult],
) -> list[ActionItem]:
    """Generate personalised, impact-ranked reduction actions.

    Logic:
    1. Check each major emission source for high-impact opportunities.
    2. Cap at 4 actions sorted descending by monthly saving.
    3. If no conditions trigger (very low-impact profile), set a focused goal
       on the largest remaining category.
    """
    actions: list[ActionItem] = []

    # ── Home energy ──
    if request.home.electricity_kwh > 150 and request.home.renewable_percent < 80:
        potential_saving = min(90.0, request.home.electricity_kwh * 0.12)
        actions.append(
            ActionItem(
                title="Switch to a renewable energy tariff or reduce peak-hour usage by 20%",
                impact_kg_month=_round_kg(potential_saving),
                effort="medium",
                why_it_matters=(
                    "Home electricity is often the fastest category to address. "
                    "A tariff change requires no daily behaviour change after switching."
                ),
            )
        )

    # ── Transport: high car use ──
    car_km = sum(
        item.km_per_week
        for item in request.transport
        if item.mode in CAR_MODES
    )
    if car_km > 30:
        saving = _round_kg(car_km * 0.15 * WEEKS_PER_MONTH * 0.18)
        actions.append(
            ActionItem(
                title="Replace one car trip per week with public transport or cycling",
                impact_kg_month=saving,
                effort="low",
                why_it_matters=(
                    "Even a 15% modal shift on your weekly car distance compounding "
                    "over a month produces visible savings without major inconvenience."
                ),
            )
        )

    # ── Diet ──
    if request.lifestyle.diet in {DietType.meat_heavy, DietType.mixed}:
        if request.profile.country.strip().lower() == "india":
            saving_kg = 6.0 if request.lifestyle.diet == DietType.meat_heavy else 3.0
        else:
            saving_kg = 20.0 if request.lifestyle.diet == DietType.meat_heavy else 10.0
        actions.append(
            ActionItem(
                title="Try two lower-carbon meals each week (plant-based swap)",
                impact_kg_month=saving_kg,
                effort="low",
                why_it_matters=(
                    "Replacing two meat-based meals per week with plant-based alternatives "
                    "is one of the highest-leverage, lowest-cost actions available."
                ),
            )
        )

    # ── Consumer purchases ──
    if request.lifestyle.new_items_per_month >= 3:
        actions.append(
            ActionItem(
                title="Delay or buy second-hand for one non-essential purchase this month",
                impact_kg_month=18.0,
                effort="medium",
                why_it_matters=(
                    "Manufacturing a single new clothing or electronics item embeds "
                    "~18 kg CO₂e. Buying used keeps that carbon from being emitted."
                ),
            )
        )

    # ── Waste ──
    if request.lifestyle.waste_bags_per_week >= 3:
        saving = _round_kg(
            request.lifestyle.waste_bags_per_week * 0.5 * WEEKS_PER_MONTH * WASTE_BAG_KG
        )
        actions.append(
            ActionItem(
                title="Reduce waste by composting food scraps and recycling packaging",
                impact_kg_month=saving,
                effort="low",
                why_it_matters=(
                    "Diverting organic waste from landfill prevents methane generation, "
                    "which has 28× the warming impact of CO₂ over 100 years."
                ),
            )
        )

    # ── Fallback: focused goal on largest category ──
    if not actions:
        top_category = max(categories, key=lambda item: item.monthly_kg)
        actions.append(
            ActionItem(
                title=f"Set a 10% monthly reduction goal for {top_category.category.lower()}",
                impact_kg_month=_round_kg(top_category.monthly_kg * 0.1),
                effort="medium",
                why_it_matters=(
                    "Your footprint is already low. A focused 10% target on your "
                    "largest category keeps progress measurable and momentum building."
                ),
            )
        )

    # Return top 4 sorted by impact
    return sorted(actions, key=lambda item: item.impact_kg_month, reverse=True)[:4]


# ── Confidence scoring ────────────────────────────────────────────────────────

def calculate_confidence(request: FootprintRequest) -> float:
    """Estimate data quality as a confidence score in [0, 1].

    Starts at 0.72 (baseline from diet + home data).
    Increments for each additional data signal provided.
    Capped at 0.92 to acknowledge inherent estimation uncertainty.
    """
    score = 0.72
    if request.transport:
        score += 0.08
    if request.home.household_size > 1:
        score += 0.04
    if request.home.renewable_percent > 0:
        score += 0.04
    if request.lifestyle.meals_out_per_week or request.lifestyle.new_items_per_month:
        score += 0.04
    if request.home.natural_gas_therms > 0:
        score += 0.02
    return min(round(score, 2), 0.92)
