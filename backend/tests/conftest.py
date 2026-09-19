"""
conftest.py

Points the backend at a fresh temporary SQLite file before any
`backend.*` module is imported anywhere in the test session, so tests
never touch the real dev database (trusted_data_power_dev.db) or a
real Postgres instance. This must happen before backend.db.session is
first imported (it reads DATABASE_URL at import time), which is why
it's done here at module level, in conftest.py, which pytest always
loads before collecting test files in this directory.

Also disables the Phase 8 background scheduler (DISABLE_SCHEDULER) -
tests that exercise syncing call services.datasource_service.sync_datasource()
directly for deterministic control, rather than racing a real 60-second
timer thread against the test process.

Table creation: this calls Base.metadata.create_all() directly rather
than running Alembic migrations - deliberately different from the real
app (see main.py's docstring), since a disposable per-session test
database has no upgrade history to track and no real data to protect;
it only needs to match whatever the current models say, which
create_all() guarantees by construction.
"""

import os
import tempfile
import uuid

_tmp_dir = tempfile.mkdtemp(prefix="tdp_test_db_")
_tmp_db_path = os.path.join(_tmp_dir, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["DISABLE_SCHEDULER"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.db.base import Base  # noqa: E402
from backend.db.session import engine  # noqa: E402
from backend.main import app  # noqa: E402
import backend.models  # noqa: E402,F401 - registers every model on Base.metadata

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    """A fresh, registered user's bearer-token header, for tests that
    need an authenticated request but don't care about the user's
    identity or organization beyond "some real account"."""
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/auth/register", json={"email": email, "password": "password123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
