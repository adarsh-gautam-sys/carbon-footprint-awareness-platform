from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.carbon import calculate_categories, calculate_confidence, generate_actions
from app.insights import generate_personalized_insights
from app.models import FootprintRequest, FootprintResponse
from app.storage import save_assessment


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app = FastAPI(
    title="Carbon Footprint Awareness Platform",
    version="1.0.0",
    description="Tracks and explains personal carbon footprint estimates with practical action recommendations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/footprint", response_model=FootprintResponse)
def estimate_footprint(request: FootprintRequest) -> FootprintResponse:
    categories = calculate_categories(request)
    total_monthly = round(sum(item.monthly_kg for item in categories), 1)
    actions = generate_actions(request, categories)
    insights = generate_personalized_insights(request, categories, actions)
    storage_status = save_assessment(
        {
            "profile": request.profile.model_dump(),
            "total_monthly_kg": total_monthly,
            "category_results": [item.model_dump() for item in categories],
            "actions": [item.model_dump() for item in actions],
        }
    )

    return FootprintResponse(
        total_monthly_kg=total_monthly,
        total_yearly_tonnes=round((total_monthly * 12) / 1000, 2),
        category_results=categories,
        personalized_actions=actions,
        insights=insights,
        confidence_score=calculate_confidence(request),
        methodology="CO2e estimate using transparent activity factors, household allocation, and behavior-based action modeling.",
        storage_status=storage_status,
    )
