"""
services.datasource_service

Links a Dataset slot to a Google Sheet, and syncs it - fetches the
current sheet contents, runs it through the same analysis + storage
path a file upload uses (analysis_service.store_analysis_result), and
records whether the sync succeeded.

sync_datasource() is called from two places: the API route (manual
"Sync now" / initial link) and services/scheduler.py (automatic
background sync). Both go through this one function, so there's a
single place that updates last_synced_at/last_sync_status - a
scheduled sync and a manual one are indistinguishable to the rest of
the system, which is exactly what makes this a drop-in for Phase 7's
"any new run" alert detection.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models import DataSource, Dataset
from backend.services.analysis_service import resolve_dataset, store_analysis_result
from backend.services.sheets_connector import InvalidSheetUrl, SheetFetchError, fetch_sheet_as_dataframe
from engine import analyze_dataframe


class DatasetNotFound(Exception):
    pass


class NoDataSource(Exception):
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


def link_google_sheet(
    db: Session,
    organization_id: int,
    sheet_url: str,
    dataset_id: int | None = None,
    dataset_name: str | None = None,
    sync_interval_minutes: int | None = None,
):
    """
    Resolve/create the target Dataset (same resolution rules as file
    upload - explicit id, or name match, or a new slot), attach a
    DataSource pointing at `sheet_url`, and perform an immediate sync.

    Returns (dataset, run) - `run` is the AnalysisRun from the initial
    sync. Raises InvalidSheetUrl/SheetFetchError (propagated from
    sheets_connector) if the initial sync fails - the link is NOT
    created in that case, so a bad URL never leaves a dataset pointing
    at a source that's never worked.
    """
    # Validate/fetch BEFORE creating anything, so a bad URL doesn't
    # leave a half-created dataset or data source behind.
    df = fetch_sheet_as_dataframe(sheet_url)
    result = analyze_dataframe(df)

    dataset = resolve_dataset(
        db, organization_id, dataset_id, dataset_name, fallback_name="Google Sheet"
    )

    if dataset.data_source is not None:
        dataset.data_source.source_url = sheet_url
        dataset.data_source.sync_interval_minutes = sync_interval_minutes
    else:
        dataset.data_source = DataSource(
            source_type="google_sheets",
            source_url=sheet_url,
            sync_interval_minutes=sync_interval_minutes,
        )
    db.flush()

    run = store_analysis_result(
        db, dataset, filename=f"{dataset.name} (Google Sheet)", result=result, raw_df=df
    )

    dataset.data_source.last_synced_at = datetime.now(timezone.utc)
    dataset.data_source.last_sync_status = "success"
    dataset.data_source.last_sync_error = None
    db.commit()

    return dataset, run


def sync_datasource(db: Session, data_source: DataSource):
    """
    Re-fetch and re-analyze the sheet behind `data_source`, storing a
    new AnalysisRun (and running Phase 7 alert detection against the
    dataset's previous run, via store_analysis_result). Always updates
    last_synced_at/last_sync_status, including on failure - so a
    dashboard can show "last checked 3 minutes ago, failed" rather than
    going silent when a sheet becomes unreachable.

    Does not raise on a fetch/parse failure - the failure is recorded
    on the DataSource itself instead, since this is the function the
    unattended background scheduler calls, and there's no one to catch
    an exception there.
    """
    dataset = data_source.dataset
    data_source.last_synced_at = datetime.now(timezone.utc)

    try:
        df = fetch_sheet_as_dataframe(data_source.source_url)
        result = analyze_dataframe(df)
    except (InvalidSheetUrl, SheetFetchError, ValueError) as exc:
        data_source.last_sync_status = "error"
        data_source.last_sync_error = str(exc)
        db.commit()
        return None

    run = store_analysis_result(
        db, dataset, filename=f"{dataset.name} (Google Sheet)", result=result, raw_df=df
    )
    data_source.last_sync_status = "success"
    data_source.last_sync_error = None
    db.commit()
    return run


def sync_dataset_now(db: Session, organization_id: int, dataset_id: int):
    dataset = _get_owned_dataset(db, organization_id, dataset_id)
    if dataset.data_source is None:
        raise NoDataSource(f"Dataset {dataset_id} has no linked data source.")
    return sync_datasource(db, dataset.data_source)


def get_datasource(db: Session, organization_id: int, dataset_id: int) -> DataSource | None:
    dataset = _get_owned_dataset(db, organization_id, dataset_id)
    return dataset.data_source


def unlink_datasource(db: Session, organization_id: int, dataset_id: int) -> None:
    dataset = _get_owned_dataset(db, organization_id, dataset_id)
    if dataset.data_source is not None:
        db.delete(dataset.data_source)
        db.commit()
