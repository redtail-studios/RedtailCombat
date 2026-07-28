# Expanding Lore from mobile fighting games to all mobile games

This is a research + planning doc, not a changelog — nothing in `lore_engine/`
has been touched yet. It audits exactly where today's scraping pipeline is
locked to the "mobile fighting game" niche, proposes a genre taxonomy and a
config architecture to cover mobile games broadly, and lays out a phased
rollout. Read §1 first if you're unfamiliar with the current setup, then use
the rest as a working plan.

For how the pipeline physically runs (S3/SQS/Lambda, local vs. deployed),
see `SCRAPING_ARCHITECTURE.md` — this doc is about *what* gets scraped, not
*how* scraping executes; nothing proposed here changes that architecture.

**Status: Phases 0-2 and 4 are implemented** (`config.py`'s `GENRES`
registry, all genre-scoped scrapers, the new `appcharts.py`, and
`analysis.py`'s optional genre filter) for a 4-genre pilot — Puzzle, Gacha /
Collection RPG, Idle / Incremental, Hybrid-Casual — alongside the original
Fighting scope. Control which genres run with `LORE_GENRES` (comma-separated
keys from `config.GENRES`; defaults to all of them). Phase 3 (the remaining
~8 genres from §2) and region expansion (§7) are still open. Two things in
the original draft below turned out to need correction once actually
implemented — see the "Correction" notes in §4.

## 1. Current state: how niche-locked is it, really?

The good news first: **the scraper code itself is already genre-agnostic.**
Every one of the 14 scrapers in `lore_engine/scrapers/` takes its queries,
app IDs, subreddit names, etc. from `config.py` constants and loops over
whatever it's given — there is no `if "fighting" in text` logic anywhere in
scraper bodies. The niche lock lives entirely in **data**, not code. That
matters a lot for scoping this: expansion is mostly a config/curation
project, not a rewrite.

Per platform, current state:

| Scraper | Config knobs | Fighting-specific today? |
|---|---|---|
| `reddit.py` | `SUBREDDITS` (config.py:94-104), `REDDIT_KEYWORDS` (config.py:109-114) | Yes — half the subreddit list is fighting-game subs (`FightingGames`, `Tekken`, `StreetFighter`, `MortalKombat`, `SmashBros`, `Brawlhalla`, `ClashRoyale`); keyword filter for broad subs includes `"fighting game"` |
| `steam.py` | `STEAM_GENRE_TAG="Fighting"` (config.py:119), `STEAM_APP_IDS` (config.py:120, hardcoded to Brawlhalla/SF6/Rainbow Six) | Yes, entirely |
| `googleplay.py` | `GOOGLE_PLAY_QUERY="mobile fighting game pvp"` (config.py:124) | Yes — single free-text search, 5 apps total |
| `appstore.py` | `APP_STORE_APPS` (config.py:129-133, 3 named apps) | Yes, entirely — no search API exists for iTunes RSS, so this is hand-curated by design |
| `hackernews.py` | `HN_QUERIES` (config.py:137) | Partial — `"fighting game"` alongside generic `"mobile game"`, `"free to play"` |
| `googletrends.py` | `TREND_TERMS` (config.py:176-179) | Partial — already mixes `gacha game`, `battle royale`, `auto battler`, `idle game`, `roguelike`, `hero shooter` with `mobile fighting game`/`fighting game`. This one's already halfway generalized. |
| `wikipedia.py` | `WIKI_ARTICLES` (config.py:182-186) | Partial — `Street_Fighter_6`, `Tekken_8`, `Mortal_Kombat_1` alongside generic `Mobile_game`, `Free-to-play`, `Esports` |
| `youtube.py` | `YT_QUERIES` (config.py:197) | Yes — `"mobile fighting game"`, `"best mobile pvp game"` vs. one generic `"gacha game review"` |
| `gamenews.py` | `GAMENEWS_FEEDS` (config.py:142-157) | **No** — broad outlet RSS, no genre filter. Already generic. |
| `github.py` | `GITHUB_QUERIES` (config.py:164) | **No** — `topic:game`, `topic:gamedev`, `topic:game-engine`, `mobile game`. Already generic. |
| `itch.py` | `ITCH_FEED` (config.py:168) | **No** — itch.io's featured feed, unfiltered. Already generic. |
| `rawg.py` | `RAWG_API_KEY`/`RAWG_PAGE_SIZE` (config.py:172-173) | **No**, but leaves a real capability on the table — RAWG's API supports a `genres=` filter and this scraper doesn't use it (§4). |
| `steamtrending.py` / `steamcharts.py` | `STEAM_TRENDING_N` / `STEAM_CHARTS_PER_LIST` | **No** — whole-store top charts, no genre param. Already generic. |
| `twitch.py` | `TWITCH_TOP_GAMES` | **No** — Twitch's `top games by viewers` endpoint has no genre filter to begin with. Already generic. |

Cross-cutting config (not tied to one scraper):

- **`SIGNAL_KEYWORDS`** (config.py:208-215) — actually already genre-neutral
  in spirit: short-session preference, ad sentiment, PvP demand, progression,
  co-op, cosmetic monetization. These axes apply to almost any mobile game
  genre as-is. Low priority to change.
- **`COMPETITORS`** (config.py:218-225) — 100% fighting titles (Brawlhalla,
  Shadow Fight, Street Fighter, Mortal Kombat, Injustice, Clash Royale). This
  needs to grow per-genre.
- **Orphaned config**: `APPCHARTS_COUNTRY`/`APPCHARTS_LIMIT` (config.py:189-190)
  exist but **no scraper module uses them** — looks like a planned Apple
  top-charts scraper that was never built. This is a good first target
  because it can be genre-parameterized from day one (§4).

**Bottom line:** roughly half the platforms need real data work (subreddits,
app IDs, queries, competitor lists); the other half already run genre-blind
and need nothing. `analysis.py` and `report.py` need almost no change — see
§6.

## 2. Target genre taxonomy

Industry classification for mobile games in 2026 has largely converged on
three top-level archetypes — **Hyper-casual**, **Hybrid-casual**, and
**Midcore** — with genre as the finer-grained axis underneath (source:
AppsFlyer's game-classification writeup, AppFollow's 2026 genre report,
data.ai/Sensor Tower's own category tree). Hybrid-casual in particular is
called out as the fastest-growing segment (~$4.2B revenue in 2025), so it's
worth tracking as its own bucket rather than folding it into casual.

Recommended genre list to track (keeps "Fighting / Competitive PvP" as one
entry among many, not replaced):

| Genre bucket | Example flagship titles | Notes |
|---|---|---|
| Fighting / Competitive PvP | Brawlhalla, Shadow Fight, Mortal Kombat | current scope — keep as-is |
| Battle Royale / Shooter | COD Mobile, PUBG Mobile, Free Fire | |
| Gacha / Collection RPG | Genshin Impact, Fate/GO, Raid: Shadow Legends | huge in JP/KR — see §7 region note |
| Idle / Incremental | AFK Arena, Cookie Clicker mobile, idle RPGs | r/incremental_games is an active, on-topic subreddit |
| Puzzle | Candy Crush, Royal Match, Merge games | App Store's single largest genre by app count in 2026 per AppFollow |
| Simulation | Township, Design Home, life-sim/tycoon games | |
| Strategy (4X / tower defense / base-building) | Clash of Clans, Rise of Kingdoms | |
| Card & Board | Hearthstone mobile, Solitaire variants | |
| Casino / Social Casino | Slotomania, DoubleDown Casino | ad/monetization signal especially relevant here |
| Sports & Racing | 8 Ball Pool, Asphalt, sports-management sims | |
| Hyper-casual / Hybrid-casual | Voodoo/Homa-published titles | short session length, ad-driven — ties directly into existing `SIGNAL_KEYWORDS` |
| Trivia & Word | Wordscapes, trivia games | |
| Adventure | Data.ai/AppFollow flag this as the single largest App Store Top-200 category by volume in 2026 | |

This is a starting list, not gospel — treat it as the seed for
`config.GENRES` (§3) and expect to prune/merge buckets once real data volume
per genre is visible.

## 3. Architecture: from single-niche constants to a genre registry

The central decision this plan makes: **don't multiply the (year, platform)
key into (year, platform, genre).** `worker.py` and `storage.py` key
everything strictly by `(year, platform)` — SQS message bodies are
`{"year": ..., "platform": ...}` (worker.py:_process_one), S3 objects are
`<prefix>/data/<year>/<platform>.json`. Adding genre as a third storage/queue
dimension would ripple through `storage.py`, `worker.py`, `manifest.py`, and
the scrape-status polling endpoints — a much bigger, riskier change than the
goal here actually requires.

Instead: **tag records with a `"genre"` field and keep one file per
platform per year, covering every active genre's data.** Every scraper
already returns a list of free-form dicts (`{"source": ..., "text": ...,
"sentiment": ...}` etc.) — adding one more key (`"genre": "puzzle"`) is a
non-breaking, additive change that `analysis.py` can choose to read or
ignore. No storage/queue schema changes needed at all.

Concretely, replace today's single-purpose constants with a registry:

```python
# config.py — replaces the single-niche constants (STEAM_GENRE_TAG,
# GOOGLE_PLAY_QUERY, APP_STORE_APPS, etc.) with a per-genre lookup.
GENRES = {
    "fighting": {
        "label": "Fighting / Competitive PvP",
        "subreddits": ["FightingGames", "Fighters", "StreetFighter", "Tekken",
                       "MortalKombat", "SmashBros", "Brawlhalla"],
        "steam_tag": "Fighting",
        "steam_app_ids": ["1716740", "2358720", "359550"],
        "google_play_query": "mobile fighting game pvp",
        "app_store_apps": [{"name": "brawlhalla", "app_id": "1344199847"}, ...],
        "hn_query": "fighting game",
        "trend_term": "fighting game",
        "wiki_articles": ["Street_Fighter_6", "Tekken_8", "Mortal_Kombat_1"],
        "yt_query": "mobile fighting game",
        "competitors": {"Brawlhalla": ["brawlhalla"], ...},
        "signal_keywords_extra": {},  # genre-specific additions on top of the shared baseline
    },
    "puzzle": { ... },
    "gacha":   { ... },
    # ...
}
ACTIVE_GENRES = os.getenv("LORE_GENRES", "fighting").split(",")  # comma-separated; "all" = every key
```

Each scraper that's currently niche-locked (`googleplay`, `appstore`,
`steam`, `hackernews`, `youtube`, `googletrends`, `wikipedia`) changes from
"read one constant" to "loop over `GENRES[g]` for `g` in `ACTIVE_GENRES`,
tag each record with `genre=g`." The scrapers that are already generic
(`gamenews`, `github`, `itch`, `rawg`, `steamtrending`, `steamcharts`,
`twitch`) don't need a genre loop at all — they stay whole-market signals,
which is correct (news and trending charts shouldn't be genre-filtered).

`SIGNAL_KEYWORDS` and `COMPETITORS` become: a shared baseline (today's dict,
since those axes are genre-neutral) plus each genre's `signal_keywords_extra`
/ `competitors` merged in at runtime. `analysis.py`'s `competitors()`
(analysis.py:131-156) already sorts by mention count and truncates to the
top 6 — a much bigger merged `COMPETITORS` dict costs nothing there, no
schema change required.

## 4. Two real code-level upgrades worth doing alongside the config work

These aren't just "add more niches" — they're capability gaps found while
auditing the current scrapers. **Both were implemented and verified live**
(see §8/implementation) — one exactly as originally scoped, one corrected
after the original assumption turned out to be wrong:

1. **Build the orphaned `appcharts.py` scraper**, genre-parameterized from
   day one. *Correction from the original draft of this doc*: Apple's newer
   RSS Feed Generator (`rss.marketingtools.apple.com`) turned out to have
   **dropped genre-level filtering** — it only serves whole-store top
   charts, confirmed by a live 404 on every genre-scoped path tried. The
   older, still-live `itunes.apple.com/{cc}/rss/top{free,grossing}applications/limit={n}/genre={id}/json`
   endpoint does support a genre ID and was verified against real
   data — `genre=7012` (Puzzle) returns Royal Match / Candy Crush Saga,
   `genre=7014` (Role Playing) returns Pokémon GO / Dragon Ball Legends. This
   is the endpoint `appcharts.py` actually uses; same "no key" constraint,
   just the older API family (the same one `appstore.py` already uses for
   reviews) instead of the newer one.
2. **`rawg.py` ignores RAWG's `genres=` query param.** Trivial addition —
   pass `genres` from the active genre's RAWG genre slug (RAWG's own genre
   taxonomy is close enough to §2's list to map directly) instead of pulling
   the whole database's top-by-popularity every run. Implemented as scoped.

   *Dropped from the original draft*: a proposed `googleplay.py` upgrade to
   category-based `list()` browsing (Google Play's JS scraper library
   supports category/collection constants for real top-charts). The actual
   installed dependency (`google-play-scraper` 1.2.7, the Python port) only
   exposes `search`/`app`/`reviews`/`permissions` — no `list()` — so that
   upgrade doesn't exist for this stack. `googleplay.py` still uses
   `search()`, now looped per genre query instead of one hardcoded query.

## 5. New data sources considered and rejected/deferred

Researched during this pass (market-intelligence tooling, since "expand to
all mobile games" raises the question of whether the existing free/no-key
sources still scale):

- **FreeGameRank / gamerank.net** — free daily iOS/Android rankings (JP/KR/
  TW/SEA + revenue estimates), no login, no paywall. Worth a future look for
  regional top-charts coverage, but it's outside "no key, official-ish
  endpoint" territory (scraping a third party's own aggregated-and-modeled
  numbers, not a primary source) — defer until core genre coverage lands.
- **AppMagic, AppFollow, Sensor Tower, data.ai, Apptopia** — all paid
  intelligence platforms. Their public blog posts are useful **research
  reading** (this doc cites two of them) but their actual ranking/revenue
  data sits behind paywalls or ToS-restricted UIs — do not scrape these; it
  would break the "no key, public/official API" philosophy every existing
  scraper follows and risks ToS violations for data we can't compare
  against reliable ground truth anyway.
- **GameAnalytics** — requires the *target game's own* SDK to be integrated
  by its developer. Not usable for external market intelligence on
  competitors' games (we don't own them) — not applicable here regardless
  of genre scope.

Conclusion: no new *sources* are needed beyond the two in §4 (Apple charts,
RAWG genre filter) — the existing 14 official/public APIs already cover the
signal types (reviews, charts, trends, news, social discussion, dev
activity) generically across genres; the gap is data curation, not source
coverage.

## 6. `analysis.py` / `report.py` impact

Both are already close to genre-neutral:

- `analysis.py`'s `load_items()`, `signal_scores()`, `scorecard()`,
  `competitors()`, `top_quotes()` all operate on the flat `items`/`records`
  list — none of them assume fighting-game content. The only change needed:
  optionally accept a `genre` filter param (`analyse(year, genre=None)`) that
  filters `_iter_records`'s output on the new `"genre"` field before
  aggregating; `genre=None` preserves today's cross-genre-aggregate
  behavior exactly, so this is backward-compatible by construction.
- `report.py`'s LLM prompt (report.py:103) is already written generically
  ("a senior market-intelligence analyst... find genuine GAPS in the
  market") — it doesn't mention fighting games anywhere. No prompt rewrite
  needed; at most, add a line letting the prompt know which genre(s) the
  data below covers, so Claude doesn't have to infer it from quotes.

## 7. Open questions (need a decision before Phase 1 starts)

- **Which genres to prioritize first?** Doing all ~12 buckets in §2 at once
  multiplies every genre-scoped scraper's request count and runtime
  proportionally — `SCRAPING_ARCHITECTURE.md` already flags Reddit and
  GitHub as rate-limit-fragile at *current*, single-genre volume. Recommend
  picking 3-4 genres for a pilot (suggest: Puzzle, Gacha, Idle, Hybrid-casual
  — largest/fastest-growing per §2's sources) before scaling to all of them.
- **Region scope.** Everything today is US-only (`country="us"` in
  `googleplay.py`/`appstore.py`, `APPCHARTS_COUNTRY="us"`). Gacha and idle
  genres in particular are disproportionately JP/KR/CN-driven — going
  multi-region is a *separate*, larger expansion than "all genres, still
  US" and should be scoped as its own follow-up, not bundled in here.
- **Do RAWG/YouTube/Twitch API keys get provisioned?** They currently skip
  cleanly when unset (`rawg.py`:16-18, `youtube.py`:797-799, `twitch.py`:704-706).
  Broad genre coverage benefits most from RAWG (real genre metadata) and
  YouTube (genre-specific search), so it's worth asking whether getting
  those free keys is in scope for this expansion or a later step.
- **Per-genre reports vs. one cross-genre report.** `report.py` currently
  generates one report per year. Once multiple genres are tracked, is the
  desired output "one report per genre" or "one report comparing genres"?
  This changes how `report.py:generate()` should be parameterized.

## 8. Phased rollout

1. **Phase 0 — tagging, no behavior change.** Add a `"genre"` field
   (default `"fighting"`) to every scraper's output records. Confirm
   `analysis.py`/`report.py` tolerate the extra key (they will — both read
   specific keys, not whole-dict schemas). Zero risk, ships independently.
2. **Phase 1 — config registry + pilot genres.** Build `GENRES` in
   config.py (§3), migrate today's fighting config into `GENRES["fighting"]`,
   fully populate 3-4 pilot genres (§7's open question). Update the 7
   niche-locked scrapers to loop over `ACTIVE_GENRES`.
3. **Phase 2 — platform-native genre filtering.** Ship the two upgrades in
   §4 (Google Play category `list()`, new `appcharts.py`, RAWG `genres=`
   param) — these make Phase 1's pilot genres' data meaningfully better,
   not just broader.
4. **Phase 3 — full genre coverage.** Fill in the remaining genres from §2,
   expand `COMPETITORS`/`SIGNAL_KEYWORDS` extras per genre, expand
   `SUBREDDITS`/`WIKI_ARTICLES`/`TREND_TERMS`/`YT_QUERIES` accordingly.
   Verify candidate subreddits are actually active before adding them (a
   dead/quarantined sub silently wastes a scrape cycle the way `reddit.py`
   already handles blocked feeds).
5. **Phase 4 — analysis/report layer.** Add the optional `genre` filter to
   `analyse()` (§6); resolve the "per-genre vs. cross-genre report" question
   from §7 and update `report.py:generate()`'s signature accordingly.
6. **Phase 5 — rate-limit/cost validation.** After Phase 1's pilot genres
   are live, time a full scrape cycle and compare against today's baseline
   before committing to Phase 3's full genre list — GitHub's ~10/min
   unauthenticated search limit and Reddit's known AWS-IP throttling
   (`SCRAPING_ARCHITECTURE.md` §5) get strictly worse as query lists grow,
   not better.

## Sources consulted

- [It's time for new mobile gaming categories & genres — AppsFlyer](https://www.appsflyer.com/blog/uncategorized/game-classification-app-stores/)
- [Most Popular Mobile Game Genres 2026: Top 200 Data — AppFollow](https://appfollow.io/blog/popular-mobile-game-genres-2026)
- [Mobile Gaming Market in 2026: Trends and Outlook — ASO Mobile](https://asomobile.net/en/blog/mobile-gaming-market-in-2026-trends-and-outlook/)
- [Mobile Game Genre Breakdown 2026 — game-developers.org](https://www.game-developers.org/mobile-game-genre-breakdown-2026)
- [FreeGameRank — free mobile game rankings](https://gamerank.net/en)
- [List of Best Sensor Tower Alternatives & Competitors 2026 — TrustRadius](https://www.trustradius.com/products/sensor-tower/competitors)
- [Data Solutions for Mobile Developers — GameAnalytics](https://www.gameanalytics.com/use-cases/mobile)
