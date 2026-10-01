"""Shared account/auth + per-user data helpers.

Pulled out of server.py so workspace.py (and friends) can check credentials
and read/write a user's saved reports/portfolio without importing server.py
itself — server.py imports workspace.py, so the reverse import would be
circular.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timezone

import config
import storage

LORE_PASSWORD = os.getenv("LORE_PASSWORD", "redtaillore@2026")
# Time-boxed guest login — expires on its own, no separate revoke step needed.
GUEST_PASSWORD = os.getenv("LORE_GUEST_PASSWORD", "loreguest@2026")
GUEST_EXPIRES = datetime.fromisoformat(
    os.getenv("LORE_GUEST_EXPIRES", "2026-08-29T23:59:59+00:00"))
# Permanent co-founder/team accounts — same full access, separate credentials.
ADMIN_PASSWORD = os.getenv("LORE_ADMIN_PASSWORD", "redtailadmin@2026")
DAKOTA_PASSWORD = os.getenv("LORE_DAKOTA_PASSWORD", "dakotaredtail@2026")
ANDRES_PASSWORD = os.getenv("LORE_ANDRES_PASSWORD", "andresredtail@2026")
# External partner account (Caravela Capital) — same full access, own
# credential, own isolated per-user portfolio/reports (see user_ok below).
CARAVELA_PASSWORD = os.getenv("LORE_CARAVELA_PASSWORD", "7ghlZU1IB9hOo1JzyveK")
# Personal demo/preview account (Amritha) — same full access, own credential.
AMRITHA_PASSWORD = os.getenv("LORE_AMRITHA_PASSWORD", "amritha")
# External partner accounts (Cometa, Newtopia) — same full access, own
# credential, own isolated per-user portfolio/reports (see user_ok below).
COMETA_PASSWORD = os.getenv("LORE_COMETA_PASSWORD", "redt@ilcometa2026")
NEWTOPIA_PASSWORD = os.getenv("LORE_NEWTOPIA_PASSWORD", "redt@ilnewtopia2026")
# Personal demo/preview accounts (Mauricio, Santi) — same full access, own
# credential, own isolated per-user portfolio/reports.
MAURICIO_PASSWORD = os.getenv("LORE_MAURICIO_PASSWORD", "redt@ilmauricio2026")
SANTI_PASSWORD = os.getenv("LORE_SANTI_PASSWORD", "redt@ilsanti2026")
# Personal demo/preview accounts (Daniel Stein, Andres Sevilla) — same full
# access, own credential, own isolated per-user portfolio/reports.
# 'andressevilla' is a second, separate login for Andres Sevilla alongside
# the existing 'andres' account (kept as-is, not renamed).
DANIELSTEIN_PASSWORD = os.getenv("LORE_DANIELSTEIN_PASSWORD", "redt@ildanielstein@2026")
ANDRESSEVILLA_PASSWORD = os.getenv("LORE_ANDRESSEVILLA_PASSWORD", "redt@ilandressevilla@2026")


def ok(pw: str) -> bool:
    pw = pw or ""
    if pw in (LORE_PASSWORD, ADMIN_PASSWORD, DAKOTA_PASSWORD, ANDRES_PASSWORD, CARAVELA_PASSWORD, AMRITHA_PASSWORD, COMETA_PASSWORD, NEWTOPIA_PASSWORD, MAURICIO_PASSWORD, SANTI_PASSWORD, DANIELSTEIN_PASSWORD, ANDRESSEVILLA_PASSWORD):
        return True
    if pw == GUEST_PASSWORD:
        return datetime.now(timezone.utc) < GUEST_EXPIRES
    return False


def user_ok(username: str, password: str) -> bool:
    """Like ok(), but binds the password to the specific username it belongs
    to — so 'guest' can't accidentally (or otherwise) read/write 'lore's
    saved dashboard data by only getting the password right."""
    username = (username or "").strip().lower()
    if username == "lore":
        return password == LORE_PASSWORD
    if username == "admin":
        return password == ADMIN_PASSWORD
    if username == "dakota":
        return password == DAKOTA_PASSWORD
    if username == "andres":
        return password == ANDRES_PASSWORD
    if username == "caravelacapital":
        return password == CARAVELA_PASSWORD
    if username == "amritha":
        return password == AMRITHA_PASSWORD
    if username == "cometa":
        return password == COMETA_PASSWORD
    if username == "newtopia":
        return password == NEWTOPIA_PASSWORD
    if username == "mauricio":
        return password == MAURICIO_PASSWORD
    if username == "santi":
        return password == SANTI_PASSWORD
    if username == "danielstein":
        return password == DANIELSTEIN_PASSWORD
    if username == "andressevilla":
        return password == ANDRESSEVILLA_PASSWORD
    if username == "guest":
        return password == GUEST_PASSWORD and datetime.now(timezone.utc) < GUEST_EXPIRES
    dynamic = _dynamic_accounts().get(username)
    if dynamic:
        return password == dynamic.get("password")
    return False


# ── Admin-panel account management ──────────────────────────────────────────
# Everything above is a fixed, hardcoded account (credentials come from code
# or env vars) — adding one has always meant a code change + redeploy. The
# accounts below are created at runtime through the admin panel and persisted
# in S3, so admin-tier users (lore, admin) can onboard teammates themselves.
# LEGACY_ACCOUNTS exists purely so the admin panel can *display* the
# hardcoded accounts above alongside the dynamic ones in one list — it has no
# bearing on auth, which is still exactly the user_ok() chain above.
LEGACY_ACCOUNTS = [
    {"username": "lore", "password": LORE_PASSWORD, "displayName": "Lore (Owner)", "tier": "admin"},
    {"username": "admin", "password": ADMIN_PASSWORD, "displayName": "Admin (Co-founder)", "tier": "admin"},
    {"username": "dakota", "password": DAKOTA_PASSWORD, "displayName": "Dakota", "tier": "member"},
    {"username": "andres", "password": ANDRES_PASSWORD, "displayName": "Andres Sevilla", "tier": "member"},
    {"username": "caravelacapital", "password": CARAVELA_PASSWORD, "displayName": "Caravela Capital", "tier": "member"},
    {"username": "amritha", "password": AMRITHA_PASSWORD, "displayName": "Amritha", "tier": "member"},
    {"username": "cometa", "password": COMETA_PASSWORD, "displayName": "Cometa", "tier": "member"},
    {"username": "newtopia", "password": NEWTOPIA_PASSWORD, "displayName": "Newtopia", "tier": "member"},
    {"username": "mauricio", "password": MAURICIO_PASSWORD, "displayName": "Mauricio", "tier": "member"},
    {"username": "santi", "password": SANTI_PASSWORD, "displayName": "Santi", "tier": "member"},
    {"username": "danielstein", "password": DANIELSTEIN_PASSWORD, "displayName": "Daniel Stein", "tier": "member"},
    {"username": "andressevilla", "password": ANDRESSEVILLA_PASSWORD, "displayName": "Andres Sevilla (second login)", "tier": "member"},
]
_LEGACY_USERNAMES = {row["username"] for row in LEGACY_ACCOUNTS}

_DYNAMIC_CACHE = {"at": 0.0, "data": {}}
_DYNAMIC_TTL = 30  # seconds — matches workspace.py's market() cache pattern


def _dynamic_accounts() -> dict:
    if time.time() - _DYNAMIC_CACHE["at"] > _DYNAMIC_TTL:
        rows = storage.workspace_list_json("account")
        _DYNAMIC_CACHE["data"] = {row["username"]: row for row in rows if isinstance(row, dict) and row.get("username")}
        _DYNAMIC_CACHE["at"] = time.time()
    return _DYNAMIC_CACHE["data"]


def is_admin(username: str, password: str) -> bool:
    username = (username or "").strip().lower()
    for row in LEGACY_ACCOUNTS:
        if row["username"] == username:
            return row["tier"] == "admin" and password == row["password"]
    dynamic = _dynamic_accounts().get(username)
    return bool(dynamic and dynamic.get("tier") == "admin" and password == dynamic.get("password"))


def list_all_accounts() -> list:
    """Every account, legacy (hardcoded) and dynamic (created via the admin
    panel) — for the admin panel's own listing. Dynamic accounts always win
    a username collision (can't happen in practice; create_account() already
    refuses a username that's taken)."""
    merged = {row["username"]: {**row, "source": "built-in"} for row in LEGACY_ACCOUNTS}
    merged.update({username: {**row, "source": "created"} for username, row in _dynamic_accounts().items()})
    return sorted(merged.values(), key=lambda r: r["username"])


def create_account(username: str, password: str, display_name: str, tier: str = "member") -> dict:
    username = safe_username(username)
    if not username or username == "anon":
        raise ValueError("Enter a valid username.")
    if username in _LEGACY_USERNAMES or username in _dynamic_accounts():
        raise ValueError(f'The username "{username}" is already taken.')
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if tier not in ("admin", "member"):
        tier = "member"
    row = {
        "username": username, "password": password, "displayName": (display_name or username).strip()[:80],
        "tier": tier, "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    storage.workspace_put_json("account", username, row)
    _DYNAMIC_CACHE["at"] = 0.0  # force the next read to pick this up immediately
    return row


def safe_username(username: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", (username or "").lower())[:32] or "anon"


def _user_data_path(username: str) -> str:
    d = os.path.join(config.DATA_DIR, "users")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{safe_username(username)}.json")


_MAX_STORED_REPORTS = 20  # matches the previous client-side localStorage cap


def read_user_data(username: str) -> dict:
    if config.DEPLOYED:
        return storage.get_user_data(safe_username(username)) or {"reports": [], "portfolio": []}
    path = _user_data_path(username)
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return {"reports": [], "portfolio": []}


def write_user_data(username: str, reports: list, portfolio: list) -> None:
    payload = {"reports": reports[:_MAX_STORED_REPORTS], "portfolio": portfolio}
    if config.DEPLOYED:
        storage.save_user_data(safe_username(username), payload)
        return
    path = _user_data_path(username)
    # Write to a sibling temp file and os.replace() it in — atomic at the
    # filesystem level, so a second near-simultaneous save can never leave a
    # torn/corrupted file (valid JSON prefix + garbage suffix).
    tmp_path = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp_path, path)
