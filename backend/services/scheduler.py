"""
services.scheduler

The actual "scheduled re-analysis" this whole line of work has been
building toward since Phase 7 (which built the alert-detection engine
this fires into, but had no external source to poll on a timer) and
Phase 8 (which added the first such source, Google Sheets).

Runs an APScheduler BackgroundScheduler in-process - no separate worker
process or external infra (Celery, cron) needed, appropriate for this
product's current scale. A job runs every minute, checks every
DataSource with a sync_interval_minutes set, and re-syncs any that are
due (never synced, or last synced longer ago than their interval).

Disabled entirely when DISABLE_SCHEDULER is set (see backend/tests/conftest.py) -
tests need deterministic control over when a sync happens, via direct
calls to sync_datasource(), not a real timer racing the test process.
"""

import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models import DataSource
from backend.services.datasource_service import sync_datasource

CHECK_INTERVAL_SECONDS = 60

_scheduler: BackgroundScheduler | None = None


def _is_due(data_source: DataSource, now: datetime) -> bool:
    if data_source.sync_interval_minutes is None:
        return False
    if data_source.last_synced_at is None:
        return True
    due_at = data_source.last_synced_at.replace(tzinfo=timezone.utc) + timedelta(
        minutes=data_source.sync_interval_minutes
    )
    return now >= due_at


def _run_due_syncs():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        candidates = db.query(DataSource).filter(DataSource.sync_interval_minutes.isnot(None)).all()
        for data_source in candidates:
            if _is_due(data_source, now):
                sync_datasource(db, data_source)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """
    Starts the background scheduler unless DISABLE_SCHEDULER is set.
    Safe to call multiple times - only starts one instance. Returns
    the scheduler (or None if disabled), mainly so callers/tests can
    shut it down explicitly if needed.
    """
    global _scheduler

    if os.environ.get("DISABLE_SCHEDULER"):
        return None

    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_run_due_syncs, "interval", seconds=CHECK_INTERVAL_SECONDS, id="sync_data_sources")
    _scheduler.start()
    return _scheduler
