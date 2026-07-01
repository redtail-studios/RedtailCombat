"""
snapshot.py — the feedback loop's visual layer.

Takes the market analysis for a year + the game's design doc, asks Claude to
propose concrete, on-brand MODIFICATIONS to the game (what to change after
launch given what players want), and crafts an image prompt for a snapshot of
the MODIFIED game. Then OpenAI renders that snapshot.

  analysis (year)  ->  Claude: modifications + image prompt  ->  OpenAI image
"""
import base64
import glob
import json
import os
from datetime import datetime

import llm
from analysis import analyse
from report import _year_block
from config import (get_year_dir, GAMES_DIR, SNAPSHOTS_DIR,
                    OPENAI_IMAGE_MODEL, OPENAI_IMAGE_SIZE)


# ── Load the game design doc ─────────────────────────────────────────────────
def list_games() -> list:
    files = []
    for ext in ("*.pdf", "*.md", "*.txt"):
        files += glob.glob(os.path.join(GAMES_DIR, ext))
    return sorted(files)


def find_game(path: str | None = None) -> str:
    if path:
        if os.path.exists(path):
            return path
        cand = os.path.join(GAMES_DIR, os.path.basename(path))  # bare filename from dropdown
        if os.path.exists(cand):
            return cand
    files = list_games()
    if not files:
        raise FileNotFoundError(f"No game doc found in {GAMES_DIR} (add a .pdf/.md/.txt)")
    return files[0]


def load_game_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(path)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    else:
        text = open(path, encoding="utf-8", errors="ignore").read()
    return text.strip()


def game_name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


# ── Claude: derive modifications + image prompt ──────────────────────────────
ART_STYLE = (
    "2D hand-drawn rubber-hose cartoon style, thick black ink outlines, flat "
    "muted-earthy colors, exaggerated squash-and-stretch, vintage-1930s-cartoon "
    "energy; cartoon dog luchador characters; portrait phone (9:16) framing"
)


def _brief_prompt(game_text: str, year: int, analysis: dict, n: int) -> str:
    return f"""You are the design intelligence for the mobile game below. This is a POST-LAUNCH feedback loop: real market analysis for {year} surfaced what players want and complain about. Propose concrete, on-brand FEATURE changes, and for EACH one write an image prompt that visualises THAT feature as a concept mockup.

## CURRENT GAME DESIGN
{game_text[:6000]}

## MARKET ANALYSIS — {year} (real scraped player data)
{_year_block(year, analysis)}

## YOUR TASK
Pick the {n} strongest, most relevant findings. For each, propose ONE concrete feature/mode/mechanic/cosmetic change that responds to it, respecting the LOCKED constraints (2D rubber-hose art, portrait phone, ~30s duels, two-thumb controls, fixed camera, player-bottom/rival-top, cosmetic-only — no pay-to-win).

For EACH modification also write an `image_prompt` that is a CONCEPT-DESIGN MOCKUP of THAT ONE FEATURE — not a generic fight scene. Show the new element itself: the new mode's layout, the new UI panel/screen, the new menu card, the new cosmetic, the new HUD element — whatever the feature is. Rules for every image_prompt:
- It must depict THAT specific feature clearly and be visually DIFFERENT from the others.
- Reproduce the art style exactly: {ART_STYLE}.
- It is a visual design mockup: show the feature through layout, characters, icons, and UI shapes — NOT through words. Keep any embedded text to almost none (no big "CRIT"/"PARRY" word-art, no paragraphs); the written explanation lives outside the image.
- 3–5 concrete sentences describing what is on screen.

Output ONLY valid JSON, no markdown fences:
{{
  "headline": "one line summarising the new post-analysis direction",
  "modifications": [
    {{
      "finding": "the player signal/gap (short)",
      "change": "the concrete feature change",
      "why": "why it addresses the finding",
      "image_prompt": "concept-design mockup prompt for THIS feature"
    }}
  ]
}}"""


def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    return json.loads(t.strip())


# ── OpenAI: render the snapshot ──────────────────────────────────────────────
def _render_image(prompt: str) -> bytes:
    from openai import OpenAI
    client = OpenAI()  # reads OPENAI_API_KEY
    size = OPENAI_IMAGE_SIZE
    kwargs = {"model": OPENAI_IMAGE_MODEL, "prompt": prompt, "size": size, "n": 1}
    if "dall-e" in OPENAI_IMAGE_MODEL:
        kwargs["response_format"] = "b64_json"
        if size not in ("1024x1024", "1024x1792", "1792x1024"):
            kwargs["size"] = "1024x1792"  # dall-e-3 portrait
    resp = client.images.generate(**kwargs)
    d = resp.data[0]
    b64 = getattr(d, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    import requests
    return requests.get(d.url).content


# ── Orchestrate ──────────────────────────────────────────────────────────────
def _render_safe(prompt: str):
    try:
        return _render_image(prompt), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def generate_snapshot(year: int, game_path: str | None = None) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from config import SNAPSHOT_MAX, SNAPSHOT_WORKERS

    path = find_game(game_path)
    game_text = load_game_text(path)
    analysis = analyse(get_year_dir(year))

    brief = _parse_json(llm.generate(
        _brief_prompt(game_text, year, analysis, SNAPSHOT_MAX), max_tokens=4000))
    mods = (brief.get("modifications") or [])[:SNAPSHOT_MAX]
    if not mods:
        raise RuntimeError("No modifications returned from the analysis.")

    # Render one image per feature, in parallel.
    prompts = [m.get("image_prompt", "") for m in mods]
    with ThreadPoolExecutor(max_workers=SNAPSHOT_WORKERS) as ex:
        rendered = list(ex.map(_render_safe, prompts))

    if all(img is None for img, _ in rendered):
        raise RuntimeError(next((e for _, e in rendered if e), "image generation failed"))

    os.makedirs(os.path.join(SNAPSHOTS_DIR, str(year)), exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_mods = []
    for i, (m, (img, err)) in enumerate(zip(mods, rendered), 1):
        rec = {"finding": m.get("finding", ""), "change": m.get("change", ""),
               "why": m.get("why", "")}
        if img:
            fp = os.path.join(SNAPSHOTS_DIR, str(year),
                              f"{game_name(path)}_{stamp}_{i}.png")
            with open(fp, "wb") as f:
                f.write(img)
            rec["image_b64"] = base64.b64encode(img).decode()
            rec["image_path"] = fp
        else:
            rec["image_error"] = err
        out_mods.append(rec)

    return {
        "game": game_name(path),
        "year": year,
        "headline": brief.get("headline", ""),
        "modifications": out_mods,
        "model_text": llm.active_model(),
        "model_image": OPENAI_IMAGE_MODEL,
    }


if __name__ == "__main__":
    import sys
    r = generate_snapshot(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
    print("headline:", r["headline"])
    print("saved:", r["image_path"])
