"""Carbon Footprint Awareness Platform — API entry point.

Architecture:
- lifespan: initialises semaphore, pre-seeds cache, configures Cloud Logging.
- Security middleware: attaches strict HTTP headers on every response.
- CORS: explicit allowlist — never wildcard in any environment.
- /api/footprint: async endpoint with cache hit/miss and semaphore-guarded LLM.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app import cache as app_cache
from app.carbon import calculate_categories, calculate_confidence, generate_actions
from app.config import settings
from app.insights import generate_personalized_insights
from app.models import FootprintRequest, FootprintResponse
from app.storage import save_assessment

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"


# ── Cloud Logging setup ───────────────────────────────────────────────────────

def _setup_cloud_logging() -> None:
    """Attach Google Cloud Logging handler when GCP credentials are available.

    Falls back to stdlib logging silently so local development is unaffected.
    """
    if not settings.google_cloud_project:
        logging.basicConfig(level=settings.log_level)
        return
    try:
        import google.cloud.logging as gcp_logging  # noqa: PLC0415

        client = gcp_logging.Client(project=settings.google_cloud_project)
        client.setup_logging(log_level=getattr(logging, settings.log_level, logging.INFO))
        logger.info("Google Cloud Logging initialised for project %s.", settings.google_cloud_project)
    except Exception as exc:  # noqa: BLE001
        logging.basicConfig(level=settings.log_level)
        logger.warning("Cloud Logging unavailable (%s); using stdlib logging.", exc.__class__.__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """Manage application startup and shutdown.

    Startup:
      1. Configure structured logging (Cloud Logging or stdlib fallback).
      2. Initialise the async LLM semaphore inside the running event loop.
      3. Pre-seed the TTLCache with deterministic demo responses for 0 ms
         latency and 0 API cost on expected demo queries.

    Shutdown:
      Nothing to clean up — cache and semaphore are in-process objects.
    """
    _setup_cloud_logging()
    app_cache.init_semaphore()
    app_cache.preseed_cache()
    logger.info(
        "Carbon Footprint Platform started. Cache size: %d entries.",
        app_cache.cache_size(),
    )
    yield
    logger.info("Carbon Footprint Platform shutting down.")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Carbon Footprint Awareness Platform",
    version="1.2.0",
    description=(
        "AI-powered platform that helps individuals understand, track, and reduce "
        "their personal carbon footprint through transparent calculations, ranked "
        "actions, and Gemini-powered personalised insights."
    ),
    contact={"name": "PromptWars 2026 Submission"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Explicit allowlist — never "*". Configured via ALLOWED_ORIGINS env var.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Security headers ──────────────────────────────────────────────────────────

@app.middleware("http")
async def add_security_headers(request: Request, call_next: Callable) -> JSONResponse:
    """Attach strict security headers to every HTTP response."""
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe for Cloud Run and load balancers."""
    return {
        "status": "ok",
        "version": "1.2.0",
        "cache_entries": str(app_cache.cache_size()),
    }


@app.post(
    "/api/footprint",
    response_model=FootprintResponse,
    summary="Estimate personal carbon footprint",
    description=(
        "Accepts a structured lifestyle profile, computes monthly CO₂e estimates "
        "across three categories, ranks personalised reduction actions, and returns "
        "Gemini-powered insights (with deterministic fallback). "
        "Responses are cached by request hash for sub-millisecond repeat queries."
    ),
    tags=["footprint"],
)
async def estimate_footprint(request: FootprintRequest) -> FootprintResponse:
    """Core agent endpoint: validate → cache check → calculate → rank → personalise → store.

    Pipeline:
    1. Check in-memory TTLCache for an identical previous request.
    2. Compute deterministic carbon categories and ranked actions.
    3. Acquire the LLM semaphore and await Gemini personalised insights.
    4. Persist the assessment asynchronously.
    5. Cache the response and return.
    """
    # ── 1. Cache hit fast-path ────────────────────────────────────────────────
    cache_key = app_cache.make_cache_key(request)
    if cached_response := app_cache.get_cached(cache_key):
        return cached_response

    # ── 2. Deterministic computation ──────────────────────────────────────────
    categories = calculate_categories(request)
    total_monthly = round(sum(item.monthly_kg for item in categories), 1)
    actions = generate_actions(request, categories)

    # ── 3. Gemini insights (rate-limited) ─────────────────────────────────────
    semaphore = app_cache.semaphore
    if semaphore is not None:
        async with semaphore:
            insights = await generate_personalized_insights(request, categories, actions)
    else:
        insights = await generate_personalized_insights(request, categories, actions)

    # ── 4. Persist assessment ─────────────────────────────────────────────────
    storage_status = await save_assessment(
        {
            "profile": request.profile.model_dump(),
            "total_monthly_kg": total_monthly,
            "category_results": [item.model_dump() for item in categories],
            "actions": [item.model_dump() for item in actions],
        }
    )

    # ── 5. Build, cache, and return ───────────────────────────────────────────
    result = FootprintResponse(
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
    app_cache.set_cached(cache_key, result)
    return result


# ── Validation error handler ──────────────────────────────────────────────────

@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:  # noqa: ARG001
    """Return a structured 422 body for Pydantic validation failures."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(include_url=False)},
    )
