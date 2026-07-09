"""
config.py — central configuration for the AI market-intelligence engine.

Edit the RESEARCH section to change what you analyse. Everything downstream
(scrapers, analysis, report) reads from here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────────
HERE     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
GAMES_DIR     = os.path.join(HERE, "games")       # game design docs (PDF/MD/TXT)
SNAPSHOTS_DIR = os.path.join(HERE, "snapshots")   # generated game snapshots

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
    {"id": "rawg",        "name": "RAWG DB",       "icon": "🗄️", "free": False,
     "desc": "Game database: ratings/genres/popularity (free key)"},
    {"id": "youtube",     "name": "YouTube",      "icon": "▶️", "free": False,
     "desc": "Game video comments (needs free API key)"},
    {"id": "twitch",      "name": "Twitch",       "icon": "🟣", "free": False,
     "desc": "Top games by viewers (needs free app key)"},
]
PLATFORM_IDS = [p["id"] for p in PLATFORMS]


def get_year_dir(year: int | None) -> str:
    """Return (and create) the data directory for a year, or the base dir."""
    path = os.path.join(DATA_DIR, str(year)) if year else DATA_DIR
    os.makedirs(path, exist_ok=True)
    return path


# ── Research target ──────────────────────────────────────────────────────────
# Change these to research a different market.

# Reddit — public JSON endpoints, no API key needed (run locally; residential
# IPs are served, datacenter IPs often 403). A free OAuth key (REDDIT_CLIENT_ID/
# SECRET) is used automatically if present and makes it bulletproof.
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "script:redtail-market-intel:v1.0 (market research)")

# Subreddits to mine. NICHE/topical subs: every post is relevant → keep all.
# BROAD subs: huge + off-topic → keep only posts matching REDDIT_KEYWORDS.
SUBREDDITS = [
    # mobile
    "MobileGaming", "AndroidGaming", "iosgaming", "gachagaming",
    # fighting / competitive PvP
    "FightingGames", "Fighters", "StreetFighter", "Tekken", "MortalKombat",
    "SmashBros", "Brawlhalla", "ClashRoyale", "Brawlstars",
    # monetization / design / dev
    "FreeToPlay", "gamedesign", "IndieGaming", "gamedev",
    # broad (keyword-filtered)
    "gaming", "Games", "gamingsuggestions", "patientgamers", "truegaming",
]
REDDIT_BROAD = {
    "gaming", "Games", "gamingsuggestions", "patientgamers", "truegaming",
    "gamedev", "gamedesign",
}
REDDIT_KEYWORDS = [
    "mobile", "fighting game", "pvp", "1v1", "competitive", "ranked", "brawler",
    "gacha", "monetization", "pay to win", "p2w", "microtransaction", "ads",
    "matchmaking", "grind", "progression", "quick match", "short session",
    "retention", "quit", "uninstalled", "battle pass", "cosmetic",
]
REDDIT_SORTS         = ["top", "hot"]   # listings pulled per subreddit
REDDIT_TOP_TIME      = "year"           # time window for the 'top' listing
REDDIT_POST_LIMIT    = 120              # max posts per subreddit (deduped)
REDDIT_COMMENT_LIMIT = 8                # top comments pulled per post

# Steam (no key)
STEAM_GENRE_TAG       = "Fighting"
STEAM_APP_IDS         = ["1716740", "2358720", "359550"]  # Brawlhalla, SF6, R6
STEAM_REVIEWS_PER_APP = 100

# Google Play (no key)
GOOGLE_PLAY_QUERY   = "mobile fighting game pvp"
GOOGLE_PLAY_N_APPS  = 5
GOOGLE_PLAY_REVIEWS = 100

# App Store (no key, iTunes RSS)
APP_STORE_APPS = [
    {"name": "brawlhalla",    "app_id": "1344199847"},
    {"name": "shadowfight3",  "app_id": "1132900541"},
    {"name": "streetfighter", "app_id": "6446903120"},
]
APP_STORE_REVIEWS = 80

# Hacker News (no key, Algolia search API)
HN_QUERIES      = ["mobile game", "fighting game", "game monetization", "free to play"]
HN_HITS_PER_Q   = 30
HN_COMMENTS_PER = 10

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
TREND_TERMS = [
    "mobile fighting game", "gacha game", "battle royale", "fighting game",
    "auto battler", "idle game", "roguelike", "hero shooter",
]

# ── Wikipedia pageviews (no key, Wikimedia REST) ─────────────────────────────
WIKI_ARTICLES = [
    "Mobile_game", "Fighting_game", "Battle_royale_game", "Gacha_game",
    "Free-to-play", "Esports", "Street_Fighter_6", "Tekken_8",
    "Mortal_Kombat_1", "Brawl_Stars", "Clash_Royale",
]

# ── Apple top charts (no key, Apple Marketing RSS) ───────────────────────────
APPCHARTS_COUNTRY = "us"
APPCHARTS_LIMIT   = 50   # top N per chart (top-free + top-grossing games)

# ── SteamSpy trending (no key) ───────────────────────────────────────────────
STEAM_TRENDING_N = 60    # top N from top100in2weeks

# ── YouTube (needs free key: console.cloud.google.com → YouTube Data API v3) ──
YOUTUBE_API_KEY  = os.getenv("YOUTUBE_API_KEY", "")
YT_QUERIES       = ["mobile fighting game", "best mobile pvp game", "gacha game review"]
YT_VIDEOS_PER_Q  = 5
YT_COMMENTS_PER  = 30

# ── Twitch (needs free app: dev.twitch.tv/console/apps) ──────────────────────
TWITCH_CLIENT_ID     = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_TOP_GAMES     = 60

# ── Signal taxonomy (keyword → demand signal) ────────────────────────────────
# Used for cheap pre-aggregation before Claude does the deep analysis.
SIGNAL_KEYWORDS = {
    "Short-session preference":    ["quick", "fast", "5 min", "short match", "quick game", "on the go", "short session", "lunch break"],
    "Preference for <90s matches": ["90 second", "quick match", "fast round", "short round", "under 2 min", "60 sec", "instant"],
    "Negative ad sentiment":       ["too many ads", "ad spam", "pay to win", "p2w", "microtransaction", "paywall", "forced ads", "monetization bad"],
    "Competitive / PvP demand":    ["pvp", "1v1", "ranked", "competitive", "tournament", "esport", "ladder", "versus"],
    "Fast progression demand":     ["progression", "level up", "grind", "unlock", "rank up", "skill tree", "power up", "upgrade fast"],
    "Co-op / social play":         ["coop", "co-op", "friends", "multiplayer", "guild", "clan", "team up", "party"],
    "Cosmetic monetization ok":    ["cosmetic", "skin", "costume", "no p2w", "fair monetization", "cosmetics only", "battle pass"],
}

# Competitors to track in the snapshot (display name → match substrings)
COMPETITORS = {
    "Brawlhalla":     ["brawlhalla"],
    "Shadow Fight":   ["shadow fight", "shadowfight"],
    "Street Fighter": ["street fighter", "streetfighter"],
    "Mortal Kombat":  ["mortal kombat"],
    "Injustice":      ["injustice"],
    "Clash Royale":   ["clash royale"],
}
