"""
api.monitoring

    GET   /api/datasets/{dataset_id}/monitoring -> current settings
    PATCH /api/datasets/{dataset_id}/monitoring -> update settings
    GET   /api/alerts                           -> list alerts (org-scoped)
    POST  /api/alerts/{alert_id}/read           -> mark one alert read

All routes require auth and are scoped to the current user's
organization, same as api/datasets.py and api/reports.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import User
from backend.schemas.analysis import AlertOut, MonitoringSettings, MonitoringUpdate
from backend.services.monitoring_service import (
    AlertNotFound,
    DatasetNotFound,
    get_monitoring_settings,
    list_alerts,
    mark_alert_read,
    update_monitoring_settings,
)

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/datasets/{dataset_id}/monitoring", response_model=MonitoringSettings)
def get_monitoring(
    dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        dataset = get_monitoring_settings(db, current_user.organization_id, dataset_id)
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return MonitoringSettings(
        monitoring_enabled=dataset.monitoring_enabled,
        alert_threshold_points=dataset.alert_threshold_points,
    )


@router.patch("/datasets/{dataset_id}/monitoring", response_model=MonitoringSettings)
def update_monitoring(
    dataset_id: int,
    payload: MonitoringUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        dataset = update_monitoring_settings(
            db,
            current_user.organization_id,
            dataset_id,
            enabled=payload.monitoring_enabled,
            threshold_points=payload.alert_threshold_points,
        )
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return MonitoringSettings(
        monitoring_enabled=dataset.monitoring_enabled,
        alert_threshold_points=dataset.alert_threshold_points,
    )


@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_alerts(db, current_user.organization_id, unread_only=unread_only)


@router.post("/alerts/{alert_id}/read", response_model=AlertOut)
def read_alert(
    alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        return mark_alert_read(db, current_user.organization_id, alert_id)
    except AlertNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
