"""
app.py — FastAPI backend + dashboard.

Runs two ways:
  • Local:  python app.py   → full power (scrape + analyse + Claude report)
  • Vercel: imported by api/index.py → analyse committed data + Claude report
            (scraping is disabled on serverless; do it locally and commit data)
"""
import os
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import report
import llm
from config import DATA_DIR, SUPPORTED_YEARS, PLATFORMS, PLATFORM_IDS

HERE      = Path(__file__).parent
DASHBOARD = HERE / "dashboard.html"

# Vercel sets VERCEL=1; treat any serverless flag as "deployed" (no scraping).
DEPLOYED = bool(os.getenv("VERCEL") or os.getenv("AI_ENGINE_DEPLOYED"))

app = FastAPI(title="AI Market Intelligence Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── Scrape job state (local only) ────────────────────────────────────────────
_lock = threading.Lock()


def _blank(year):
    return {"status": "idle", "year": year, "log": [],
            "platforms": {p: "idle" for p in PLATFORM_IDS}}


_scrape = {str(y): _blank(y) for y in SUPPORTED_YEARS}


# ── Models ───────────────────────────────────────────────────────────────────
class ScrapeReq(BaseModel):
    year: int


class ReportReq(BaseModel):
    backtest_years: list[int]
    validation_years: list[int] = []


class SnapshotReq(BaseModel):
    year: int
    game: str | None = None   # game doc filename (from the dropdown)


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return DASHBOARD.read_text(encoding="utf-8")


@app.get("/api/env")
def env():
    return {"deployed": DEPLOYED, "model": llm.active_model(),
            "platforms": PLATFORMS}


@app.get("/api/available-years")
def available_years():
    out = []
    for y in SUPPORTED_YEARS:
        ydir = Path(DATA_DIR) / str(y)
        files = [f for f in ydir.glob("*_data.json")] if ydir.exists() else []
        if files:
            out.append({"year": y, "files": len(files),
                        "platforms": [f.stem.replace("_data", "") for f in files]})
    return out


def _run_scrape_job(year: int):
    import importlib
    ys = str(year)
    with _lock:
        st = _scrape[ys]
        st.update(status="running", log=[])
        for p in PLATFORM_IDS:
            st["platforms"][p] = "pending"

    def log(line):
        with _lock:
            _scrape[ys]["log"].append(str(line))
            _scrape[ys]["log"] = _scrape[ys]["log"][-100:]

    for pid in PLATFORM_IDS:
        with _lock:
            _scrape[ys]["platforms"][pid] = "running"
        try:
            importlib.import_module(f"scrapers.{pid}").run(year=year, log=log)
            with _lock:
                _scrape[ys]["platforms"][pid] = "done"
        except Exception as e:
            log(f"[{pid}] error: {e}")
            with _lock:
                _scrape[ys]["platforms"][pid] = "error"
    with _lock:
        _scrape[ys]["status"] = "done"


@app.post("/api/scrape")
def start_scrape(req: ScrapeReq):
    if DEPLOYED:
        return JSONResponse(
            {"error": "Scraping is disabled on the deployed app. Run "
                      "`python scrape.py` locally and commit ai_engine/data/."},
            status_code=400)
    if req.year not in SUPPORTED_YEARS:
        return JSONResponse({"error": f"year must be one of {SUPPORTED_YEARS}"}, status_code=400)
    ys = str(req.year)
    with _lock:
        if _scrape[ys]["status"] == "running":
            return JSONResponse({"error": f"already scraping {req.year}"}, status_code=409)
    threading.Thread(target=_run_scrape_job, args=(req.year,), daemon=True).start()
    return {"status": "started", "year": req.year}


@app.get("/api/scrape/status")
def scrape_status(year: int | None = None):
    with _lock:
        if year is not None:
            return dict(_scrape.get(str(year), _blank(year)))
        return {y: dict(s) for y, s in _scrape.items()}


@app.post("/api/report")
def make_report(req: ReportReq):
    if not req.backtest_years:
        return JSONResponse({"error": "select at least one year"}, status_code=400)
    try:
        html = report.generate(req.backtest_years, req.validation_years)
        return {"html": html, "model": llm.active_model()}
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.get("/api/games")
def games():
    """List game design docs available in the games/ folder (for the dropdown)."""
    import os, snapshot
    return [{"file": os.path.basename(p), "name": snapshot.game_name(p)}
            for p in snapshot.list_games()]


@app.post("/api/snapshot")
def make_snapshot(req: SnapshotReq):
    """Analysis → game modifications → OpenAI-rendered snapshot of the modified game."""
    try:
        import snapshot
        return snapshot.generate_snapshot(req.year, req.game)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.get("/health")
def health():
    return {"ok": True, "deployed": DEPLOYED}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("\n" + "=" * 52)
    print("  AI MARKET INTELLIGENCE ENGINE")
    print(f"  open  http://localhost:{port}")
    print("=" * 52 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
