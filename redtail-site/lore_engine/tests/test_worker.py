import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import worker


def _install_fake_scraper(monkeypatch, platform, run_fn):
    mod = types.ModuleType(f"scrapers.{platform}")
    mod.run = run_fn
    monkeypatch.setitem(sys.modules, f"scrapers.{platform}", mod)


@pytest.fixture
def storage_spy(monkeypatch):
    calls = {"put_status": [], "put_records": [], "merge_by_key": [], "merge_nested_by_key": []}
    monkeypatch.setattr(worker.storage, "put_status",
                        lambda year, platform, status, error=None:
                        calls["put_status"].append((year, platform, status, error)))
    monkeypatch.setattr(worker.storage, "put_records",
                        lambda year, platform, records:
                        calls["put_records"].append((year, platform, records)))
    monkeypatch.setattr(worker.storage, "get_last_scraped", lambda year, platform: None)
    monkeypatch.setattr(worker.storage, "get_raw_records", lambda year, platform: [])

    def fake_merge_by_key(existing, new, key):
        calls["merge_by_key"].append((existing, new, key))
        return existing + new
    monkeypatch.setattr(worker.storage, "merge_by_key", fake_merge_by_key)

    def fake_merge_nested(existing, new, record_key, nested_field, nested_key):
        calls["merge_nested_by_key"].append((existing, new, record_key, nested_field, nested_key))
        return existing + new
    monkeypatch.setattr(worker.storage, "merge_nested_by_key", fake_merge_nested)
    return calls


def test_process_one_happy_path_no_merge(storage_spy, monkeypatch):
    _install_fake_scraper(monkeypatch, "faketestplatform", lambda **k: [{"a": 1}])

    worker._process_one(2024, "faketestplatform")

    assert storage_spy["put_records"] == [(2024, "faketestplatform", [{"a": 1}])]
    statuses = [c[2] for c in storage_spy["put_status"]]
    assert statuses == ["running", "done"]
    assert storage_spy["merge_by_key"] == []
    assert storage_spy["merge_nested_by_key"] == []


def test_process_one_empty_records_sets_status_empty(storage_spy, monkeypatch):
    _install_fake_scraper(monkeypatch, "faketestplatform", lambda **k: [])

    worker._process_one(2024, "faketestplatform")

    statuses = [c[2] for c in storage_spy["put_status"]]
    assert statuses == ["running", "empty"]


def test_process_one_error_sets_status_error_and_reraises(storage_spy, monkeypatch):
    def failing_run(**k):
        raise RuntimeError("boom")
    _install_fake_scraper(monkeypatch, "faketestplatform", failing_run)

    with pytest.raises(RuntimeError, match="boom"):
        worker._process_one(2024, "faketestplatform")

    statuses = [c[2] for c in storage_spy["put_status"]]
    assert statuses == ["running", "error"]
    assert storage_spy["put_status"][-1][3] == "RuntimeError: boom"


def test_process_one_merge_key_platform_passes_since(storage_spy, monkeypatch):
    since = "2024-01-01T00:00:00Z"
    monkeypatch.setattr(worker.storage, "get_last_scraped", lambda year, platform: since)
    monkeypatch.setattr(worker.storage, "get_raw_records", lambda year, platform: [{"id": "old"}])
    captured_kwargs = {}

    def fake_run(**k):
        captured_kwargs.update(k)
        return [{"id": "new"}]
    _install_fake_scraper(monkeypatch, "hackernews", fake_run)

    worker._process_one(2024, "hackernews")

    assert captured_kwargs.get("since") == since
    assert storage_spy["merge_by_key"] == [([{"id": "old"}], [{"id": "new"}], "id")]
    assert storage_spy["put_records"] == [(2024, "hackernews", [{"id": "old"}, {"id": "new"}])]


def test_process_one_merge_key_platform_no_since_on_first_run(storage_spy, monkeypatch):
    captured_kwargs = {}

    def fake_run(**k):
        captured_kwargs.update(k)
        return [{"id": "new"}]
    _install_fake_scraper(monkeypatch, "hackernews", fake_run)

    worker._process_one(2024, "hackernews")  # get_last_scraped stubbed to None by storage_spy

    assert "since" not in captured_kwargs


def test_process_one_nested_merge_key_platform(storage_spy, monkeypatch):
    since = "2024-01-01T00:00:00Z"
    monkeypatch.setattr(worker.storage, "get_last_scraped", lambda year, platform: since)
    monkeypatch.setattr(worker.storage, "get_raw_records",
                        lambda year, platform: [{"app_id": "999", "reviews": [{"id": "old"}]}])
    captured_kwargs = {}

    def fake_run(**k):
        captured_kwargs.update(k)
        return [{"app_id": "999", "reviews": [{"id": "new"}]}]
    _install_fake_scraper(monkeypatch, "steam", fake_run)

    worker._process_one(2024, "steam")

    assert captured_kwargs.get("since") == since
    assert storage_spy["merge_nested_by_key"] == [
        ([{"app_id": "999", "reviews": [{"id": "old"}]}],
         [{"app_id": "999", "reviews": [{"id": "new"}]}],
         "app_id", "reviews", "id"),
    ]


def test_handler_processes_every_record_in_the_event(monkeypatch):
    processed = []
    monkeypatch.setattr(worker, "_process_one", lambda year, platform: processed.append((year, platform)))
    event = {"Records": [
        {"body": json.dumps({"year": 2024, "platform": "steamcharts"})},
        {"body": json.dumps({"year": 2023, "platform": "hackernews"})},
    ]}

    worker.handler(event, None)

    assert processed == [(2024, "steamcharts"), (2023, "hackernews")]
