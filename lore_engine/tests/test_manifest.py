import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import manifest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(manifest, "SUPPORTED_YEARS", [2023, 2024])
    return tmp_path


def _write(data_dir, year, name, content):
    ydir = data_dir / str(year)
    ydir.mkdir(parents=True, exist_ok=True)
    (ydir / f"{name}_data.json").write_text(json.dumps(content), encoding="utf-8")


def test_rebuild_with_no_data_dirs_returns_empty_years(data_dir):
    result = manifest.rebuild()

    assert result["years"] == {}


def test_rebuild_reads_data_files_and_counts_records(data_dir):
    _write(data_dir, 2024, "appstore", [{"a": 1}, {"a": 2}, {"a": 3}])

    result = manifest.rebuild()

    assert result["years"]["2024"] == {"sources": {"appstore": 3}, "total": 3}


def test_rebuild_skips_malformed_json_without_crashing(data_dir):
    ydir = data_dir / "2024"
    ydir.mkdir(parents=True, exist_ok=True)
    (ydir / "broken_data.json").write_text("not valid json {{{", encoding="utf-8")
    _write(data_dir, 2024, "appstore", [{"a": 1}])

    result = manifest.rebuild()

    assert result["years"]["2024"]["sources"] == {"appstore": 1}


def test_rebuild_omits_empty_sources(data_dir):
    _write(data_dir, 2024, "empty_source", [])
    _write(data_dir, 2024, "appstore", [{"a": 1}])

    result = manifest.rebuild()

    assert result["years"]["2024"]["sources"] == {"appstore": 1}


def test_rebuild_counts_non_list_json_as_one(data_dir):
    _write(data_dir, 2024, "weird_source", {"not": "a list"})

    result = manifest.rebuild()

    assert result["years"]["2024"]["sources"] == {"weird_source": 1}


def test_rebuild_name_strips_data_suffix_from_filename(data_dir):
    _write(data_dir, 2024, "steamcharts", [{"a": 1}])

    result = manifest.rebuild()

    assert "steamcharts" in result["years"]["2024"]["sources"]


def test_rebuild_writes_manifest_json_to_disk(data_dir):
    _write(data_dir, 2024, "appstore", [{"a": 1}])

    result = manifest.rebuild()

    written = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert written == result


def test_rebuild_only_considers_supported_years(data_dir, monkeypatch):
    monkeypatch.setattr(manifest, "SUPPORTED_YEARS", [2024])  # 2099 not supported
    _write(data_dir, 2099, "appstore", [{"a": 1}])

    result = manifest.rebuild()

    assert result["years"] == {}
