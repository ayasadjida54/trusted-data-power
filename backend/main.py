"""
main

FastAPI application entry point.

Setup (run once, or after pulling a schema change):
    alembic upgrade head

Run with:
    uvicorn backend.main:app --reload

Schema management: Alembic migrations (backend/migrations/) are now
the source of truth for the database schema - Base.metadata.create_all()
was used directly through Phases 1-8 since the schema was still
settling, but 8 phases of ad-hoc schema changes (each one requiring
"just delete your dev database and restart" for anyone with existing
data) is exactly the point past which that stops being reasonable.
create_all() is still what backend/tests/conftest.py uses for its
disposable per-test-session database (fast, always in sync with
current models by construction, no need for migration history on data
nobody keeps) - that's a deliberate, narrower use than this file's.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth import router as auth_router
from backend.api.cleaning import router as cleaning_router
from backend.api.datasets import router as datasets_router
from backend.api.datasources import router as datasources_router
from backend.api.monitoring import router as monitoring_router
from backend.api.reports import router as reports_router, public_router as public_reports_router
from backend.services.scheduler import start_scheduler
import backend.models  # noqa: F401 - import registers models on Base.metadata

app = FastAPI(title="Trusted Data Power API")

# Wide open for local development (frontend and backend run on different
# ports). Phase 4 auth means requests now need a real token, but the
# allowed origins should still be tightened to an explicit allowlist of
# deployed frontend origins before this goes anywhere near production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(datasources_router)
app.include_router(monitoring_router)
app.include_router(reports_router)
app.include_router(public_reports_router)
app.include_router(cleaning_router)

# Phase 8: periodic auto-sync for linked Google Sheets data sources.
# No-ops if DISABLE_SCHEDULER is set (see backend/tests/conftest.py).
start_scheduler()


@app.get("/health")
def health_check():
    return {"status": "ok"}
