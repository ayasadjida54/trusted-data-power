"""
models.organization

An Organization is a workspace - "per-business workspaces" from the
spec. Every User belongs to exactly one Organization (set at
registration), and every Dataset belongs to an Organization rather than
to an individual User, so teammates in the same organization see the
same datasets. This is the multi-tenancy boundary: all data access is
scoped by organization_id, not by user_id.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from backend.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="organization")
    datasets = relationship(
        "Dataset", back_populates="organization", cascade="all, delete-orphan"
    )
