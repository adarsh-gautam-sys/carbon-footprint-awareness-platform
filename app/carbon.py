from app.models import ActionItem, CategoryResult, DietType, FootprintRequest, TransportMode


TRANSPORT_FACTORS_KG_PER_KM = {
    TransportMode.car_petrol: 0.192,
    TransportMode.car_diesel: 0.171,
    TransportMode.car_ev: 0.053,
    TransportMode.bus: 0.089,
    TransportMode.train: 0.041,
    TransportMode.flight_short: 0.255,
    TransportMode.walk_cycle: 0.0,
}

DIET_FACTORS_KG_PER_MONTH = {
    DietType.meat_heavy: 330.0,
    DietType.mixed: 230.0,
    DietType.vegetarian: 170.0,
    DietType.vegan: 130.0,
}

ELECTRICITY_KG_PER_KWH = 0.71
NATURAL_GAS_KG_PER_THERM = 5.3
MEAL_OUT_KG = 4.5
NEW_ITEM_KG = 18.0
WASTE_BAG_KG = 2.2
WEEKS_PER_MONTH = 4.345


def round_kg(value: float) -> float:
    return round(value, 1)


def calculate_home_kg(request: FootprintRequest) -> float:
    nonrenewable_share = (100 - request.home.renewable_percent) / 100
    electricity = request.home.electricity_kwh * ELECTRICITY_KG_PER_KWH * nonrenewable_share
    gas = request.home.natural_gas_therms * NATURAL_GAS_KG_PER_THERM
    return (electricity + gas) / request.home.household_size


def calculate_transport_kg(request: FootprintRequest) -> float:
    total = 0.0
    for item in request.transport:
        total += item.km_per_week * WEEKS_PER_MONTH * TRANSPORT_FACTORS_KG_PER_KM[item.mode]
    return total


def calculate_lifestyle_kg(request: FootprintRequest) -> float:
    diet = DIET_FACTORS_KG_PER_MONTH[request.lifestyle.diet]
    meals = request.lifestyle.meals_out_per_week * WEEKS_PER_MONTH * MEAL_OUT_KG
    purchases = request.lifestyle.new_items_per_month * NEW_ITEM_KG
    waste = request.lifestyle.waste_bags_per_week * WEEKS_PER_MONTH * WASTE_BAG_KG
    return diet + meals + purchases + waste


def calculate_categories(request: FootprintRequest) -> list[CategoryResult]:
    values = [
        (
            "Home energy",
            calculate_home_kg(request),
            "Electricity is adjusted for renewable share and divided across household members.",
        ),
        (
            "Transport",
            calculate_transport_kg(request),
            "Weekly travel is converted to monthly distance and multiplied by mode-specific factors.",
        ),
        (
            "Food and lifestyle",
            calculate_lifestyle_kg(request),
            "Diet, restaurant meals, new purchases, and waste are combined into monthly impact.",
        ),
    ]

    return [
        CategoryResult(
            category=category,
            monthly_kg=round_kg(monthly_kg),
            yearly_kg=round_kg(monthly_kg * 12),
            explanation=explanation,
        )
        for category, monthly_kg, explanation in values
    ]


def generate_actions(request: FootprintRequest, categories: list[CategoryResult]) -> list[ActionItem]:
    actions: list[ActionItem] = []

    if request.home.electricity_kwh > 150 and request.home.renewable_percent < 80:
        impact = min(90.0, request.home.electricity_kwh * 0.12)
        actions.append(
            ActionItem(
                title="Shift 20% of electricity use to renewable or lower-use habits",
                impact_kg_month=round_kg(impact),
                effort="medium",
                why_it_matters="Home energy is one of the fastest places to reduce emissions without changing daily travel.",
            )
        )

    car_km = sum(
        item.km_per_week
        for item in request.transport
        if item.mode in {TransportMode.car_petrol, TransportMode.car_diesel}
    )
    if car_km > 30:
        actions.append(
            ActionItem(
                title="Replace one car trip per week with public transport or cycling",
                impact_kg_month=round_kg(car_km * 0.15 * WEEKS_PER_MONTH * 0.18),
                effort="low",
                why_it_matters="Small weekly travel substitutions compound into visible monthly savings.",
            )
        )

    if request.lifestyle.diet in {DietType.meat_heavy, DietType.mixed}:
        actions.append(
            ActionItem(
                title="Try two lower-carbon meals each week",
                impact_kg_month=38.0 if request.lifestyle.diet == DietType.meat_heavy else 24.0,
                effort="low",
                why_it_matters="Food changes work best when framed as repeatable swaps instead of strict restrictions.",
            )
        )

    if request.lifestyle.new_items_per_month >= 3:
        actions.append(
            ActionItem(
                title="Delay or buy used for one non-essential purchase",
                impact_kg_month=18.0,
                effort="medium",
                why_it_matters="Manufacturing emissions are hidden in daily consumption and are easy to overlook.",
            )
        )

    if not actions:
        top_category = max(categories, key=lambda item: item.monthly_kg)
        actions.append(
            ActionItem(
                title=f"Set a 10% reduction goal for {top_category.category.lower()}",
                impact_kg_month=round_kg(top_category.monthly_kg * 0.1),
                effort="medium",
                why_it_matters="A focused target keeps the next action measurable and realistic.",
            )
        )

    return sorted(actions, key=lambda item: item.impact_kg_month, reverse=True)[:4]


def calculate_confidence(request: FootprintRequest) -> float:
    score = 0.72
    if request.transport:
        score += 0.08
    if request.home.household_size > 1:
        score += 0.04
    if request.home.renewable_percent > 0:
        score += 0.04
    if request.lifestyle.meals_out_per_week or request.lifestyle.new_items_per_month:
        score += 0.04
    return min(round(score, 2), 0.92)
