"""
config.py — Central configuration for the Redtail scraper pipeline.
Edit SUBREDDITS, STEAM_TAGS, PLAY_QUERY, and SIGNALS to change what you research.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Reddit ─────────────────────────────────────────────────────────────────────
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "RedtailScraper/1.0")

# Subreddits to scan
SUBREDDITS = [
    "gaming",
    "AndroidGaming",
    "iosgaming",
    "patientgamers",
    "FightingGames",
    "MobileGaming",
    "indiegaming",
]

# Keywords to find relevant posts within subreddits
REDDIT_KEYWORDS = [
    "mobile fighting", "pvp mobile", "brawler mobile", "fighting game mobile",
    "competitive mobile", "short session", "quick match",
]

REDDIT_POST_LIMIT = 100   # Posts per subreddit (max 1000 with PRAW)
REDDIT_COMMENT_LIMIT = 20  # Top comments per post

# ── Steam ──────────────────────────────────────────────────────────────────────
# SteamSpy genre tag to search (no API key needed)
STEAM_GENRE_TAG = "Fighting"

# Specific Steam app IDs to pull reviews for (add any relevant game IDs)
# Find app IDs in the Steam store URL: store.steampowered.com/app/APP_ID/
STEAM_APP_IDS = [
    "1716740",   # Brawlhalla
    "359550",    # Tom Clancy's Rainbow Six Siege (competitive reference)
    "2358720",   # Street Fighter 6
]

STEAM_REVIEWS_PER_APP = 100

# ── Google Play ────────────────────────────────────────────────────────────────
GOOGLE_PLAY_QUERY   = "mobile fighting game pvp"
GOOGLE_PLAY_N_APPS  = 5     # Number of apps to pull
GOOGLE_PLAY_REVIEWS = 100   # Reviews per app

# ── App Store (iOS) ────────────────────────────────────────────────────────────
# Provide app name + numeric ID from App Store URL
APP_STORE_APPS = [
    {"name": "brawlhalla",       "app_id": "1344199847"},
    {"name": "shadowfight3",     "app_id": "1132900541"},
    {"name": "streetfighter",    "app_id": "6446903120"},
]
APP_STORE_REVIEWS = 100

# ── Signal Keywords ────────────────────────────────────────────────────────────
# These map to the bar chart signals in the report.
# Each signal is a name + list of keywords that indicate it.
SIGNAL_KEYWORDS = {
    "Short-session preference":   ["quick", "fast", "5 min", "short match", "quick game", "on the go", "short session", "lunch break"],
    "Preference for <90s matches":["90 second", "quick match", "fast round", "short round", "under 2 min", "60 sec", "instant"],
    "Negative ad sentiment":      ["too many ads", "ad spam", "pay to win", "p2w", "microtransaction", "paywall", "forced ads", "monetization bad"],
    "Competitive fighting demand":["pvp", "1v1", "ranked", "competitive", "tournament", "esport", "ladder", "versus"],
    "Fast progression demand":    ["progression", "level up", "grind", "unlock", "rank up", "skill tree", "power up", "upgrade fast"],
    "Co-op / social play":        ["coop", "co-op", "friends", "multiplayer", "guild", "clan", "team up", "party"],
    "Cosmetic monetization ok":   ["cosmetic", "skin", "costume", "no p2w", "fair monetization", "cosmetics only", "battle pass"],
}

# ── Output paths ───────────────────────────────────────────────────────────────
DATA_DIR   = "data"
OUTPUT_DIR = "output"
