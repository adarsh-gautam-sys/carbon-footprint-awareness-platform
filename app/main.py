"""Carbon Footprint Awareness Platform — API entry point."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.carbon import calculate_categories, calculate_confidence, generate_actions
from app.insights import generate_personalized_insights
from app.models import FootprintRequest, FootprintResponse
from app.storage import save_assessment


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

# ── Allowed origins ──────────────────────────────────────────────────────────
# In production restrict to the Cloud Run service URL.
# For local development and demos "*" is accepted; override via ALLOWED_ORIGINS.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()] or ["*"]

app = FastAPI(
    title="Carbon Footprint Awareness Platform",
    version="1.1.0",
    description=(
        "AI-powered platform that helps individuals understand, track, and reduce "
        "their personal carbon footprint through transparent calculations, ranked "
        "actions, and Gemini-powered personalised insights."
    ),
    contact={
        "name": "PromptWars 2026 Submission",
    },
    license_info={
        "name": "MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https://fastapi.tiangolo.com",
        "connect-src 'self'",
        "frame-ancestors 'none'",
    ]
    response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
    return response

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    """Liveness probe for Cloud Run and load balancers."""
    return {"status": "ok", "version": "1.1.0"}


@app.post(
    "/api/footprint",
    response_model=FootprintResponse,
    summary="Estimate personal carbon footprint",
    description=(
        "Accepts a structured lifestyle profile, computes monthly CO₂e estimates "
        "across three categories, ranks personalised reduction actions, and returns "
        "Gemini-powered insights (with deterministic fallback)."
    ),
    tags=["footprint"],
)
def estimate_footprint(request: FootprintRequest) -> FootprintResponse:
    """Core agent endpoint: validate → calculate → rank → personalise → store."""
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
        methodology=(
            "CO₂e estimates use IPCC/EPA-aligned emission factors. "
            "Electricity is scaled by renewable share and split across household members. "
            "Transport factors are applied per km per week. "
            "Diet, meals out, purchases, and waste are combined into monthly lifestyle impact. "
            "Gemini AI personalises insight phrasing; it does not alter the numbers."
        ),
        storage_status=storage_status,
    )


# ── Validation error handler ─────────────────────────────────────────────────
@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(include_url=False)},
    )
