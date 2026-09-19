"""
services.cleaning_service

The real version of the prototype's "Execute DataScore Pipeline"
button: given an existing AnalysisRun, re-loads its stored raw data
(see AnalysisRun.raw_data_csv), runs engine.clean_dataframe() on it,
re-analyzes the CLEANED data with the full normal pipeline, and stores
that as a brand-new AnalysisRun in the same dataset - via the same
store_analysis_result() every other run goes through, so a cleaning
run automatically gets version history, trend/comparison, alerts, and
reports for free, exactly like a file upload or sheet sync would.

The before/after this produces is real: the "after" score comes from
actually re-running the full scoring pipeline on the actually-modified
data, not a scripted number.
"""

import io

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import AnalysisRun, Dataset
from backend.services.analysis_service import store_analysis_result
from backend.services.json_safe import to_jsonable
from engine import analyze_dataframe, clean_dataframe


class RunNotFound(Exception):
    pass


class NoRawData(Exception):
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


def clean_run(db: Session, organization_id: int, run_id: int) -> AnalysisRun:
    """
    Clean the data behind `run_id` and store the result as a new run in
    the same dataset. Returns the new (cleaned) AnalysisRun.

    Raises RunNotFound if `run_id` doesn't resolve within this
    organization, or NoRawData if this run has no stored raw data to
    clean (e.g. it predates the cleaning feature, or was itself a
    cleaning output re-cleaned with nothing left to fix would still
    have raw data - NoRawData specifically means "we never stored the
    source data for this run").
    """
    run = _get_owned_run(db, organization_id, run_id)
    if not run.raw_data_csv:
        raise NoRawData(
            f"Run {run_id} has no stored source data to clean "
            "(only runs created after the cleaning feature was added have this)."
        )

    df = pd.read_csv(io.StringIO(run.raw_data_csv))
    cleaned_df, actions = clean_dataframe(df, run.issues)
    result = analyze_dataframe(cleaned_df)

    return store_analysis_result(
        db,
        run.dataset,
        filename=f"{run.filename} (cleaned)",
        result=result,
        raw_df=cleaned_df,
        cleaning_actions=to_jsonable(actions),
        cleaned_from_run_id=run.id,
    )
