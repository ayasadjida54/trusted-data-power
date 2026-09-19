"""
db.session

Database engine and session setup.

Designed for PostgreSQL in production (set DATABASE_URL, e.g.
"postgresql+psycopg2://user:password@host:5432/trusted_data_power").
When DATABASE_URL is not set, falls back to a local SQLite file so the
backend runs with zero setup during development - no code changes are
needed to switch, since all models use SQLAlchemy's cross-dialect JSON
type rather than anything Postgres-specific.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_SQLITE_URL = "sqlite:///./trusted_data_power_dev.db"

DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)

# SQLite requires this flag for use across FastAPI's threaded request
# handling; it's a no-op for PostgreSQL.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
