from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from .api.orchestration import router as orchestration_router
from .api.patients import router as patients_router
from .api.policy import router as policy_router
from .config import SettingsError, load_settings
from .data.store import SeedDataError, patient_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("care-orchestration-api")


def initialize_app_state(target_app: FastAPI) -> None:
    """Load settings and seed patient fixtures.

    Runs both at import time (so a module-level ``TestClient(app)`` that never
    enters the ASGI lifespan still has seeded data) and from the lifespan
    handler (for real ``uvicorn`` startup). It is idempotent: settings load is
    pure and ``patient_store.load_from_file`` replaces the fixture snapshot.
    """
    if getattr(target_app.state, "initialized", False):
        return

    try:
        settings = load_settings()
        fixture_path = Path(__file__).parent / "data" / "fixtures" / "patients.json"
        patient_store.load_from_file(fixture_path)
        target_app.state.settings = settings
        target_app.state.seed_fixture_path = str(fixture_path)
        target_app.state.initialized = True
        logger.info(
            "Service startup complete: name=%s env=%s version=%s seeded_patients=%s",
            settings.service_name,
            settings.environment,
            settings.app_version,
            patient_store.count,
        )
    except SettingsError as exc:
        logger.exception("Startup configuration error: %s", exc)
        raise RuntimeError(f"Startup configuration error: {exc}") from exc
    except SeedDataError as exc:
        logger.exception("Seed data error: %s", exc)
        raise RuntimeError(f"Seed data error: {exc}") from exc


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    initialize_app_state(fastapi_app)
    yield


app = FastAPI(
    title="AI Care Orchestration API",
    version="0.1.0",
    description="Backend skeleton for care orchestration workflows.",
    lifespan=lifespan,
)

app.include_router(orchestration_router)
app.include_router(patients_router)
app.include_router(policy_router)

# Permissive CORS for local development so browser front-ends (the static HTML
# dashboards and the Flutter Web app) can call the API from a different origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed immediately at import so tests using a module-level ``TestClient(app)``
# (which does not run the ASGI lifespan) still have patient data available.
initialize_app_state(app)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next) -> Response:
    started_at = time.perf_counter()
    incoming_correlation_id = request.headers.get("X-Correlation-ID", "").strip()
    correlation_id = incoming_correlation_id or str(uuid4())
    request.state.correlation_id = correlation_id

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed correlation_id=%s method=%s route=%s status=%s latency_ms=%s",
            correlation_id,
            request.method,
            request.url.path,
            500,
            latency_ms,
        )
        raise

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id
    logger.info(
        "request_completed correlation_id=%s method=%s route=%s status=%s latency_ms=%s",
        correlation_id,
        request.method,
        request.url.path,
        status_code,
        latency_ms,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    settings = getattr(app.state, "settings", None)
    service_name = settings.service_name if settings else "care-orchestration-api"
    app_version = settings.app_version if settings else app.version
    return {
        "status": "ok",
        "service": service_name,
        "version": app_version,
    }


@app.get("/ready")
def ready() -> dict[str, object]:
    settings = getattr(app.state, "settings", None)
    if not settings:
        raise HTTPException(status_code=503, detail="service not ready: settings not loaded")

    return {
        "status": "ready",
        "service": settings.service_name,
        "environment": settings.environment,
        "seeded_patient_count": patient_store.count,
        "seed_fixture_path": getattr(app.state, "seed_fixture_path", "unknown"),
        "orchestration_routes": [
            "/api/v1/orchestration/ping",
            "/api/v1/orchestration/routes",
            "/api/v1/orchestration/rules/versions",
            "/api/v1/orchestration/rules/active",
            "/api/v1/orchestration/rules/publish",
            "/api/v1/orchestration/rules/activate",
            "/api/v1/orchestration/taxonomy/versions",
            "/api/v1/orchestration/taxonomy/active",
            "/api/v1/orchestration/taxonomy/publish",
            "/api/v1/orchestration/taxonomy/activate",
            "/api/v1/orchestration/taxonomy/validate",
            "/api/v1/orchestration/taxonomy/compatibility/check",
            "/api/v1/orchestration/conversation/start",
            "/api/v1/orchestration/cx/webhook",
            "/api/v1/orchestration/runs",
            "/api/v1/orchestration/runs/{run_id}",
            "/api/v1/orchestration/runs/{run_id}/decision",
            "/api/v1/orchestration/runs/{run_id}/tasks/generate",
            "/api/v1/orchestration/runs/{run_id}/tasks",
            "/api/v1/orchestration/runs/{run_id}/tasks/{task_id}/status",
            "/api/v1/orchestration/runs/{run_id}/escalation/check",
            "/api/v1/orchestration/runs/{run_id}/timeline",
            "/api/v1/orchestration/runs/{run_id}/tracking",
            "/api/v1/orchestration/analytics",
            "/api/v1/orchestration/analysis/trigger",
            "/api/v1/orchestration/analysis",
            "/api/v1/orchestration/analysis/{analysis_id}",
            "/api/v1/orchestration/analysis/{analysis_id}/validate",
            "/api/v1/orchestration/analysis/{analysis_id}/validation",
        ],
        "patient_routes": [
            "/api/v1/patients",
            "/api/v1/patients/{patient_id}/profile",
            "/api/v1/patients/ingest",
        ],
        "policy_routes": [
            "/api/v1/policy/disclaimer",
            "/api/v1/policy/audit/events",
            "/api/v1/policy/audit/integrity",
            "/api/v1/policy/audit/patients/{patient_id}",
        ],
    }
