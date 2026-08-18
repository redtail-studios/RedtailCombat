import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import scrapers.googletrends as googletrends


class FakeSeries:
    def __init__(self, values):
        self._values = values

    def mean(self):
        return sum(self._values) / len(self._values)


class FakeIOT:
    """Stand-in for the pandas DataFrame pytrends.interest_over_time() returns."""
    empty = False

    def __init__(self, term, values):
        self._term = term
        self._values = values

    def __contains__(self, key):
        return key == self._term

    def __getitem__(self, key):
        return FakeSeries(self._values)


class EmptyIOT:
    empty = True


class FakeRisingDF:
    """Stand-in for the pandas DataFrame related_queries()[...]['rising']."""
    def __init__(self, rows):
        self.empty = len(rows) == 0
        self._rows = rows

    def head(self, n):
        return FakeRisingDF(self._rows[:n])

    def iterrows(self):
        return enumerate(self._rows)


def _install_fake_pytrends(monkeypatch, trend_req_cls):
    fake_request = types.ModuleType("pytrends.request")
    fake_request.TrendReq = trend_req_cls
    fake_pkg = types.ModuleType("pytrends")
    monkeypatch.setitem(sys.modules, "pytrends", fake_pkg)
    monkeypatch.setitem(sys.modules, "pytrends.request", fake_request)


@pytest.fixture
def one_term(monkeypatch):
    monkeypatch.setattr(googletrends, "GENRES", {})
    monkeypatch.setattr(googletrends, "ACTIVE_GENRES", [])
    monkeypatch.setattr(googletrends, "TREND_TERMS_COMMON", ["fake term"])
    monkeypatch.setattr(googletrends, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(googletrends, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(googletrends.time, "sleep", lambda *a: None)


def test_pytrends_not_installed_skips_without_crashing(one_term, monkeypatch):
    # Simulate the library being absent: None in sys.modules forces
    # `from pytrends.request import TrendReq` to raise ImportError.
    monkeypatch.setitem(sys.modules, "pytrends.request", None)

    assert googletrends.run(log=lambda *a: None) == []


def test_trendreq_init_failure_skips_without_crashing(one_term, monkeypatch):
    class BrokenTrendReq:
        def __init__(self, hl, tz):
            raise RuntimeError("connection refused")
    _install_fake_pytrends(monkeypatch, BrokenTrendReq)

    assert googletrends.run(log=lambda *a: None) == []


def test_term_with_no_data_and_no_rising_is_skipped(one_term, monkeypatch):
    class NoDataTrendReq:
        def __init__(self, hl, tz):
            pass
        def build_payload(self, kw_list, timeframe):
            pass
        def interest_over_time(self):
            return EmptyIOT()
        def related_queries(self):
            return {}
    _install_fake_pytrends(monkeypatch, NoDataTrendReq)

    assert googletrends.run(log=lambda *a: None) == []


def test_happy_path_record_fields(one_term, monkeypatch):
    class HappyTrendReq:
        def __init__(self, hl, tz):
            pass
        def build_payload(self, kw_list, timeframe):
            self._term = kw_list[0]
        def interest_over_time(self):
            return FakeIOT(self._term, [10, 20, 30])
        def related_queries(self):
            return {self._term: {"rising": FakeRisingDF(
                [{"query": "fake term guide", "value": 150}])}}
    _install_fake_pytrends(monkeypatch, HappyTrendReq)

    records = googletrends.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["term"] == "fake term"
    assert r["avg_interest"] == 20.0
    assert r["rising_queries"] == ["fake term guide (+150%)"]
    assert "sentiment" in r


def test_transient_failure_retries_then_succeeds(one_term, monkeypatch):
    class FlakyThenOkTrendReq:
        attempts = 0

        def __init__(self, hl, tz):
            pass

        def build_payload(self, kw_list, timeframe):
            self._term = kw_list[0]
            FlakyThenOkTrendReq.attempts += 1
            if FlakyThenOkTrendReq.attempts < 2:
                raise RuntimeError("429 rate limited")

        def interest_over_time(self):
            return FakeIOT(self._term, [5, 5])

        def related_queries(self):
            return {self._term: {"rising": FakeRisingDF([])}}
    _install_fake_pytrends(monkeypatch, FlakyThenOkTrendReq)

    records = googletrends.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["avg_interest"] == 5.0
    assert FlakyThenOkTrendReq.attempts == 2


def test_all_attempts_failing_skips_the_term(one_term, monkeypatch):
    class AlwaysFailsTrendReq:
        def __init__(self, hl, tz):
            pass
        def build_payload(self, kw_list, timeframe):
            raise RuntimeError("429 rate limited")
    _install_fake_pytrends(monkeypatch, AlwaysFailsTrendReq)

    assert googletrends.run(log=lambda *a: None) == []
