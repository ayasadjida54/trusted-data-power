"""
test_scheduler.py

Tests the scheduler's pure due/not-due logic directly (no real timer
involved), and confirms DISABLE_SCHEDULER actually prevents a
scheduler from starting - the guard the rest of the test suite relies
on for determinism.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from backend.services.scheduler import _is_due, start_scheduler


def _fake_source(interval_minutes, last_synced_at):
    source = Mock()
    source.sync_interval_minutes = interval_minutes
    source.last_synced_at = last_synced_at
    return source


def test_never_synced_source_with_interval_is_due():
    source = _fake_source(interval_minutes=60, last_synced_at=None)
    assert _is_due(source, datetime.now(timezone.utc)) is True


def test_source_with_no_interval_is_never_due():
    source = _fake_source(interval_minutes=None, last_synced_at=None)
    assert _is_due(source, datetime.now(timezone.utc)) is False


def test_source_synced_recently_is_not_due():
    now = datetime.now(timezone.utc)
    source = _fake_source(interval_minutes=60, last_synced_at=now - timedelta(minutes=5))
    assert _is_due(source, now) is False


def test_source_synced_longer_ago_than_interval_is_due():
    now = datetime.now(timezone.utc)
    source = _fake_source(interval_minutes=60, last_synced_at=now - timedelta(minutes=61))
    assert _is_due(source, now) is True


def test_source_synced_exactly_at_interval_is_due():
    now = datetime.now(timezone.utc)
    source = _fake_source(interval_minutes=60, last_synced_at=now - timedelta(minutes=60))
    assert _is_due(source, now) is True


def test_scheduler_disabled_in_test_environment():
    # conftest.py sets DISABLE_SCHEDULER=1 before backend.main is
    # imported anywhere in this test session - confirms that guard
    # actually works, since every other test in this suite depends on
    # no real background timer running during the test run.
    assert start_scheduler() is None
