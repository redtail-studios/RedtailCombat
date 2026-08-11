import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def test_get_year_dir_creates_and_returns_year_subdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IS_LAMBDA", False)
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))

    path = config.get_year_dir(2024)

    assert path == str(tmp_path / "2024")
    assert os.path.isdir(path)


def test_get_year_dir_no_year_returns_base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IS_LAMBDA", False)
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path / "base"))

    path = config.get_year_dir(None)

    assert path == str(tmp_path / "base")
    assert os.path.isdir(path)


def test_get_year_dir_lambda_redirects_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "IS_LAMBDA", True)
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    path = config.get_year_dir(2024)

    assert path == str(tmp_path / "lore_scratch" / "2024")
    assert os.path.isdir(path)
