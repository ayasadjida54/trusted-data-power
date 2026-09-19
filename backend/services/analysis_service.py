"""
services.analysis_service

Glue between the API layer and the engine: given a DataFrame (from a
file upload OR a Phase 8 external source sync), runs
engine.analyze_dataframe() and stores the result as an AnalysisRun,
scoped to the uploading user's organization (workspace) - not to the
individual user - so teammates in the same organization share
datasets.

Phase 5 adds dataset-slot REUSE: a caller can either target an existing
slot explicitly (`dataset_id`) or by matching name (`dataset_name`,
case-insensitive, within the same organization) so repeat uploads for
"the same" dataset accumulate into one version history instead of each
becoming an unrelated one-run dataset. With neither given, a brand-new
slot is created, named after the filename - the Phase 1-4 behavior,
unchanged as the default.

Phase 7 adds automatic alert detection: if the resolved dataset already
had a previous run AND has monitoring enabled, the new run is compared
against the immediately preceding one and an Alert is created if the
score dropped past the configured threshold.

Phase 8 splits the "given a DataFrame, store it" logic (store_analysis_result)
out from the "given a file, load it into a DataFrame" logic
(run_analysis_and_store), so services/datasource_service.py (Google
Sheets sync) can share the exact same storage + alert-detection path a
file upload uses, rather than duplicating it.

The DataScore cleaning pipeline reuses this same store_analysis_result
function too (see services/cleaning_service.py) - a cleaned run is
stored exactly like any other, just with cleaning_actions/
cleaned_from_run_id set, which is what gives it version history,
trend/comparison, alerts, and reports for free.
"""

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import AnalysisRun, Dataset
from backend.services.file_loader import load_dataframe
from backend.services.json_safe import to_jsonable
from backend.services.monitoring_service import maybe_create_alert
from engine import analyze_dataframe


class DatasetNotFound(Exception):
    pass


def resolve_dataset(
    db: Session, organization_id: int, dataset_id: int | None, dataset_name: str | None, fallback_name: str
) -> Dataset:
    if dataset_id is not None:
        dataset = (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id, Dataset.organization_id == organization_id)
            .first()
        )
        if dataset is None:
            raise DatasetNotFound(f"Dataset {dataset_id} not found in this organization.")
        return dataset

    if dataset_name:
        existing = (
            db.query(Dataset)
            .filter(
                Dataset.organization_id == organization_id,
                Dataset.name.ilike(dataset_name),
            )
            .first()
        )
        if existing is not None:
            return existing

    dataset = Dataset(organization_id=organization_id, name=dataset_name or fallback_name)
    db.add(dataset)
    db.flush()  # assigns dataset.id without committing yet
    return dataset


def store_analysis_result(
    db: Session,
    dataset: Dataset,
    filename: str,
    result: dict,
    raw_df: pd.DataFrame | None = None,
    cleaning_actions: list | None = None,
    cleaned_from_run_id: int | None = None,
) -> AnalysisRun:
    """
    Persist an already-computed engine result (from analyze_dataframe())
    as a new AnalysisRun under `dataset`, running Phase 7's alert
    detection against the dataset's previous run if there is one.
    Commits and returns the saved run.

    `raw_df`, if given, is stored as CSV text (raw_data_csv) so a later
    "clean this dataset" action has real data to work with - see
    services/cleaning_service.py. `cleaning_actions`/`cleaned_from_run_id`
    are set only when THIS call is itself storing the output of a
    cleaning run.

    This is the shared core run_analysis_and_store (file upload),
    services/datasource_service.py (Google Sheets sync), AND
    services/cleaning_service.py (cleaning pipeline) all call into -
    none of them duplicates the alert-detection wiring.
    """
    previous_run = dataset.runs[-1] if dataset.runs else None

    run = AnalysisRun(
        dataset_id=dataset.id,
        filename=filename,
        score=result["score"],
        score_label=result["score_label"],
        profile=to_jsonable(result["profile"]),
        column_dtypes=to_jsonable(result["column_dtypes"]),
        issues=to_jsonable(result["issues"]),
        numeric_stats=to_jsonable(result["numeric_stats"]),
        issue_counts=to_jsonable(result["issue_counts"]),
        recommendations=to_jsonable(result["recommendations"]),
        dimension_scores=to_jsonable(result["dimension_scores"]),
        dimension_weights=to_jsonable(result["dimension_weights"]),
        score_explanation=to_jsonable(result["score_explanation"]),
        column_scores=to_jsonable(result["column_scores"]),
        raw_data_csv=raw_df.to_csv(index=False) if raw_df is not None else None,
        cleaning_actions=cleaning_actions,
        cleaned_from_run_id=cleaned_from_run_id,
    )
    db.add(run)
    db.flush()  # assigns run.id, needed if maybe_create_alert fires below

    if previous_run is not None:
        maybe_create_alert(db, dataset, previous_run, run)

    db.commit()
    db.refresh(run)
    return run


def run_analysis_and_store(
    db: Session,
    organization_id: int,
    filename: str,
    file_obj,
    dataset_name: str | None = None,
    dataset_id: int | None = None,
) -> AnalysisRun:
    """
    Load `file_obj` (named `filename`), run the full engine analysis,
    and persist it as a new AnalysisRun under the resolved Dataset slot
    (see resolve_dataset), owned by `organization_id`. Returns the
    saved AnalysisRun (with its dataset relationship loaded).

    Raises ValueError (propagated from file_loader or the engine) on
    an unreadable file or a file with no usable tabular data, and
    DatasetNotFound if `dataset_id` doesn't resolve within this
    organization - callers are expected to translate both into an
    HTTP 400/404 respectively.
    """
    df = load_dataframe(filename, file_obj)
    result = analyze_dataframe(df)

    dataset = resolve_dataset(db, organization_id, dataset_id, dataset_name, filename)
    return store_analysis_result(db, dataset, filename, result, raw_df=df)
