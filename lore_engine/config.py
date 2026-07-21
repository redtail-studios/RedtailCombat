"""
config.py — central configuration for the AI market-intelligence engine.

Edit the RESEARCH section to change what you analyse. Everything downstream
(scrapers, analysis, report) reads from here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

DEPLOYED = bool(os.getenv("VERCEL"))
IS_LAMBDA = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))  # auto-set by the Lambda runtime

# ── Paths (Lore lives inside the redtail-site) ──────────────────────────────
HERE     = os.path.dirname(os.path.abspath(__file__))
BASE     = os.path.dirname(HERE)                        # redtail-site/
DATA_DIR = os.path.join(BASE, "lore_data")             # committed scrape snapshot
GAMES_DIR     = os.path.join(BASE, "lore_games")       # (uploads used instead)
SNAPSHOTS_DIR = os.path.join(os.getenv("TMPDIR", "/tmp"), "lore_snapshots")  # writable on Vercel

# ── Snapshot generation (OpenAI images) ──────────────────────────────────────
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")  # or dall-e-3
OPENAI_IMAGE_SIZE  = os.getenv("OPENAI_IMAGE_SIZE", "1024x1536")     # portrait
SNAPSHOT_MAX       = int(os.getenv("SNAPSHOT_MAX", "4"))   # how many features to visualise
SNAPSHOT_WORKERS   = int(os.getenv("SNAPSHOT_WORKERS", "4"))  # parallel image renders

SUPPORTED_YEARS = [2022, 2023, 2024, 2025, 2026]

# Platforms the dashboard knows about (id must match scraper output filename
# <id>_data.json). "free" = no paid API needed.
PLATFORMS = [
    {"id": "reddit",      "name": "Reddit",       "icon": "💬", "free": True,
     "desc": "Subreddit posts + comments (free key recommended — keyless 403s)"},
    {"id": "steam",       "name": "Steam",        "icon": "🎮", "free": True,
     "desc": "SteamSpy + Steam reviews (no key)"},
    {"id": "googleplay",  "name": "Google Play",  "icon": "📱", "free": True,
     "desc": "Play Store reviews (no key)"},
    {"id": "appstore",    "name": "App Store",    "icon": "🍎", "free": True,
     "desc": "iOS reviews via iTunes RSS (no key)"},
    {"id": "hackernews",  "name": "Hacker News",  "icon": "🟠", "free": True,
     "desc": "HN stories + comments (Algolia, no key)"},
    {"id": "gamenews",    "name": "Gaming News",  "icon": "📰", "free": True,
     "desc": "IGN, Polygon, Eurogamer + more (RSS, no key)"},
    {"id": "googletrends","name": "Google Trends","icon": "📈", "free": True,
     "desc": "Search interest + rising queries (pytrends)"},
    {"id": "wikipedia",   "name": "Wikipedia",    "icon": "📚", "free": True,
     "desc": "Pageview trends per game/genre (no key)"},
    {"id": "steamtrending","name": "Steam Trending","icon":"🔥","free": True,
     "desc": "SteamSpy top-100 by players/2wk (no key)"},
    {"id": "steamcharts", "name": "Steam Charts",  "icon": "💰", "free": True,
     "desc": "Top sellers / new releases / specials (no key)"},
    {"id": "github",      "name": "GitHub",        "icon": "🐙", "free": True,
     "desc": "Trending game repos & engines (no key)"},
    {"id": "itch",        "name": "itch.io",       "icon": "🎨", "free": True,
     "desc": "Featured indie games (RSS, no key)"},
    {"id": "appcharts",   "name": "App Store Charts", "icon": "📊", "free": True,
     "desc": "Per-genre top-free/top-grossing charts (iTunes RSS, no key)"},
    {"id": "rawg",        "name": "RAWG DB",       "icon": "🗄️", "free": False,
     "desc": "Game database: ratings/genres/popularity (free key)"},
    {"id": "youtube",     "name": "YouTube",      "icon": "▶️", "free": False,
     "desc": "Game video comments (needs free API key)"},
    {"id": "twitch",      "name": "Twitch",       "icon": "🟣", "free": False,
     "desc": "Top games by viewers (needs free app key)"},
]
PLATFORM_IDS = [p["id"] for p in PLATFORMS]


def get_year_dir(year: int | None) -> str:
    """Return (and create) the data directory for a year, or the base dir.

    Inside the Lambda scrape worker the repo checkout is read-only (same
    constraint as Vercel) — only /tmp is writable there, so redirect. The
    worker never reads this path back; it uses run()'s in-memory return
    value directly and uploads that to S3, so this write is a harmless,
    unread side effect that lets every scraper module stay unmodified.
    """
    base = os.path.join(os.getenv("TMPDIR", "/tmp"), "lore_scratch") if IS_LAMBDA else DATA_DIR
    path = os.path.join(base, str(year)) if year else base
    os.makedirs(path, exist_ok=True)
    return path


# ── Research target ──────────────────────────────────────────────────────────
# The engine now researches N genres at once rather than one hardcoded niche.
# `GENRES` holds every genre-scoped input (subreddits, search queries, app
# IDs, competitors, ...); `ACTIVE_GENRES` picks which of those actually run.
# Scrapers that aren't genre-scoped by nature (news, GitHub, itch.io, Steam
# charts, Twitch top-games) are untouched — those stay whole-market signals.
# See MOBILE_EXPANSION_PLAN.md for the reasoning behind this shape.

# Reddit — public JSON endpoints, no API key needed (run locally; residential
# IPs are served, datacenter IPs often 403). A free OAuth key (REDDIT_CLIENT_ID/
# SECRET) is used automatically if present and makes it bulletproof.
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "script:redtail-market-intel:v1.0 (market research)")

# Subreddits/keywords that apply regardless of which genres are active.
# NICHE/topical subs: every post is relevant → keep all, tagged genre="general".
# BROAD subs: huge + off-topic → keep only posts matching a keyword list.
SUBREDDITS_COMMON = [
    "MobileGaming", "AndroidGaming", "iosgaming",
    "FreeToPlay", "gamedesign", "IndieGaming", "gamedev",
]
SUBREDDITS_BROAD = [
    "gaming", "Games", "gamingsuggestions", "patientgamers", "truegaming",
]
REDDIT_KEYWORDS_COMMON = [
    "mobile", "pvp", "1v1", "competitive", "ranked",
    "monetization", "pay to win", "p2w", "microtransaction", "ads",
    "matchmaking", "grind", "progression", "quick match", "short session",
    "retention", "quit", "uninstalled", "battle pass", "cosmetic",
]
REDDIT_POST_LIMIT    = 25               # max posts kept per subreddit (deduped)
REDDIT_COMMENT_LIMIT = 8                # top comments pulled per post

STEAM_REVIEWS_PER_APP = 100
GOOGLE_PLAY_N_APPS    = 5
GOOGLE_PLAY_REVIEWS   = 100
APP_STORE_REVIEWS     = 80

# Hacker News queries that apply regardless of which genres are active.
HN_QUERIES_COMMON = ["mobile game", "game monetization", "free to play"]
HN_HITS_PER_Q     = 30
HN_COMMENTS_PER   = 10

# ── Genre registry ───────────────────────────────────────────────────────────
# Every genre-scoped scraper (reddit, steam, googleplay, appstore, hackernews,
# googletrends, wikipedia, youtube, rawg, appcharts) loops over
# `ACTIVE_GENRES` and pulls its inputs from here, tagging each record with
# `genre=<key>`. App Store/Steam/RAWG genre IDs and app IDs below were looked
# up and verified against the live iTunes RSS / SteamSpy / App Store Search
# APIs while building this — not guessed.
GENRES = {
    "fighting": {
        "label":            "Fighting / Competitive PvP",
        "subreddits":       ["FightingGames", "Fighters", "StreetFighter", "Tekken",
                             "MortalKombat", "SmashBros", "Brawlhalla", "ClashRoyale",
                             "Brawlstars"],
        "reddit_keywords":  ["fighting game", "brawler", "combo", "tier list",
                             "frame data", "versus"],
        "steam_tag":        "Fighting",
        # Verified live against SteamSpy — the previous IDs here (1716740,
        # 2358720) actually resolved to Starfield and Black Myth: Wukong, not
        # Brawlhalla/SF6, silently polluting fighting-genre signal with
        # unrelated AAA RPG reviews. Brawlhalla is already covered via the
        # "Fighting" tag auto-discovery above; these two are supplemental.
        "steam_app_ids":    ["1364780", "359550"],  # Street Fighter 6, Rainbow Six Siege
        "google_play_query": "mobile fighting game pvp",
        "app_store_apps": [
            {"name": "brawlhalla",    "app_id": "1344199847"},
            {"name": "shadowfight3",  "app_id": "1132900541"},
            {"name": "streetfighter", "app_id": "6446903120"},
        ],
        "hn_query":         "fighting game",
        "trend_term":       "mobile fighting game",
        "wiki_article":     "Fighting_game",
        "yt_query":         "mobile fighting game",
        "rawg_genre":       "fighting",
        "apple_chart_genre": "6014",  # no dedicated Fighting genre ID on the App Store — overall Games
        "competitors": {
            "Brawlhalla":     ["brawlhalla"],
            "Shadow Fight":   ["shadow fight", "shadowfight"],
            "Street Fighter": ["street fighter", "streetfighter"],
            "Mortal Kombat":  ["mortal kombat"],
            "Injustice":      ["injustice"],
            "Clash Royale":   ["clash royale"],
        },
    },
    "puzzle": {
        "label":            "Puzzle",
        # No single dominant, verified-active puzzle-only subreddit — rely on
        # the keyword-filtered broad subs (SUBREDDITS_BROAD) instead.
        "subreddits":       [],
        "reddit_keywords":  ["puzzle game", "match-3", "match three", "brain teaser",
                             "level pack", "tile match"],
        "steam_tag":        "Match 3",  # verified live against SteamSpy — real puzzle titles
        "steam_app_ids":    [],
        "google_play_query": "puzzle match 3 game",
        "app_store_apps": [
            {"name": "royalmatch",      "app_id": "1482155847"},
            {"name": "candycrushsaga",  "app_id": "553834731"},
        ],
        "hn_query":         "puzzle game",
        "trend_term":       "puzzle game",
        "wiki_article":     "Puzzle_video_game",
        "yt_query":         "best mobile puzzle game",
        "rawg_genre":       "puzzle",
        "apple_chart_genre": "7012",  # Puzzle — verified live against the iTunes charts RSS
        "competitors": {
            "Royal Match":   ["royal match"],
            "Candy Crush":   ["candy crush"],
            "Gardenscapes":  ["gardenscapes"],
            "Homescapes":    ["homescapes"],
        },
    },
    "gacha": {
        "label":            "Gacha / Collection RPG",
        "subreddits":       ["gachagaming"],
        "reddit_keywords":  ["gacha", "banner", "pity", "summon", "reroll", "waifu"],
        "steam_tag":        None,  # no meaningful PC/Steam analog for mobile gacha monetization
        "steam_app_ids":    [],
        "google_play_query": "gacha rpg game",
        "app_store_apps": [
            {"name": "genshinimpact",  "app_id": "1517783697"},
            {"name": "fategrandorder", "app_id": "1183802626"},
        ],
        "hn_query":         "gacha game",
        "trend_term":       "gacha game",
        "wiki_article":     "Gacha_game",
        "yt_query":         "gacha game review",
        "rawg_genre":       "role-playing-games-rpg",
        "apple_chart_genre": "7014",  # Role Playing — closest App Store proxy for gacha
        "competitors": {
            "Genshin Impact":       ["genshin"],
            "Fate/Grand Order":     ["fate/grand order", "fgo"],
            "Honkai: Star Rail":    ["honkai"],
            "Raid: Shadow Legends": ["raid: shadow legends", "raid shadow legends"],
        },
    },
    "idle": {
        "label":            "Idle / Incremental",
        "subreddits":       ["incremental_games"],
        "reddit_keywords":  ["idle game", "incremental", "afk", "prestige",
                             "offline progress", "clicker"],
        "steam_tag":        "Idler",  # verified live against SteamSpy — Cookie Clicker, AdVenture Capitalist, IdleOn
        "steam_app_ids":    [],
        "google_play_query": "idle incremental game",
        "app_store_apps": [
            {"name": "afkarena", "app_id": "1375425432"},
            {"name": "egginc",   "app_id": "993492744"},
        ],
        "hn_query":         "idle game",
        "trend_term":       "idle game",
        "wiki_article":     "Incremental_game",
        "yt_query":         "best idle mobile game",
        "rawg_genre":       "casual",  # RAWG has no dedicated "idle" genre; casual is the closest bucket
        "apple_chart_genre": "7015",  # Simulation — closest App Store proxy (no dedicated Idle genre)
        "competitors": {
            "AFK Arena":     ["afk arena"],
            "Egg, Inc.":     ["egg, inc", "egg inc"],
            "Cookie Clicker": ["cookie clicker"],
            "Idle Heroes":   ["idle heroes"],
        },
    },
    "hybrid_casual": {
        "label":            "Hybrid-Casual",
        # A publishing/monetization category, not a player community — no
        # dedicated subreddit; rely on keyword-filtered broad/dev subs.
        "subreddits":       [],
        "reddit_keywords":  ["hybrid casual", "hyper casual", "playable ad",
                             "ad monetization", "rewarded ad"],
        "steam_tag":        None,  # mobile-ads business model term, not a Steam/PC category
        "steam_app_ids":    [],
        "google_play_query": "hyper casual game",
        "app_store_apps": [
            {"name": "joinclash",     "app_id": "1499812410"},
            {"name": "countmasters",  "app_id": "1568245971"},
        ],
        "hn_query":         "hyper casual game",
        "trend_term":       "hyper casual game",
        "wiki_article":     "Hyper-casual_game",
        "yt_query":         "hyper casual game",
        "rawg_genre":       "casual",
        "apple_chart_genre": "7003",  # Casual — closest App Store proxy for hybrid/hyper-casual
        "competitors": {
            "Join Clash":     ["join clash"],
            "Count Masters":  ["count masters"],
            "Save the Doge":  ["save the doge"],
        },
    },
}

# Comma-separated genre keys to research, e.g. LORE_GENRES=fighting,puzzle.
# Defaults to every genre in the registry. Unknown keys are dropped silently
# (a typo shouldn't crash a scrape); if that empties the list, fall back to
# "fighting" so the pipeline never silently researches nothing.
ACTIVE_GENRES = [g.strip() for g in os.getenv("LORE_GENRES", ",".join(GENRES)).split(",")
                 if g.strip() in GENRES] or ["fighting"]

# Merged competitor list across active genres — analysis.py's competitors()
# already sorts by mention count and truncates to the top few, so a bigger
# merged dict is harmless.
COMPETITORS = {}
for _g in ACTIVE_GENRES:
    COMPETITORS.update(GENRES[_g]["competitors"])
del _g

# ── Gaming news RSS (no key) ─────────────────────────────────────────────────
GAMENEWS_FEEDS = [
    ("IGN",             "https://feeds.ign.com/ign/games-all"),
    ("Polygon",         "https://www.polygon.com/rss/index.xml"),
    ("Eurogamer",       "https://www.eurogamer.net/feed"),
    ("GamesIndustry",   "https://www.gamesindustry.biz/feed"),
    ("GameDeveloper",   "https://www.gamedeveloper.com/rss.xml"),
    ("PocketGamer",     "https://www.pocketgamer.com/rss/"),
    ("TouchArcade",     "https://toucharcade.com/feed/"),
    ("RockPaperShotgun","https://www.rockpapershotgun.com/feed"),
    ("Kotaku",          "https://kotaku.com/rss"),
    ("PCGamer",         "https://www.pcgamer.com/rss/"),
    ("GamesRadar",      "https://www.gamesradar.com/rss/"),
    ("VGC",             "https://www.videogameschronicle.com/feed/"),
    ("GameRant",        "https://gamerant.com/feed/"),
    ("PocketTactics",   "https://www.pockettactics.com/feed"),
]
GAMENEWS_PER_FEED = 50

# ── Steam charts (no key, Steam store featuredcategories) ────────────────────
STEAM_CHARTS_PER_LIST = 30   # per list: top sellers, new releases, specials

# ── GitHub trending game projects (no key; low unauth rate limit) ────────────
GITHUB_QUERIES = ["topic:game", "topic:gamedev", "topic:game-engine", "mobile game"]
GITHUB_PER_Q   = 15

# ── itch.io featured indie games (no key, RSS) ───────────────────────────────
ITCH_FEED  = "https://itch.io/feed/featured.xml"
ITCH_LIMIT = 50

# ── RAWG video game database (free key: rawg.io/apidocs) ─────────────────────
RAWG_API_KEY   = os.getenv("RAWG_API_KEY", "")
RAWG_PAGE_SIZE = 40

# ── Google Trends (no key, pytrends) ─────────────────────────────────────────
# Terms that apply regardless of which genres are active; each active genre
# additionally contributes its own `trend_term`.
TREND_TERMS_COMMON = ["battle royale", "auto battler", "roguelike", "hero shooter"]

# ── Wikipedia pageviews (no key, Wikimedia REST) ─────────────────────────────
# Articles that apply regardless of which genres are active; each active
# genre additionally contributes its own `wiki_article`.
WIKI_ARTICLES_COMMON = ["Mobile_game", "Free-to-play", "Esports", "Battle_royale_game"]

# ── Apple top charts (no key, iTunes RSS, genre-parameterized) ───────────────
APPCHARTS_COUNTRY = "us"
APPCHARTS_LIMIT   = 50   # top N per chart (top-free + top-grossing games)

# ── SteamSpy trending (no key) ───────────────────────────────────────────────
STEAM_TRENDING_N = 60    # top N from top100in2weeks

# ── YouTube (needs free key: console.cloud.google.com → YouTube Data API v3) ──
# Queries that apply regardless of which genres are active; each active genre
# additionally contributes its own `yt_query`.
YOUTUBE_API_KEY   = os.getenv("YOUTUBE_API_KEY", "")
YT_QUERIES_COMMON = ["best mobile pvp game"]
YT_VIDEOS_PER_Q   = 5
YT_COMMENTS_PER   = 30

# ── Twitch (needs free app: dev.twitch.tv/console/apps) ──────────────────────
TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_TOP_GAMES     = 60

# ── Signal taxonomy (keyword → demand signal) ────────────────────────────────
# Used for cheap pre-aggregation before Claude does the deep analysis.
SIGNAL_KEYWORDS = {
    "Short-session preference":    ["quick", "fast", "5 min", "short match", "quick game", "on the go", "short session", "lunch break"],
    "Negative ad sentiment":       ["too many ads", "ad spam", "pay to win", "p2w", "microtransaction", "paywall", "forced ads", "monetization bad"],
    "Competitive / PvP demand":    ["pvp", "1v1", "ranked", "competitive", "tournament", "esport", "ladder", "versus"],
    "Fast progression demand":     ["progression", "level up", "grind", "unlock", "rank up", "skill tree", "power up", "upgrade fast"],
    "Co-op / social play":         ["coop", "co-op", "friends", "multiplayer", "guild", "clan", "team up", "party"],
    "Cosmetic monetization ok":    ["cosmetic", "skin", "costume", "no p2w", "fair monetization", "cosmetics only", "battle pass"],
}
# COMPETITORS itself is built above from GENRES + ACTIVE_GENRES (§ Genre registry).