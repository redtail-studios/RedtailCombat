import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import llm


# ---------------------------------------------------------------------------
# _strip_fence
# ---------------------------------------------------------------------------

def test_strip_fence_removes_html_fence():
    assert llm._strip_fence("```html\n<div>hi</div>\n```") == "<div>hi</div>"


def test_strip_fence_removes_plain_fence():
    assert llm._strip_fence("```\nsome text\n```") == "some text"


def test_strip_fence_leaves_unfenced_text_unchanged():
    assert llm._strip_fence("plain text, no fence") == "plain text, no fence"


def test_strip_fence_language_tag_leaks_when_not_html():
    # Only the literal "```html" prefix is special-cased; any other language
    # tag (e.g. "```python") falls into the generic elif branch, which only
    # strips the three backticks — the language word itself leaks into the
    # result (llm.py:64-65).
    result = llm._strip_fence("```python\nprint('hi')\n```")
    assert result == "python\nprint('hi')"


# ---------------------------------------------------------------------------
# generate() / active_model() dispatch
# ---------------------------------------------------------------------------

def test_generate_dispatches_to_anthropic_by_default(monkeypatch):
    monkeypatch.setattr(llm, "PROVIDER", "anthropic")
    monkeypatch.setattr(llm, "_via_anthropic", lambda prompt, max_tokens: "anthropic result")
    monkeypatch.setattr(llm, "_via_openai", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("should not be called")))

    assert llm.generate("hi") == "anthropic result"


def test_generate_dispatches_to_openai_when_configured(monkeypatch):
    monkeypatch.setattr(llm, "PROVIDER", "openai")
    monkeypatch.setattr(llm, "_via_openai", lambda prompt, max_tokens: "openai result")
    monkeypatch.setattr(llm, "_via_anthropic", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("should not be called")))

    assert llm.generate("hi") == "openai result"


def test_active_model_returns_correct_model_per_provider(monkeypatch):
    monkeypatch.setattr(llm, "PROVIDER", "openai")
    monkeypatch.setattr(llm, "OPENAI_MODEL", "gpt-4o")
    assert llm.active_model() == "gpt-4o"

    monkeypatch.setattr(llm, "PROVIDER", "anthropic")
    monkeypatch.setattr(llm, "ANTHROPIC_MODEL", "claude-opus-4-8")
    assert llm.active_model() == "claude-opus-4-8"


def test_generate_html_strips_fence_from_generate_output(monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, max_tokens=32000: "```html\n<p>hi</p>\n```")

    assert llm.generate_html("prompt") == "<p>hi</p>"


# ---------------------------------------------------------------------------
# _via_anthropic / _via_openai — fake the lazily-imported SDK clients
# ---------------------------------------------------------------------------

def _install_fake_anthropic(monkeypatch, blocks):
    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_final_message(self):
            return SimpleNamespace(content=blocks)

    class FakeMessages:
        def stream(self, **kwargs):
            return FakeStream()

    class FakeClient:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

    monkeypatch.setattr("anthropic.Anthropic", FakeClient)


def _install_fake_openai(monkeypatch, content):
    class FakeCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self, *a, **k):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeClient)


def test_via_anthropic_joins_text_blocks_only(monkeypatch):
    blocks = [
        SimpleNamespace(type="text", text="Hello "),
        SimpleNamespace(type="thinking", text="ignored internal reasoning"),
        SimpleNamespace(type="text", text="world."),
    ]
    _install_fake_anthropic(monkeypatch, blocks)

    assert llm._via_anthropic("prompt", 100) == "Hello world."


def test_via_openai_returns_message_content(monkeypatch):
    _install_fake_openai(monkeypatch, "the response text")

    assert llm._via_openai("prompt", 100) == "the response text"


def test_via_openai_returns_empty_string_when_content_is_none(monkeypatch):
    _install_fake_openai(monkeypatch, None)

    assert llm._via_openai("prompt", 100) == ""
