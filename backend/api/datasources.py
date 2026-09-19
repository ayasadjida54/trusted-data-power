"""
api.datasources

    POST   /api/datasets/connect-sheet         -> link a Google Sheet, sync immediately
    POST   /api/datasets/{dataset_id}/sync-now -> re-sync an already-linked sheet
    GET    /api/datasets/{dataset_id}/datasource -> current link status
    DELETE /api/datasets/{dataset_id}/datasource -> unlink

All routes require auth and are org-scoped, same as every other
datasets-adjacent router.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import User
from backend.schemas.analysis import AnalysisRunDetail, DataSourceOut, LinkSheetRequest
from backend.services.datasource_service import (
    DatasetNotFound,
    NoDataSource,
    get_datasource,
    link_google_sheet,
    sync_dataset_now,
    unlink_datasource,
)
from backend.services.sheets_connector import InvalidSheetUrl, SheetFetchError

router = APIRouter(prefix="/api", tags=["datasources"])


@router.post("/datasets/connect-sheet", response_model=AnalysisRunDetail)
def connect_sheet(
    payload: LinkSheetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _dataset, run = link_google_sheet(
            db,
            organization_id=current_user.organization_id,
            sheet_url=payload.sheet_url,
            dataset_id=payload.dataset_id,
            dataset_name=payload.dataset_name,
            sync_interval_minutes=payload.sync_interval_minutes,
        )
    except (InvalidSheetUrl, SheetFetchError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return run


@router.post("/datasets/{dataset_id}/sync-now", response_model=AnalysisRunDetail)
def sync_now(
    dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        run = sync_dataset_now(db, current_user.organization_id, dataset_id)
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except NoDataSource as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if run is None:
        # sync_datasource() records the failure on the DataSource itself
        # rather than raising - see get_datasource for last_sync_error.
        raise HTTPException(
            status_code=502,
            detail="The sync ran but failed - check this dataset's data source status for details.",
        )
    return run


@router.get("/datasets/{dataset_id}/datasource", response_model=DataSourceOut | None)
def get_datasource_route(
    dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        return get_datasource(db, current_user.organization_id, dataset_id)
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/datasets/{dataset_id}/datasource", status_code=204)
def delete_datasource_route(
    dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        unlink_datasource(db, current_user.organization_id, dataset_id)
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
