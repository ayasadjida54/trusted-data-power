"""
services.monitoring_service

Two responsibilities:
1. Reading/updating a dataset's monitoring settings (enabled + the
   point-drop threshold that triggers an alert).
2. maybe_create_alert(): called after a new run is stored for a
   monitored dataset that already had a previous run. Compares the two
   with engine.compare_analysis_results (the same Phase 5 comparison
   logic a user gets from the Compare page - nothing new is computed
   here) and creates an Alert if the score dropped by at least the
   configured threshold.

This is intentionally NOT a scheduler. "Scheduled re-analysis" in the
literal cron sense needs something to fetch new data on a timer, which
requires a data source to poll - that's Phase 8 (ingestion) work, not
yet built. What this module provides is the detection engine a
scheduler would call into once Phase 8 exists: maybe_create_alert()
doesn't care whether the new run came from a human uploading a file or
an automated job - it fires on any new run for a monitored dataset,
which is what makes it a drop-in fit for a future scheduler with zero
changes needed here.
"""

from sqlalchemy.orm import Session

from backend.models import AnalysisRun, Alert, Dataset
from engine import compare_analysis_results


class DatasetNotFound(Exception):
    pass


def _get_owned_dataset(db: Session, organization_id: int, dataset_id: int) -> Dataset:
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == dataset_id, Dataset.organization_id == organization_id)
        .first()
    )
    if dataset is None:
        raise DatasetNotFound(f"Dataset {dataset_id} not found in this organization.")
    return dataset


def get_monitoring_settings(db: Session, organization_id: int, dataset_id: int) -> Dataset:
    return _get_owned_dataset(db, organization_id, dataset_id)


def update_monitoring_settings(
    db: Session, organization_id: int, dataset_id: int, enabled: bool, threshold_points: float
) -> Dataset:
    dataset = _get_owned_dataset(db, organization_id, dataset_id)
    dataset.monitoring_enabled = enabled
    dataset.alert_threshold_points = threshold_points
    db.commit()
    db.refresh(dataset)
    return dataset


def _as_engine_result(run: AnalysisRun) -> dict:
    return {
        "score": run.score,
        "score_label": run.score_label,
        "dimension_scores": run.dimension_scores,
        "issues": run.issues,
    }


def maybe_create_alert(
    db: Session, dataset: Dataset, previous_run: AnalysisRun, current_run: AnalysisRun
) -> Alert | None:
    """
    Compare `previous_run` -> `current_run`; if the dataset has
    monitoring enabled AND the score dropped by at least its
    alert_threshold_points, create and return a new Alert. Returns
    None (and creates nothing) otherwise - not monitored, or the drop
    (if any) didn't cross the threshold.

    Does NOT commit on its own beyond what creating the Alert row
    requires as part of the caller's existing transaction - called
    from analysis_service.run_analysis_and_store, which commits once
    for the whole upload.
    """
    if not dataset.monitoring_enabled:
        return None

    diff = compare_analysis_results(_as_engine_result(previous_run), _as_engine_result(current_run))
    if diff["score_delta"] > -dataset.alert_threshold_points:
        return None

    alert = Alert(
        dataset_id=dataset.id,
        previous_run_id=previous_run.id,
        current_run_id=current_run.id,
        score_delta=diff["score_delta"],
        summary=diff["summary"],
    )
    db.add(alert)
    return alert


def list_alerts(db: Session, organization_id: int, unread_only: bool = False) -> list[Alert]:
    query = (
        db.query(Alert)
        .join(Dataset)
        .filter(Dataset.organization_id == organization_id)
        .order_by(Alert.created_at.desc())
    )
    if unread_only:
        query = query.filter(Alert.is_read.is_(False))
    return query.all()


class AlertNotFound(Exception):
    pass


def mark_alert_read(db: Session, organization_id: int, alert_id: int) -> Alert:
    alert = (
        db.query(Alert)
        .join(Dataset)
        .filter(Alert.id == alert_id, Dataset.organization_id == organization_id)
        .first()
    )
    if alert is None:
        raise AlertNotFound(f"Alert {alert_id} not found in this organization.")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert
