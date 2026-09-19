"""
schemas.analysis

Pydantic response models for the API. Kept separate from the
SQLAlchemy models (backend.models) so the database schema and the API
contract can evolve independently - e.g. Phase 4 auth fields on User
don't need to leak into every response that includes a dataset.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRunSummary(BaseModel):
    """Lightweight run info - used in lists, no full issue/score detail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    created_at: datetime
    score: float
    score_label: str
    cleaned_from_run_id: int | None = None


class AnalysisRunDetail(AnalysisRunSummary):
    """Full run detail - the complete engine result, as stored."""

    model_config = ConfigDict(from_attributes=True)

    dataset_id: int
    profile: dict[str, Any]
    column_dtypes: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    numeric_stats: list[dict[str, Any]]
    issue_counts: dict[str, Any]
    recommendations: list[str]
    dimension_scores: dict[str, Any]
    dimension_weights: dict[str, Any]
    score_explanation: list[str]
    column_scores: dict[str, Any]
    cleaning_actions: list[str] | None = None


class DatasetSummary(BaseModel):
    """A dataset slot with its most recent run, for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    latest_run: AnalysisRunSummary | None = None


class ComparisonResult(BaseModel):
    """Phase 5: the diff between two runs of the same dataset slot."""

    previous_run_id: int
    current_run_id: int
    score_delta: float
    previous_score: float
    current_score: float
    previous_label: str
    current_label: str
    dimension_deltas: dict[str, float]
    new_issues: list[dict[str, Any]]
    resolved_issues: list[dict[str, Any]]
    worsened_issues: list[dict[str, Any]]
    improved_issues: list[dict[str, Any]]
    summary: list[str]


class ShareResponse(BaseModel):
    """Phase 6: a run's public share token and the path to view it."""

    share_token: str
    share_path: str


class MonitoringSettings(BaseModel):
    """Phase 7: a dataset's monitoring configuration."""

    monitoring_enabled: bool
    alert_threshold_points: float


class MonitoringUpdate(BaseModel):
    monitoring_enabled: bool
    alert_threshold_points: float = Field(gt=0)


class AlertOut(BaseModel):
    """Phase 7: one detected score-drop event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    previous_run_id: int
    current_run_id: int
    score_delta: float
    summary: list[str]
    is_read: bool
    created_at: datetime


class LinkSheetRequest(BaseModel):
    """Phase 8: link (or re-link) a dataset to a Google Sheet."""

    sheet_url: str
    dataset_id: int | None = None
    dataset_name: str | None = None
    sync_interval_minutes: int | None = Field(default=None, gt=0)


class DataSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    source_type: str
    source_url: str
    sync_interval_minutes: int | None
    last_synced_at: datetime | None
    last_sync_status: str | None
    last_sync_error: str | None
