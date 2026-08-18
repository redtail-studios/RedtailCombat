import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from botocore.exceptions import ClientError

import storage


def _client_error(code):
    return ClientError({"Error": {"Code": code}}, "TestOperation")


class FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data


class FakePaginator:
    def __init__(self, client):
        self.client = client

    def paginate(self, Bucket, Prefix):
        yield {"Contents": [{"Key": k} for k in self.client.objects if k.startswith(Prefix)]}


class FakeS3:
    def __init__(self):
        self.objects = {}  # key -> {"body": bytes, "last_modified": datetime, "metadata": dict}

    def put(self, key, body: bytes, last_modified=None, metadata=None):
        self.objects[key] = {
            "body": body,
            "last_modified": last_modified or datetime.now(timezone.utc),
            "metadata": metadata or {},
        }

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise _client_error("404")
        obj = self.objects[Key]
        return {"LastModified": obj["last_modified"], "Metadata": obj["metadata"]}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise _client_error("NoSuchKey")
        obj = self.objects[Key]
        return {"LastModified": obj["last_modified"], "Body": FakeBody(obj["body"])}

    def put_object(self, Bucket, Key, Body, ContentType=None, Metadata=None):
        self.objects[Key] = {
            "body": Body, "last_modified": datetime.now(timezone.utc), "metadata": Metadata or {},
        }

    def get_paginator(self, name):
        return FakePaginator(self)


class FakeSQS:
    def __init__(self):
        self.sent = []

    def send_message(self, QueueUrl, MessageBody):
        self.sent.append((QueueUrl, MessageBody))


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "_s3_client", lambda: fake)
    return fake


@pytest.fixture
def sqs(monkeypatch):
    fake = FakeSQS()
    monkeypatch.setattr(storage, "_sqs_client", lambda: fake)
    return fake


@pytest.fixture
def fixed_current_year(monkeypatch):
    monkeypatch.setattr(storage, "current_year", lambda: 2024)
    return 2024


# ---------------------------------------------------------------------------
# key helpers / _not_found / _is_fresh
# ---------------------------------------------------------------------------

def test_data_and_status_key_format():
    assert storage._data_key(2024, "steam") == f"{storage.DATA_PREFIX}/2024/steam.json"
    assert storage._status_key(2024, "steam") == f"{storage.STATUS_PREFIX}/2024/steam.json"


def test_not_found_recognizes_404_and_nosuchkey():
    assert storage._not_found(_client_error("404")) is True
    assert storage._not_found(_client_error("NoSuchKey")) is True


def test_not_found_false_for_other_error_codes():
    assert storage._not_found(_client_error("AccessDenied")) is False


def test_is_fresh_past_year_is_always_fresh(fixed_current_year):
    ancient = datetime.now(timezone.utc) - timedelta(days=3650)
    assert storage._is_fresh(2020, ancient) is True


def test_is_fresh_current_year_within_ttl(fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    recent = datetime.now(timezone.utc) - timedelta(seconds=10)
    assert storage._is_fresh(2024, recent) is True


def test_is_fresh_current_year_past_ttl(fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    old = datetime.now(timezone.utc) - timedelta(seconds=7200)
    assert storage._is_fresh(2024, old) is False


# ---------------------------------------------------------------------------
# merge_by_key / merge_nested_by_key
# ---------------------------------------------------------------------------

def test_merge_by_key_existing_wins_on_collision():
    existing = [{"url": "a", "title": "old"}]
    new = [{"url": "a", "title": "new"}]
    assert storage.merge_by_key(existing, new, "url") == [{"url": "a", "title": "old"}]


def test_merge_by_key_appends_genuinely_new_keys():
    existing = [{"url": "a"}]
    new = [{"url": "b"}]
    assert storage.merge_by_key(existing, new, "url") == [{"url": "a"}, {"url": "b"}]


def test_merge_by_key_skips_records_with_null_key():
    existing = []
    new = [{"url": None}, {"url": "b"}]
    assert storage.merge_by_key(existing, new, "url") == [{"url": "b"}]


def test_merge_nested_by_key_merges_reviews_keeps_new_top_level_fields():
    existing = [{"app_id": "1", "positive": 10, "reviews": [{"id": "r1"}]}]
    new = [{"app_id": "1", "positive": 20, "reviews": [{"id": "r2"}]}]

    merged = storage.merge_nested_by_key(existing, new, "app_id", "reviews", "id")

    assert len(merged) == 1
    assert merged[0]["positive"] == 20  # fresh top-level metric wins
    assert {r["id"] for r in merged[0]["reviews"]} == {"r1", "r2"}  # nested list merged


def test_merge_nested_by_key_keeps_untouched_existing_records():
    existing = [{"app_id": "1", "reviews": []}, {"app_id": "2", "reviews": []}]
    new = [{"app_id": "1", "reviews": []}]  # app "2" dropped out of this run

    merged = storage.merge_nested_by_key(existing, new, "app_id", "reviews", "id")

    assert {r["app_id"] for r in merged} == {"1", "2"}


# ---------------------------------------------------------------------------
# is_cached_fresh / get_cached_records / put_records
# ---------------------------------------------------------------------------

def test_is_cached_fresh_false_on_miss(s3, fixed_current_year):
    assert storage.is_cached_fresh(2024, "steam") is False


def test_is_cached_fresh_true_for_fresh_object(s3, fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    s3.put(storage._data_key(2024, "steam"), b"[]")
    assert storage.is_cached_fresh(2024, "steam") is True


def test_is_cached_fresh_reraises_non_404_errors(s3, monkeypatch):
    def raise_other(Bucket, Key):
        raise _client_error("AccessDenied")
    monkeypatch.setattr(s3, "head_object", raise_other)

    with pytest.raises(ClientError):
        storage.is_cached_fresh(2024, "steam")


def test_get_cached_records_none_on_miss(s3):
    assert storage.get_cached_records(2024, "steam") is None


def test_get_cached_records_none_when_stale(s3, fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    old = datetime.now(timezone.utc) - timedelta(seconds=7200)
    s3.put(storage._data_key(2024, "steam"), b"[1,2,3]", last_modified=old)

    assert storage.get_cached_records(2024, "steam") is None


def test_get_cached_records_returns_parsed_json_when_fresh(s3, fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    s3.put(storage._data_key(2024, "steam"), json.dumps([{"a": 1}]).encode())

    assert storage.get_cached_records(2024, "steam") == [{"a": 1}]


def test_put_records_stores_json_with_count_metadata(s3):
    storage.put_records(2024, "steam", [{"a": 1}, {"a": 2}])

    stored = s3.objects[storage._data_key(2024, "steam")]
    assert json.loads(stored["body"]) == [{"a": 1}, {"a": 2}]
    assert stored["metadata"] == {"count": "2"}


# ---------------------------------------------------------------------------
# get_last_scraped / get_raw_records
# ---------------------------------------------------------------------------

def test_get_last_scraped_none_on_miss(s3):
    assert storage.get_last_scraped(2024, "hackernews") is None


def test_get_last_scraped_returns_last_modified(s3):
    lm = datetime(2024, 6, 1, tzinfo=timezone.utc)
    s3.put(storage._data_key(2024, "hackernews"), b"[]", last_modified=lm)

    assert storage.get_last_scraped(2024, "hackernews") == lm


def test_get_raw_records_none_on_miss(s3):
    assert storage.get_raw_records(2024, "hackernews") is None


def test_get_raw_records_ignores_staleness(s3, fixed_current_year, monkeypatch):
    # Unlike get_cached_records, this path is used specifically to read
    # "stale" data as the basis for an incremental merge, so it must not
    # apply the TTL freshness check.
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    old = datetime.now(timezone.utc) - timedelta(seconds=7200)
    s3.put(storage._data_key(2024, "hackernews"), json.dumps([{"id": "old"}]).encode(),
           last_modified=old)

    assert storage.get_raw_records(2024, "hackernews") == [{"id": "old"}]


# ---------------------------------------------------------------------------
# put_status / get_status / get_all_statuses
# ---------------------------------------------------------------------------

def test_put_status_truncates_error_to_500_chars(s3):
    storage.put_status(2024, "steam", "error", error="x" * 1000)

    doc = json.loads(s3.objects[storage._status_key(2024, "steam")]["body"])
    assert doc["status"] == "error"
    assert len(doc["error"]) == 500


def test_get_status_idle_on_miss(s3):
    assert storage.get_status(2024, "steam") == {"status": "idle"}


def test_get_status_returns_parsed_doc(s3):
    storage.put_status(2024, "steam", "done")
    assert storage.get_status(2024, "steam")["status"] == "done"


def test_get_all_statuses_fans_out_over_platform_ids(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    storage.put_status(2024, "steam", "done")

    result = storage.get_all_statuses(2024)

    assert result == {"steam": "done", "reddit": "idle"}


# ---------------------------------------------------------------------------
# compute_manifest
# ---------------------------------------------------------------------------

def test_compute_manifest_builds_years_and_totals(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_records(2024, "steam", [{"a": 1}, {"a": 2}])
    storage.put_records(2024, "reddit", [{"a": 1}])

    manifest = storage.compute_manifest()

    assert manifest["years"]["2024"] == {"sources": {"steam": 2, "reddit": 1}, "total": 3}


def test_compute_manifest_omits_platforms_with_zero_count(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_records(2024, "steam", [{"a": 1}])
    storage.put_records(2024, "reddit", [])  # count=0 -> omitted

    manifest = storage.compute_manifest()

    assert manifest["years"]["2024"]["sources"] == {"steam": 1}


def test_compute_manifest_tolerates_head_failure_on_a_listed_object(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_records(2024, "steam", [{"a": 1}])
    storage.put_records(2024, "reddit", [{"a": 1}])
    real_head = s3.head_object

    def flaky_head(Bucket, Key):
        if Key == storage._data_key(2024, "reddit"):
            raise _client_error("InternalError")
        return real_head(Bucket, Key)
    monkeypatch.setattr(s3, "head_object", flaky_head)

    manifest = storage.compute_manifest()

    assert manifest["years"]["2024"]["sources"] == {"steam": 1}  # reddit dropped, not crashed


def test_compute_manifest_no_data_returns_unknown_scraped_at(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])

    manifest = storage.compute_manifest()

    assert manifest["years"] == {}
    assert manifest["scraped_at"] == "unknown"


# ---------------------------------------------------------------------------
# scrape_status_snapshot
# ---------------------------------------------------------------------------

def test_snapshot_idle_when_every_platform_idle(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])

    result = storage.scrape_status_snapshot(2024)

    assert result["status"] == "idle"


def test_snapshot_running_when_any_platform_in_progress(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_status(2024, "steam", "running")

    result = storage.scrape_status_snapshot(2024)

    assert result["status"] == "running"


def test_snapshot_done_when_all_terminal_and_manifest_has_data(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_status(2024, "steam", "done")
    storage.put_records(2024, "steam", [{"a": 1}])

    result = storage.scrape_status_snapshot(2024)

    assert result["status"] == "done"
    assert "error" not in result


def test_snapshot_error_when_all_terminal_but_no_usable_data(s3, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(storage, "SUPPORTED_YEARS", [2024])
    storage.put_status(2024, "steam", "empty")  # terminal, but never wrote any records

    result = storage.scrape_status_snapshot(2024)

    assert result["status"] == "error"
    assert result["error"] == "Scrape finished with no usable data"


# ---------------------------------------------------------------------------
# enqueue_scrape / enqueue_missing_platforms
# ---------------------------------------------------------------------------

def test_enqueue_scrape_sends_sqs_message(sqs, monkeypatch):
    monkeypatch.setattr(storage, "QUEUE_URL", "https://queue.example/q")

    storage.enqueue_scrape(2024, "steam")

    assert len(sqs.sent) == 1
    url, body = sqs.sent[0]
    assert url == "https://queue.example/q"
    assert json.loads(body) == {"year": 2024, "platform": "steam"}


def test_enqueue_missing_platforms_force_true_enqueues_everything(s3, sqs, fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    # Even a fresh platform gets re-enqueued when force=True.
    s3.put(storage._data_key(2024, "steam"), b"[]")

    queued = storage.enqueue_missing_platforms(2024, force=True)

    assert queued == ["steam", "reddit"]
    assert len(sqs.sent) == 2


def test_enqueue_missing_platforms_force_false_skips_fresh(s3, sqs, fixed_current_year, monkeypatch):
    monkeypatch.setattr(storage, "PLATFORM_IDS", ["steam", "reddit"])
    monkeypatch.setattr(storage, "TTL_SECONDS", 3600)
    s3.put(storage._data_key(2024, "steam"), b"[]")  # fresh -> skipped

    queued = storage.enqueue_missing_platforms(2024, force=False)

    assert queued == ["reddit"]
    assert len(sqs.sent) == 1
