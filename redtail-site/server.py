"""
server.py — Lore backend for the Redtail site.

Serves the static site (locally) + the Lore API:
  GET  /api/lore/env           — model info + deployed flag + platform list
  GET  /api/lore/status        — scrape snapshot (green ticks + last scraped)
  POST /api/lore/scrape        — scrape a year (password-gated)
  GET  /api/lore/scrape/status — poll a scrape job's per-source progress
  POST /api/lore/report        — LIVE Claude intelligence report (password-gated)
  POST /api/lore/game-report   — LIVE report analysing an UPLOADED game vs. market data (password-gated)
  POST /api/lore/snapshot      — redesign from an UPLOADED game PDF (password-gated)
  POST /api/lore/waitlist      — collect name+email from non-members (public, no password)

On Vercel only /api/* hits this function (see vercel.json); the HTML/images are
served statically. Locally, this also serves the static files.

Locally, scraping runs in a background thread and writes straight to
lore_data/ (see manifest.rebuild()). When DEPLOYED (Vercel's serverless
functions have no writable filesystem and no thread that survives past the
response), scraping instead enqueues one SQS message per platform and a
separate Lambda worker (lore_engine/worker.py) does the actual scrape,
writing results to S3 (lore_engine/storage.py) with a 1-week freshness TTL
on the current calendar year only.
"""
import importlib
import json
import os
import re
import sys
import threading
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "lore_engine"))   # engine modules import each other top-level

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import report      # noqa: E402  (from lore_engine/)
import snapshot    # noqa: E402
import llm         # noqa: E402
import config      # noqa: E402
import manifest as manifest_mod  # noqa: E402
import storage      # noqa: E402

LORE_PASSWORD = os.getenv("LORE_PASSWORD", "redtaillore@2026")
# Time-boxed guest login — expires on its own, no separate revoke step needed.
# Username is checked client-side only (see lore.html doLogin); this password
# check is the actual server-side gate every API call goes through.
GUEST_PASSWORD = os.getenv("LORE_GUEST_PASSWORD", "loreguest@2026")
GUEST_EXPIRES = datetime.fromisoformat(
    os.getenv("LORE_GUEST_EXPIRES", "2026-08-29T23:59:59+00:00"))

# Vercel sets VERCEL=1 on deployed functions.
DEPLOYED = config.DEPLOYED

app = FastAPI(title="Lore — Redtail")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


def _ok(pw: str) -> bool:
    pw = pw or ""
    if pw == LORE_PASSWORD:
        return True
    if pw == GUEST_PASSWORD:
        return datetime.now(timezone.utc) < GUEST_EXPIRES
    return False
    


class ReportReq(BaseModel):
    backtest_years: list[int] = []
    validation_years: list[int] = []
    genre: str | None = None  # None = aggregate across every scraped genre (default)
    password: str = ""


class ScrapeReq(BaseModel):
    year: int
    password: str = ""


class WaitlistReq(BaseModel):
    first_name: str
    last_name: str
    email: str


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.get("/api/lore/env")
def env():
    return {"model_text": llm.active_model(), "image_model": config.OPENAI_IMAGE_MODEL,
            "deployed": DEPLOYED, "platforms": config.PLATFORMS,
            "genres": {g: v["label"] for g, v in config.GENRES.items()},
            "active_genres": config.ACTIVE_GENRES}


@app.get("/api/lore/status")
def status():
    if DEPLOYED:
        return storage.compute_manifest()
    mf = os.path.join(config.DATA_DIR, "manifest.json")
    if os.path.exists(mf):
        return json.load(open(mf))
    return {"scraped_at": "unknown", "years": {}}


# ── Scrape jobs (local only) ─────────────────────────────────────────────────
_scrape_lock = threading.Lock()


def _blank_scrape(year):
    return {"status": "idle", "year": year, "log": [],
            "platforms": {p: "idle" for p in config.PLATFORM_IDS}}


_scrape = {str(y): _blank_scrape(y) for y in config.SUPPORTED_YEARS}


def _run_scrape_job(year: int):
    ys = str(year)

    def log(line):
        with _scrape_lock:
            _scrape[ys]["log"].append(str(line))
            _scrape[ys]["log"] = _scrape[ys]["log"][-100:]

    for pid in config.PLATFORM_IDS:
        with _scrape_lock:
            _scrape[ys]["platforms"][pid] = "running"
        try:
            records = importlib.import_module(f"scrapers.{pid}").run(year=year, log=log)
            with _scrape_lock:
                _scrape[ys]["platforms"][pid] = "done" if records else "empty"
        except Exception as e:
            log(f"[{pid}] error: {e}")
            with _scrape_lock:
                _scrape[ys]["platforms"][pid] = "error"

    try:
        manifest = manifest_mod.rebuild()
        has_data = bool(manifest.get("years", {}).get(ys, {}).get("sources"))
        with _scrape_lock:
            if has_data:
                _scrape[ys]["status"] = "done"
            else:
                _scrape[ys]["status"] = "error"
                _scrape[ys]["error"] = "Scrape finished with no usable data"
    except Exception as e:
        log(f"[manifest] error: {e}")
        with _scrape_lock:
            _scrape[ys]["status"] = "error"
            _scrape[ys]["error"] = f"Could not update scrape manifest: {e}"


@app.post("/api/lore/scrape")
def start_scrape(req: ScrapeReq):
    if not _ok(req.password):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if req.year not in config.SUPPORTED_YEARS:
        return JSONResponse({"error": f"year must be one of {config.SUPPORTED_YEARS}"},
                            status_code=400)
    if DEPLOYED:
        return _start_scrape_deployed(req.year)

    ys = str(req.year)
    with _scrape_lock:
        if _scrape[ys]["status"] == "running":
            return JSONResponse({"error": f"already scraping {req.year}"}, status_code=409)
        # Reserve the job before starting the thread so rapid clicks cannot start
        # two scrapes for the same year.
        _scrape[ys].update(status="running", log=[])
        _scrape[ys].pop("error", None)
        for pid in config.PLATFORM_IDS:
            _scrape[ys]["platforms"][pid] = "pending"
    threading.Thread(target=_run_scrape_job, args=(req.year,), daemon=True).start()
    return {"status": "started", "year": req.year}


def _start_scrape_deployed(year: int) -> dict:
    """Deployed mode has no writable filesystem and no thread that survives
    past the response, so scraping goes through S3 + SQS instead: skip
    platforms whose cache is still fresh, enqueue one message per platform
    that needs work, and let the Lambda worker do the actual scraping.

    This is now the manual ops fallback (see lore.html's ?ops=1 gate) — the
    weekly scrape itself is triggered independently by an EventBridge
    Scheduler invoking lore_engine/scheduler.py, which calls the same
    storage.enqueue_missing_platforms() with force=True."""
    queued = storage.enqueue_missing_platforms(year, force=False)
    if not queued:
        return {"status": "done", "year": year, "note": "all platforms already fresh"}
    return {"status": "started", "year": year, "queued": queued}


@app.get("/api/lore/scrape/status")
def scrape_status(year: int):
    if DEPLOYED:
        return storage.scrape_status_snapshot(year)
    with _scrape_lock:
        return dict(_scrape.get(str(year), _blank_scrape(year)))


@app.post("/api/lore/report")
def make_report(req: ReportReq):
    if not _ok(req.password):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if not req.backtest_years:
        return JSONResponse({"error": "Select at least one year"}, status_code=400)
    if req.genre and req.genre not in config.GENRES:
        return JSONResponse({"error": f"genre must be one of {list(config.GENRES)}"},
                            status_code=400)
    try:
        return {"html": report.generate(req.backtest_years, req.validation_years, req.genre)}
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)

@app.post("/api/lore/game-report")
async def make_game_report(file: UploadFile = File(...), years: str = Form(...),
                           password: str = Form("")):
    if not _ok(password):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        yrs = [int(y) for y in years.split(",") if y.strip()]
    except ValueError:
        return JSONResponse({"error": "Invalid years"}, status_code=400)
    if not yrs:
        return JSONResponse({"error": "Select at least one year"}, status_code=400)
    try:
        data = await file.read()
        path, gname = snapshot.prep_upload(data, file.filename)
        game_text = snapshot.load_game_text(path)
        return {"html": report.generate_game_report(yrs, game_text, gname), "game": gname}
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.post("/api/lore/waitlist")
def join_waitlist(req: WaitlistReq):
    first = req.first_name.strip()
    last = req.last_name.strip()
    email = req.email.strip()
    if not first or not last:
        return JSONResponse({"error": "First and last name are required"}, status_code=400)
    if not _EMAIL_RE.match(email):
        return JSONResponse({"error": "Enter a valid email address"}, status_code=400)
    try:
        if DEPLOYED:
            storage.add_waitlist_entry(first, last, email)
        else:
            path = os.path.join(config.DATA_DIR, "waitlist.json")
            entries = json.load(open(path)) if os.path.exists(path) else []
            entries.append({
                "first_name": first, "last_name": last, "email": email.lower(),
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            })
            os.makedirs(config.DATA_DIR, exist_ok=True)
            json.dump(entries, open(path, "w"), ensure_ascii=False, indent=2)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.post("/api/lore/snapshot")
async def make_snapshot(file: UploadFile = File(...), year: int = Form(2026),
                        password: str = Form("")):
    if not _ok(password):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        data = await file.read()
        return snapshot.generate_snapshot(year, upload_bytes=data,
                                          upload_name=file.filename)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


# Static site (local dev; on Vercel the HTML/images are served directly).
app.mount("/", StaticFiles(directory=str(HERE), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8100))
    print(f"\n  Redtail site + Lore → http://localhost:{port}   (Lore: /lore.html)\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
