import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import scheduler


@pytest.fixture
def calls(monkeypatch):
    monkeypatch.setattr(scheduler.storage, "current_year", lambda: 2024)
    recorded = []

    def fake_enqueue(year, force=False):
        recorded.append((year, force))
        return [f"platform-for-{year}"]
    monkeypatch.setattr(scheduler.storage, "enqueue_missing_platforms", fake_enqueue)
    return recorded


def test_current_year_is_force_enqueued(calls):
    scheduler.handler({}, None)

    assert calls == [(2024, True)]


def test_past_years_are_never_touched(calls):
    # Past-year reddit is a multi-part job and most platforms' past years are
    # frozen snapshots — backfills are manual, not part of the weekly run.
    scheduler.handler({}, None)

    assert all(year == 2024 for year, _ in calls)


def test_return_shape(calls):
    result = scheduler.handler({}, None)

    assert result == {"queued_by_year": {2024: ["platform-for-2024"]}}
