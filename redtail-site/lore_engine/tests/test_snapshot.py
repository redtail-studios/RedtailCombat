import base64
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import snapshot


# ---------------------------------------------------------------------------
# list_games / find_game / load_game_text / game_name
# ---------------------------------------------------------------------------

@pytest.fixture
def games_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshot, "GAMES_DIR", str(tmp_path))
    return tmp_path


def test_list_games_finds_supported_extensions_sorted(games_dir):
    (games_dir / "b.md").write_text("b")
    (games_dir / "a.txt").write_text("a")
    (games_dir / "c.pdf").write_bytes(b"%PDF-fake")
    (games_dir / "ignored.json").write_text("{}")

    files = snapshot.list_games()

    names = sorted(os.path.basename(f) for f in files)
    assert names == ["a.txt", "b.md", "c.pdf"]


def test_find_game_returns_explicit_existing_path(games_dir):
    f = games_dir / "mygame.md"
    f.write_text("design doc")

    assert snapshot.find_game(str(f)) == str(f)


def test_find_game_resolves_bare_filename_from_dropdown(games_dir):
    f = games_dir / "mygame.md"
    f.write_text("design doc")

    assert snapshot.find_game("mygame.md") == str(f)


def test_find_game_falls_back_to_first_listed_game(games_dir):
    (games_dir / "onlygame.txt").write_text("design doc")

    assert snapshot.find_game(None) == str(games_dir / "onlygame.txt")


def test_find_game_raises_when_none_available(games_dir):
    with pytest.raises(FileNotFoundError):
        snapshot.find_game(None)


def test_load_game_text_reads_txt_file(tmp_path):
    f = tmp_path / "game.txt"
    f.write_text("  some design text  ", encoding="utf-8")

    assert snapshot.load_game_text(str(f)) == "some design text"


def test_load_game_text_reads_pdf_via_pypdf(tmp_path, monkeypatch):
    f = tmp_path / "game.pdf"
    f.write_bytes(b"%PDF-fake")

    class FakePage:
        def extract_text(self):
            return "page text"

    class FakeReader:
        def __init__(self, path):
            self.pages = [FakePage(), FakePage()]
    monkeypatch.setattr("pypdf.PdfReader", FakeReader)

    assert snapshot.load_game_text(str(f)) == "page text\npage text"


def test_game_name_strips_directory_and_extension():
    assert snapshot.game_name("/some/dir/My Game.md") == "My Game"


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------

def test_parse_json_plain_json():
    assert snapshot._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_strips_json_fence():
    assert snapshot._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_strips_generic_fence():
    assert snapshot._parse_json('```\n{"a": 1}\n```') == {"a": 1}


# ---------------------------------------------------------------------------
# _render_safe
# ---------------------------------------------------------------------------

def test_render_safe_returns_bytes_on_success(monkeypatch):
    monkeypatch.setattr(snapshot, "_render_image", lambda prompt: b"fakebytes")

    img, err = snapshot._render_safe("a prompt")

    assert img == b"fakebytes"
    assert err is None


def test_render_safe_returns_error_tuple_on_exception(monkeypatch):
    def boom(prompt):
        raise ValueError("bad prompt")
    monkeypatch.setattr(snapshot, "_render_image", boom)

    img, err = snapshot._render_safe("a prompt")

    assert img is None
    assert err == "ValueError: bad prompt"


# ---------------------------------------------------------------------------
# _render_image
# ---------------------------------------------------------------------------

def _install_fake_openai(monkeypatch, data_item, captured_kwargs=None):
    class FakeImages:
        def generate(self, **kwargs):
            if captured_kwargs is not None:
                captured_kwargs.update(kwargs)
            return SimpleNamespace(data=[data_item])

    class FakeClient:
        def __init__(self, *a, **k):
            self.images = FakeImages()

    monkeypatch.setattr("openai.OpenAI", FakeClient)


def test_render_image_decodes_b64_json(monkeypatch):
    raw = b"some image bytes"
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_SIZE", "1024x1536")
    _install_fake_openai(monkeypatch, SimpleNamespace(b64_json=base64.b64encode(raw).decode()))

    assert snapshot._render_image("a prompt") == raw


def test_render_image_falls_back_to_url_download(monkeypatch, requests_mock):
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_SIZE", "1024x1536")
    _install_fake_openai(monkeypatch, SimpleNamespace(b64_json=None, url="http://fake.test/img.png"))
    requests_mock.get("http://fake.test/img.png", content=b"downloaded bytes")

    assert snapshot._render_image("a prompt") == b"downloaded bytes"


def test_render_image_dalle_forces_valid_portrait_size(monkeypatch):
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_MODEL", "dall-e-3")
    monkeypatch.setattr(snapshot, "OPENAI_IMAGE_SIZE", "512x512")  # not a valid dall-e-3 size
    captured = {}
    _install_fake_openai(monkeypatch, SimpleNamespace(b64_json=base64.b64encode(b"x").decode()),
                         captured_kwargs=captured)

    snapshot._render_image("a prompt")

    assert captured["size"] == "1024x1792"
    assert captured["response_format"] == "b64_json"


# ---------------------------------------------------------------------------
# generate_snapshot — heavily mocked integration test
# ---------------------------------------------------------------------------

@pytest.fixture
def snapshot_env(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(snapshot, "SNAPSHOTS_DIR", str(tmp_path))
    monkeypatch.setattr(snapshot, "find_game", lambda path=None: "/fake/game.md")
    monkeypatch.setattr(snapshot, "game_name", lambda path: "fake-game")
    monkeypatch.setattr(snapshot, "load_game_text", lambda path: "design doc text")
    monkeypatch.setattr(snapshot, "analyse", lambda year: {})
    monkeypatch.setattr(snapshot.llm, "active_model", lambda: "fake-model")
    # SNAPSHOT_MAX/SNAPSHOT_WORKERS are read via a local `from config import ...`
    # inside generate_snapshot() itself, so the patch target is config's own
    # module attributes, not anything on the snapshot module.
    monkeypatch.setattr(config_module, "SNAPSHOT_MAX", 2)
    monkeypatch.setattr(config_module, "SNAPSHOT_WORKERS", 2)
    return tmp_path


def _brief_json(n):
    return json.dumps({
        "headline": "New direction",
        "modifications": [
            {"finding": f"finding {i}", "change": f"change {i}", "why": f"why {i}",
             "image_prompt": f"prompt {i}"}
            for i in range(n)
        ],
    })


def test_generate_snapshot_happy_path(snapshot_env, monkeypatch):
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: _brief_json(2))
    monkeypatch.setattr(snapshot, "_render_safe",
                        lambda prompt: (f"bytes-for-{prompt}".encode(), None))

    result = snapshot.generate_snapshot(2024)

    assert result["game"] == "fake-game"
    assert result["year"] == 2024
    assert result["headline"] == "New direction"
    assert len(result["modifications"]) == 2
    for i, mod in enumerate(result["modifications"]):
        assert mod["finding"] == f"finding {i}"
        assert "image_b64" in mod
        assert os.path.exists(mod["image_path"])


def test_generate_snapshot_raises_when_no_modifications(snapshot_env, monkeypatch):
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: json.dumps(
        {"headline": "nothing", "modifications": []}))

    with pytest.raises(RuntimeError, match="No modifications"):
        snapshot.generate_snapshot(2024)


def test_generate_snapshot_raises_when_every_image_fails(snapshot_env, monkeypatch):
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: _brief_json(2))
    monkeypatch.setattr(snapshot, "_render_safe",
                        lambda prompt: (None, "RuntimeError: image service down"))

    with pytest.raises(RuntimeError, match="image service down"):
        snapshot.generate_snapshot(2024)


def test_generate_snapshot_with_uploaded_bytes_uses_upload_name(snapshot_env, monkeypatch):
    # The upload path computes `gname` straight from upload_name and never
    # calls find_game()/game_name() at all, unlike the on-disk path.
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: _brief_json(1))
    monkeypatch.setattr(snapshot, "_render_safe", lambda prompt: (b"ok bytes", None))

    result = snapshot.generate_snapshot(
        2024, upload_bytes=b"raw design doc content", upload_name="My Upload.txt")

    assert result["game"] == "My Upload"


def test_generate_snapshot_partial_image_failure_is_tolerated(snapshot_env, monkeypatch):
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: _brief_json(2))

    def flaky_render(prompt):
        if "prompt 0" in prompt:
            return b"ok bytes", None
        return None, "ValueError: failed"
    monkeypatch.setattr(snapshot, "_render_safe", flaky_render)

    result = snapshot.generate_snapshot(2024)

    assert "image_b64" in result["modifications"][0]
    assert result["modifications"][1].get("image_error") == "ValueError: failed"
