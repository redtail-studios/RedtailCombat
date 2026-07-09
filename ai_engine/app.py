"""
app.py — FastAPI backend + dashboard.

Runs two ways:
  • Local:  python app.py   → full power (scrape + analyse + Claude report)
  • Vercel: imported by api/index.py → analyse committed data + Claude report
            (scraping is disabled on serverless; do it locally and commit data)
"""
import os
import json
import tempfile
import threading
import time
import uuid
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
REPORT_JOBS_DIR = Path(os.getenv("AI_ENGINE_JOBS_DIR", tempfile.gettempdir())) / "ai_engine_report_jobs"
REPORT_JOBS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_JOBS_DIR = Path(os.getenv("AI_ENGINE_JOBS_DIR", tempfile.gettempdir())) / "ai_engine_snapshot_jobs"
SNAPSHOT_JOBS_DIR.mkdir(parents=True, exist_ok=True)

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


def _report_job_path(job_id: str) -> Path:
    return REPORT_JOBS_DIR / f"{job_id}.json"


def _write_report_job(job_id: str, data: dict):
    data["updated_at"] = time.time()
    path = _report_job_path(job_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(path)


def _read_report_job(job_id: str) -> dict | None:
    if not job_id or not all(c in "0123456789abcdef-" for c in job_id.lower()):
        return None
    path = _report_job_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _run_report_job(job_id: str, backtest_years: list[int], validation_years: list[int]):
    try:
        _write_report_job(job_id, {
            "status": "running",
            "job_id": job_id,
            "backtest_years": backtest_years,
            "validation_years": validation_years,
            "created_at": time.time(),
        })
        html = report.generate(backtest_years, validation_years)
        _write_report_job(job_id, {
            "status": "done",
            "job_id": job_id,
            "html": html,
            "model": llm.active_model(),
            "backtest_years": backtest_years,
            "validation_years": validation_years,
            "created_at": time.time(),
        })
    except Exception as e:
        _write_report_job(job_id, {
            "status": "error",
            "job_id": job_id,
            "error": f"{type(e).__name__}: {e}",
            "backtest_years": backtest_years,
            "validation_years": validation_years,
            "created_at": time.time(),
        })


def _snapshot_job_path(job_id: str) -> Path:
    return SNAPSHOT_JOBS_DIR / f"{job_id}.json"


def _write_snapshot_job(job_id: str, data: dict):
    data["updated_at"] = time.time()
    path = _snapshot_job_path(job_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(path)


def _read_snapshot_job(job_id: str) -> dict | None:
    if not job_id or not all(c in "0123456789abcdef-" for c in job_id.lower()):
        return None
    path = _snapshot_job_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _run_snapshot_job(job_id: str, year: int, game: str | None):
    try:
        import snapshot
        _write_snapshot_job(job_id, {
            "status": "running",
            "job_id": job_id,
            "year": year,
            "game_file": game,
            "created_at": time.time(),
        })
        result = snapshot.generate_snapshot(year, game)
        result.update({"status": "done", "job_id": job_id})
        _write_snapshot_job(job_id, result)
    except Exception as e:
        _write_snapshot_job(job_id, {
            "status": "error",
            "job_id": job_id,
            "error": f"{type(e).__name__}: {e}",
            "year": year,
            "game_file": game,
            "created_at": time.time(),
        })


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
    job_id = str(uuid.uuid4())
    backtest_years = list(req.backtest_years)
    validation_years = list(req.validation_years)
    _write_report_job(job_id, {
        "status": "queued",
        "job_id": job_id,
        "backtest_years": backtest_years,
        "validation_years": validation_years,
        "created_at": time.time(),
    })
    threading.Thread(
        target=_run_report_job,
        args=(job_id, backtest_years, validation_years),
        daemon=True,
    ).start()
    return JSONResponse({"status": "queued", "job_id": job_id}, status_code=202)


@app.get("/api/report/status")
def report_status(job_id: str):
    job = _read_report_job(job_id)
    if not job:
        return JSONResponse({"error": "report job not found"}, status_code=404)
    return job


@app.get("/api/games")
def games():
    """List game design docs available in the games/ folder (for the dropdown)."""
    import os, snapshot
    return [{"file": os.path.basename(p), "name": snapshot.game_name(p)}
            for p in snapshot.list_games()]


@app.post("/api/snapshot")
def make_snapshot(req: SnapshotReq):
    """Analysis → game modifications → OpenAI-rendered snapshot of the modified game."""
    job_id = str(uuid.uuid4())
    _write_snapshot_job(job_id, {
        "status": "queued",
        "job_id": job_id,
        "year": req.year,
        "game_file": req.game,
        "created_at": time.time(),
    })
    threading.Thread(
        target=_run_snapshot_job,
        args=(job_id, req.year, req.game),
        daemon=True,
    ).start()
    return JSONResponse({"status": "queued", "job_id": job_id}, status_code=202)


@app.get("/api/snapshot/status")
def snapshot_status(job_id: str):
    job = _read_snapshot_job(job_id)
    if not job:
        return JSONResponse({"error": "snapshot job not found"}, status_code=404)
    return job


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
