"""manifest.py — rebuild lore_data/manifest.json from whatever *_data.json files
are on disk. Read by /api/lore/status (and lore.html's Step 1 card).
"""
import json
import time
from pathlib import Path

from config import DATA_DIR, SUPPORTED_YEARS


def rebuild() -> dict:
    years = {}
    for y in SUPPORTED_YEARS:
        ydir = Path(DATA_DIR) / str(y)
        if not ydir.exists():
            continue
        sources = {}
        for f in sorted(ydir.glob("*_data.json")):
            try:
                records = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            name = f.stem.replace("_data", "")
            count = len(records) if isinstance(records, list) else 1
            if count:   # omit empty sources (no key configured, scraper failed, etc.)
                sources[name] = count
        if sources:
            years[str(y)] = {"sources": sources, "total": sum(sources.values())}

    manifest = {
        "scraped_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "years": years,
    }
    path = Path(DATA_DIR) / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
