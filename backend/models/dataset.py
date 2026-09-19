"""
models.dataset

A Dataset is a named "slot" belonging to an ORGANIZATION (a workspace),
not to an individual user - e.g. "Monthly Sales Export", shared by
everyone on that team. Each time someone uploads a new file for that
slot, a new AnalysisRun is created and linked to it. Modeling this as a
slot (rather than one row per upload) from the start means Phase 5
(history, trends, comparison) needs no schema change - it's already
the right shape, just unused until then.

For Phase 1-3, one dataset slot was created per upload with no reuse
logic - the upload endpoint always creates a fresh Dataset. Phase 5
added reuse (by dataset_id or matching name) so repeat uploads
accumulate into one slot's version history.

Phase 7 (monitoring): monitoring_enabled and alert_threshold_points
control whether a new run in this slot gets compared against the
previous one and an Alert raised if the score drops by at least the
threshold. See services/monitoring_service.py.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base import Base

DEFAULT_ALERT_THRESHOLD_POINTS = 5.0


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    monitoring_enabled = Column(Boolean, nullable=False, default=False)
    alert_threshold_points = Column(Float, nullable=False, default=DEFAULT_ALERT_THRESHOLD_POINTS)

    organization = relationship("Organization", back_populates="datasets")
    runs = relationship(
        "AnalysisRun",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="AnalysisRun.created_at",
    )
    alerts = relationship(
        "Alert", back_populates="dataset", cascade="all, delete-orphan", order_by="Alert.created_at"
    )
    data_source = relationship(
        "DataSource", back_populates="dataset", uselist=False, cascade="all, delete-orphan"
    )
