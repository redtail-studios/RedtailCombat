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


def ok(pw: str) -> bool:
    pw = pw or ""
    if pw in (LORE_PASSWORD, ADMIN_PASSWORD, DAKOTA_PASSWORD, ANDRES_PASSWORD):
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
    if username == "guest":
        return password == GUEST_PASSWORD and datetime.now(timezone.utc) < GUEST_EXPIRES
    return False


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
