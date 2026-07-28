# Lore — intern tasks: evidence grounding + source dedup

Two tasks, in this order. Everything below is against the **production** engine at
`redtail-site/lore_engine/` — this is what's actually deployed, not a copy. Do your
work here, not in the separate `amritha_project/video_game/ai_engine/` repo — that's
an earlier, now-diverged version of the same idea and changes there won't affect the
live site.

No tests exist anywhere in `lore_engine/` yet. Add a `lore_engine/tests/` folder with
pytest (`pip install pytest`, add it to whatever requirements file this project uses).
Run with `pytest lore_engine/tests` from the repo root.

**You do not need AWS/S3 access for either task.** `config.DEPLOYED` is only `True`
when the `VERCEL` env var is set (i.e. actually running on Vercel). Locally it's
`False`, so `analysis.py` reads from local JSON files in `redtail-site/lore_data/<year>/`
exactly the same way it would read from S3 in production — the storage backend is
swapped out underneath `_iter_records()`, but the data shape coming out of it is
identical either way. Develop and test entirely against `lore_data/`.

## Background: how the pipeline works today

1. Scrapers (in `scrapers/`) write per-platform records, tagged with a `genre` field
   (or no tag / `"general"` for whole-market sources like news, GitHub, Steam charts).
2. `analysis.py::_iter_records(year, genre)` reads those records — from S3 if
   `DEPLOYED`, otherwise from `lore_data/<year>/<platform>_data.json`. A record with
   no genre tag, or tagged `"general"`, is **included for every genre** you ask for —
   that's intentional (a rising Wikipedia/news trend is a real signal for every
   genre), not a bug. Keep that in mind for Task 1.
3. `analysis.py::analyse(year, genre)` turns those records into `signal_scores()`,
   `scorecard()`, `competitors()`, and `top_quotes()` — cheap, non-LLM aggregation.
4. `report.py::generate()` has two paths:
   - `genre=<key>`: one genre, one prompt (`build_prompt`).
   - `genre=None` (the default): calls `analyse(y, g)` **once per active genre**
     (`ACTIVE_GENRES` in config) per year, then `build_prompt_multi` renders each
     genre as its own labeled section and asks Claude to compare across them.
   - There's also `generate_game_report()` / `build_game_prompt()` — a studio uploads
     a design doc and gets it scored against the (ungenred, pooled) market data.
5. Whichever prompt gets built, `llm.generate_html()` sends it to Claude, which
   free-writes the whole HTML report — including which "gaps" are real and what
   quotes back them up, with nothing checking that those quotes are genuine.

---

## Task 1: Dedup — two distinct problems, both real in production

### 1a. Near-duplicate items inflate signal scores (same problem, any pipeline)
The same real-world story often gets picked up by more than one scraper — a gaming-
news RSS item reposted to Reddit, a Hacker News thread linking the same article, a
Steam review quoted verbatim in a comment. `load_items()` (`analysis.py:43-62`) treats
every one of those as an independent data point, so `signal_scores()` and
`competitors()` (`analysis.py:101-161`) silently overcount whatever topic happened to
get syndicated the most. `top_quotes()` (`analysis.py:65-97`) already dedups, but only
by **exact string match** (the `seen` set at line 90) — a reworded or truncated
repost slips through.

**Build:** a `dedupe_items(items: list) -> list` function in `analysis.py`.
- Normalize text (lowercase, strip punctuation, collapse whitespace).
- Use stdlib `difflib.SequenceMatcher` (no new dependency — `analysis.py`'s docstring
  is explicit about staying dependency-light so it keeps running on Vercel) to compare
  each item against a rolling window of the last ~50 seen items. Treat a similarity
  ratio above **0.85** as a duplicate — a starting point, tune once you see real data.
  Compare against a window, not the full list pairwise, or this gets slow once
  `lore_data/` has thousands of items — leave a one-line comment explaining that
  trade-off, it won't be obvious later.
- On a duplicate, keep the first occurrence but merge the second's `source` into a
  `sources: [...]` list on the kept item rather than dropping it — a later task
  (source credibility weighting, not yours yet) will want to know an item was
  corroborated by three sources vs one.
- Call it from `load_items()` before it returns (line 62), and again inside
  `top_quotes()` before the exact-match dedup (line 90) so near-duplicate quotes
  don't both make the top-25 list.

### 1b. The SAME quote repeats across genre sections in one report
This one is specific to the multi-genre path and is worth actually generating a
report locally to see — it's a visible, embarrassing bug, not a theoretical one.
Because general/untagged records count toward *every* genre (`analysis.py:38`,
by design — see Background #2), when `generate()`'s multi-genre branch calls
`analyse(y, "fighting")`, `analyse(y, "puzzle")`, `analyse(y, "rpg")`, etc.
separately (`report.py:220`), a general-tagged item (e.g. one Wikipedia trend
spike, one big news story) can land in `top_quotes()` for *all of them*. The
reader ends up seeing the identical quote under the Fighting section, then again
under Puzzle, then again under RPG.

This is different from 1a: the item legitimately contributes to each genre's numeric
signal score (that's correct — a rising trend really is a signal for every genre), so
don't dedup it out of `signal_scores`/`scorecard`. The problem is purely that the
*quote list* looks redundant across sections in the same document.

**Build:** in `report.py::build_prompt_multi` / `_year_block_multi` (lines 72-74,
151-176), track which quote texts have already been shown for a given year across
earlier genre sections, and skip re-displaying them in later ones — pass a `seen`
set through `_year_block_multi` → `_genre_block` → `_fmt_quotes` for that purpose.
Don't touch `analyse()`'s numeric outputs — only the quote-list rendering.

### Tests (`lore_engine/tests/test_analysis.py`, `test_report.py`)
- `dedupe_items()`: identical text/different source → merges to one with a
  `sources` list; ~90%-similar reworded text → dedupes; genuinely different text on
  the same topic → both kept.
- Feed a fixture with a known duplicate pair through `signal_scores()`/`competitors()`
  and assert the count is 1, not 2.
- A fixture where the same general-tagged quote appears in two genres' `analyse()`
  output → assert `build_prompt_multi`'s rendered text contains it only once.

### Definition of done
- `dedupe_items()` exists, called from `load_items()` and `top_quotes()`.
- Cross-genre quote repetition fixed in `build_prompt_multi`'s rendering.
- Tests pass.
- Sanity check on real data: run `report.generate(backtest_years=[2025])` (multi-genre,
  default) against real `lore_data/`, before and after your change — confirm
  `total_items` drops in `analyse()` output, and manually check the assembled prompt
  text no longer repeats the same quote verbatim across genre sections.

---

## Task 2: Evidence grounding — force claims to cite real quotes

### Why this matters
The prompt already tells Claude to "cite exact numbers, use real quotes, no
platitudes" (e.g. `report.py:144`), but nothing enforces it — the model can assert a
"gap" that isn't backed by anything in the data, and there's no way to tell from the
output whether a cited quote is real or invented. For a report a studio makes real
product/spend decisions from, that's the actual risk.

Production has **three** places that build a prompt from quotes — `build_prompt`
(single genre / backtest), `build_prompt_multi` (cross-genre), and `build_game_prompt`
(uploaded game vs market) — all three route through `_fmt_quotes()`
(`report.py:36-39`). Design this so all three get grounding, not just one; that's the
main way this task goes wrong.

### What to build

**1. Assign quote IDs at render time, not inside `analysis.py`.**
`analyse()` is called independently per year and per genre (see Background), so it
has no way to know about IDs used elsewhere in the same report. Keep `top_quotes()`
returning plain text — instead, thread an ID counter and a registry through the
formatting functions:

```python
def _fmt_quotes(quotes: list, ids: Iterator[int], registry: dict) -> str:
    if not quotes:
        return "  (no quotes)"
    lines = []
    for q in quotes[:20]:
        qid = f"Q{next(ids)}"
        registry[qid] = q
        lines.append(f'  - [{qid}] "{q}"')
    return "\n".join(lines)
```

Thread `ids` (an `itertools.count(1)`) and `registry` (a plain `dict`) through
`_year_block`, `_genre_block`, `_year_block_multi` — created once per `build_prompt*`
call, so IDs stay unique across the whole prompt (including across genre sections,
which also fixes any risk of Task 1b's fix producing ID collisions).

**2. Return the registry alongside the prompt string.**
Change `build_prompt`, `build_prompt_multi`, and `build_game_prompt` to return
`(prompt: str, registry: dict)` instead of just a string. Update their three call
sites in `generate()` (lines 218, 222) and `generate_game_report()` (line 263)
accordingly.

**3. Require citations in the prompt text itself.**
In the "Market Gap Analysis" instructions (`report.py:137`, and the per-genre
equivalent at line 191, and `build_game_prompt`'s "Exposed Gaps"/"Market Fit" at
lines 246-247), add: *"Every gap you name must include at least one quote ID in
brackets, e.g. [Q7], pulled from the quotes list above. Do not invent quotes or IDs —
if you don't have a real quote for a gap, say so instead of fabricating one."*

**4. Validate the HTML Claude returns.**
Add `validate_citations(html: str, registry: dict) -> dict` to `report.py`:
- Regex-extract every `[Q\d+]`-style tag from the HTML.
- Flag any cited ID not present in `registry` (a hallucinated citation).
- Flag gap sections with zero citations — a reasonable first cut is checking each
  gap heading block (e.g. each `<h3>` under the Market Gap Analysis section) contains
  at least one `[Q\d+]` tag. Don't over-engineer real HTML parsing here; `re` plus a
  loose heuristic is fine.
- Return `{"valid": bool, "hallucinated_ids": [...], "uncited_gaps": [...]}`.

**5. Wire it in and log, don't silently swallow.**
Call `validate_citations()` after `llm.generate_html()` returns, in all of
`generate()` and `generate_game_report()`. Log a clear warning with whatever
logging/print pattern this file already uses when validation fails, including which
IDs were hallucinated or which gaps lack citations. Whether to hard-fail the run is a
judgment call — default to logging loudly, ask before making it block report
generation in prod (that could break a live customer-facing flow).

### Tests (`lore_engine/tests/test_report.py`)
- `_fmt_quotes()` assigns sequential IDs and populates the registry correctly, given
  a shared counter across two calls (simulating two genre sections in one report).
- `validate_citations()` against fixture HTML with: a valid citation, a citation to
  an ID absent from the registry, and a gap section with no citation — each case
  caught correctly.

### Definition of done
- Quotes carry stable, globally-unique IDs across all three prompt-building paths.
- Prompts explicitly require citations per named gap in all three paths.
- `validate_citations()` exists, is called in both `generate()` and
  `generate_game_report()`, and results are logged.
- Tests pass.
- Generate one real report against `lore_data/` (try both single-genre and the
  default multi-genre path) and manually confirm: cited quote IDs match real quotes,
  and every named gap has at least one.

---

## Notes for whoever reviews this
- Neither task touches `storage.py`/`worker.py`/S3 — everything here is local to
  `analysis.py` and `report.py`, testable entirely against `lore_data/`.
- These two are prerequisites for a later idea (weighting sources by credibility) —
  don't build that yet, it needs outcome data we don't have. The `sources: [...]`
  list added in Task 1a is deliberately there to make that easier later, but the
  weighting logic itself is a separate, bigger conversation.
