"""
llm.py — single place that talks to the LLM.

Default provider is Claude (Anthropic). The report is large, so we stream and
collect the final message (the SDK requires streaming for big max_tokens to
avoid HTTP timeouts).

Switch provider/model with env vars:
  LLM_PROVIDER = anthropic | openai     (default anthropic)
  ANTHROPIC_MODEL = claude-opus-4-8     (default)
  OPENAI_MODEL    = gpt-4o              (default, only if provider=openai)
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER        = os.getenv("LLM_PROVIDER", "anthropic").lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o")


def _via_anthropic(prompt: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    # Stream so a long report doesn't hit the SDK's non-streaming timeout guard.
    # Note: Opus 4.8 rejects temperature/top_p/top_k — do not pass them.
    with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    return "".join(b.text for b in message.content if b.type == "text")


def _via_openai(prompt: str, max_tokens: int) -> str:
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY from env
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def generate(prompt: str, max_tokens: int = 32000) -> str:
    """Generate text from the configured provider."""
    if PROVIDER == "openai":
        return _via_openai(prompt, max_tokens)
    return _via_anthropic(prompt, max_tokens)


def active_model() -> str:
    return OPENAI_MODEL if PROVIDER == "openai" else ANTHROPIC_MODEL


def _strip_fence(html: str) -> str:
    """Remove ```html fences if the model wrapped the output."""
    html = html.strip()
    if html.startswith("```html"):
        html = html[7:]
    elif html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    return html.strip()


def generate_html(prompt: str, max_tokens: int = 32000) -> str:
    """Generate and clean an HTML document."""
    return _strip_fence(generate(prompt, max_tokens=max_tokens))