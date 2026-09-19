"""
api.datasets

    POST /api/datasets/upload                    -> run analysis, store, return full result
    GET  /api/datasets                            -> list datasets in the current org
    GET  /api/datasets/{dataset_id}/latest        -> latest run for one dataset
    GET  /api/datasets/{dataset_id}/runs          -> every run for one dataset, chronological
    GET  /api/datasets/{dataset_id}/compare       -> diff between two runs (Phase 5)
    GET  /api/runs/{run_id}                       -> a specific run's full detail

All routes require a bearer token (see api/deps.get_current_user) and
are scoped to the current user's organization - not to the user
individually - so teammates in the same organization share datasets.
A dataset or run belonging to a different organization returns 404,
not 403, so its existence isn't leaked to users outside that org.

Phase 5: POST /datasets/upload accepts an optional `dataset_id` to
append a new run to an EXISTING dataset slot (building a version
history) instead of always creating a new one - see
services/analysis_service.py for the resolution logic.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models import AnalysisRun, Dataset, User
from backend.schemas.analysis import AnalysisRunDetail, AnalysisRunSummary, ComparisonResult, DatasetSummary
from backend.services.analysis_service import DatasetNotFound, run_analysis_and_store
from backend.services.comparison_service import RunNotFound, compare_runs

router = APIRouter(prefix="/api", tags=["datasets"])


@router.post("/datasets/upload", response_model=AnalysisRunDetail)
def upload_dataset(
    file: UploadFile,
    dataset_name: str | None = None,
    dataset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        run = run_analysis_and_store(
            db=db,
            organization_id=current_user.organization_id,
            filename=file.filename,
            file_obj=file.file,
            dataset_name=dataset_name,
            dataset_id=dataset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except DatasetNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return run


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    datasets = (
        db.query(Dataset)
        .filter(Dataset.organization_id == current_user.organization_id)
        .order_by(Dataset.created_at.desc())
        .all()
    )

    summaries = []
    for dataset in datasets:
        latest_run = dataset.runs[-1] if dataset.runs else None
        summaries.append(
            DatasetSummary(
                id=dataset.id,
                name=dataset.name,
                created_at=dataset.created_at,
                latest_run=latest_run,
            )
        )
    return summaries


def _get_owned_dataset(db: Session, dataset_id: int, organization_id: int) -> Dataset:
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == dataset_id, Dataset.organization_id == organization_id)
        .first()
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("/datasets/{dataset_id}/latest", response_model=AnalysisRunDetail)
def get_latest_run(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = _get_owned_dataset(db, dataset_id, current_user.organization_id)
    if not dataset.runs:
        raise HTTPException(status_code=404, detail="This dataset has no analysis runs yet.")
    return dataset.runs[-1]


@router.get("/datasets/{dataset_id}/runs", response_model=list[AnalysisRunSummary])
def list_runs(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = _get_owned_dataset(db, dataset_id, current_user.organization_id)
    return dataset.runs  # already ordered chronologically (see Dataset.runs)


@router.get("/datasets/{dataset_id}/compare", response_model=ComparisonResult)
def compare_dataset_runs(
    dataset_id: int,
    run_a: int = Query(..., description="Earlier run id"),
    run_b: int = Query(..., description="Later run id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Confirms the dataset itself belongs to this org before touching
    # the runs, so a bad dataset_id 404s cleanly rather than falling
    # through to the run-level check below.
    _get_owned_dataset(db, dataset_id, current_user.organization_id)

    try:
        return compare_runs(db, current_user.organization_id, run_a, run_b)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}", response_model=AnalysisRunDetail)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = (
        db.query(AnalysisRun)
        .join(Dataset)
        .filter(
            AnalysisRun.id == run_id,
            Dataset.organization_id == current_user.organization_id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found.")
    return run
