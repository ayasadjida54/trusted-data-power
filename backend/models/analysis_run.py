"""
models.analysis_run

One AnalysisRun row is stored per uploaded file: the full result of
engine.analyze_dataframe(), serialized to JSON columns. The score and
score_label are also stored as their own plain columns (redundant with
dimension_scores/JSON, but this is what lets Phase 5's trend queries
sort/filter by score directly, without unpacking JSON in the query).

Column-level detail from the DataFrame outputs (numeric_stats,
column_dtypes) is stored as JSON via `.to_dict(orient="records")` -
see services/analysis_service.py for the DataFrame -> JSON conversion.

column_scores and score_explanation (Phase 3) are stored exactly as
engine.analyze_dataframe() returns them - a dict keyed by column name,
and a list of explanation sentences, respectively.

raw_data_csv (DataScore cleaning pipeline): the actual analyzed data,
serialized as CSV text, so a later "clean this dataset" action has
something to clean - the JSON columns above are all computed
SUMMARIES of the data, not the data itself. Nullable so older rows
(and any run type that doesn't want to pay the storage cost) can leave
it unset; the clean-dataset action simply isn't offered for a run with
no raw data stored. This does mean a wide dataset's full contents are
duplicated into the database on every run - an explicit, acceptable
trade-off at this product's current scale, not something to carry
forward silently if it ever needs to scale up.

cleaning_actions / cleaned_from_run_id: set only on a run PRODUCED by
the cleaning pipeline (see services/cleaning_service.py) - the
plain-language list of what was fixed, and which run it was cleaned
from, so the UI can show "this is a cleaned version of run #12" and
list exactly what changed.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)

    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    score = Column(Float, nullable=False)
    score_label = Column(String, nullable=False)

    profile = Column(JSON, nullable=False)
    column_dtypes = Column(JSON, nullable=False)
    issues = Column(JSON, nullable=False)
    numeric_stats = Column(JSON, nullable=False)
    issue_counts = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    dimension_scores = Column(JSON, nullable=False)
    dimension_weights = Column(JSON, nullable=False)
    score_explanation = Column(JSON, nullable=False)
    column_scores = Column(JSON, nullable=False)

    # Phase 6: set only when someone generates a share link for this run
    # (see services/share_service.py). NULL means "not shared" - the
    # public report route 404s on a run with no token, same as on an
    # unrecognized one, so "shared vs not" isn't distinguishable from
    # the outside.
    share_token = Column(String, unique=True, nullable=True, index=True)

    raw_data_csv = Column(Text, nullable=True)
    cleaning_actions = Column(JSON, nullable=True)
    cleaned_from_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=True)

    dataset = relationship("Dataset", back_populates="runs")
