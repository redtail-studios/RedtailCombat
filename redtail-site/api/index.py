"""Vercel serverless entry — exposes the Lore FastAPI app (handles /api/* only)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "lore_engine"))

from server import app  # noqa: E402
