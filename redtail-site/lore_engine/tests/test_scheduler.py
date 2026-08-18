import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import scheduler


@pytest.fixture
def calls(monkeypatch):
    monkeypatch.setattr(scheduler.storage, "current_year", lambda: 2024)
    monkeypatch.setattr(scheduler.config, "SUPPORTED_YEARS", [2022, 2023, 2024])
    recorded = []

    def fake_enqueue(year, force=False):
        recorded.append((year, force))
        return [f"platform-for-{year}"]
    monkeypatch.setattr(scheduler.storage, "enqueue_missing_platforms", fake_enqueue)
    return recorded


def test_current_year_is_force_enqueued(calls):
    scheduler.handler({}, None)

    assert (2024, True) in calls


def test_past_years_are_backfill_only(calls):
    scheduler.handler({}, None)

    assert (2022, False) in calls
    assert (2023, False) in calls


def test_current_year_not_double_enqueued(calls):
    scheduler.handler({}, None)

    current_year_calls = [c for c in calls if c[0] == 2024]
    assert len(current_year_calls) == 1


def test_return_shape(calls):
    result = scheduler.handler({}, None)

    assert result == {"queued_by_year": {
        2024: ["platform-for-2024"],
        2022: ["platform-for-2022"],
        2023: ["platform-for-2023"],
    }}
