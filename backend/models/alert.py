"""
models.alert

An Alert is created automatically (see services/monitoring_service.py)
when a new run is added to a monitored Dataset and its score drops by
at least that dataset's alert_threshold_points compared to the
immediately preceding run. It stores the comparison's summary
sentences (from engine.compare_analysis_results - see Phase 5) at
creation time, so the alert's explanation doesn't change even if the
underlying runs are later affected by anything else.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    previous_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)
    current_run_id = Column(Integer, ForeignKey("analysis_runs.id"), nullable=False)

    score_delta = Column(Float, nullable=False)
    summary = Column(JSON, nullable=False)  # list[str], from compare_analysis_results

    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    dataset = relationship("Dataset", back_populates="alerts")
    previous_run = relationship("AnalysisRun", foreign_keys=[previous_run_id])
    current_run = relationship("AnalysisRun", foreign_keys=[current_run_id])
