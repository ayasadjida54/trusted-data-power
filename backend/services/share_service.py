"""
services.share_service

A share token is a random, unguessable string that lets anyone with the
URL view (and download) a read-only report for one run, without an
account. Tokens are per-run (not per-dataset): sharing one version of
a dataset doesn't expose its history or any other run.

Revoking sets share_token back to NULL - the old link 404s immediately
(no separate "revoked" state to check, since NULL already means
"not shared" everywhere else).
"""

import secrets

from sqlalchemy.orm import Session

from backend.models import AnalysisRun, Dataset


class RunNotFound(Exception):
    pass


def _get_owned_run(db: Session, organization_id: int, run_id: int) -> AnalysisRun:
    run = (
        db.query(AnalysisRun)
        .join(Dataset)
        .filter(AnalysisRun.id == run_id, Dataset.organization_id == organization_id)
        .first()
    )
    if run is None:
        raise RunNotFound(f"Run {run_id} not found in this organization.")
    return run


def get_or_create_share_token(db: Session, organization_id: int, run_id: int) -> str:
    run = _get_owned_run(db, organization_id, run_id)
    if not run.share_token:
        run.share_token = secrets.token_urlsafe(24)
        db.commit()
        db.refresh(run)
    return run.share_token


def revoke_share(db: Session, organization_id: int, run_id: int) -> None:
    run = _get_owned_run(db, organization_id, run_id)
    run.share_token = None
    db.commit()


def get_run_by_share_token(db: Session, token: str) -> AnalysisRun | None:
    return db.query(AnalysisRun).filter(AnalysisRun.share_token == token).first()
