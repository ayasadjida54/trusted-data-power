"""
models.datasource

Phase 8: a DataSource links one Dataset slot to an external source it
can be re-synced from - currently only Google Sheets (see
services/sheets_connector.py), kept as a `source_type` string rather
than a dedicated table-per-source so a future second source type
doesn't require a schema migration, just a new value and a new
connector module.

One Dataset has at most one DataSource (one-to-one) - linking a sheet
to a dataset that already has one replaces it, rather than stacking
multiple sources into one slot's history, which would make "what
produced this run" ambiguous.

sync_interval_minutes controls automatic syncing (see
services/scheduler.py): NULL means manual sync only ("Sync now" in the
UI); a number means the background scheduler will re-fetch and
re-analyze on that cadence, running the same Phase 7 alert-detection
path a manual sync or file upload does.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, unique=True)

    source_type = Column(String, nullable=False, default="google_sheets")
    source_url = Column(String, nullable=False)

    sync_interval_minutes = Column(Integer, nullable=True)  # NULL = manual sync only
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, nullable=True)  # "success" | "error" | NULL (never synced)
    last_sync_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    dataset = relationship("Dataset", back_populates="data_source")
