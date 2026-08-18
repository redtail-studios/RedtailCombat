import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scrapers


def test_save_creates_directory_and_writes_json(tmp_path):
    data_dir = tmp_path / "nested" / "dir"

    result = scrapers.save([{"a": 1}, {"a": 2}], str(data_dir), "steam", log=lambda *a: None)

    written = json.loads((data_dir / "steam_data.json").read_text(encoding="utf-8"))
    assert written == [{"a": 1}, {"a": 2}]
    assert result == [{"a": 1}, {"a": 2}]


def test_save_logs_a_summary_message(tmp_path):
    logs = []

    scrapers.save([{"a": 1}], str(tmp_path), "steam", log=logs.append)

    assert any("saved 1 records" in msg for msg in logs)


def test_score_returns_vader_compound_field():
    result = scrapers.score("This game is absolutely wonderful and fun!")

    assert "compound" in result
    assert result["compound"] > 0


def test_score_handles_empty_text():
    result = scrapers.score("")

    assert result["compound"] == 0
