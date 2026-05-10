"""
server.py — Redtail Intelligence Dashboard
Run: python server.py
Open: http://localhost:8000
"""
import json
import os
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()  # picks up ANTHROPIC_API_KEY from .env if present

SCRAPER_DIR    = Path(__file__).parent / "scraper"
DASHBOARD_PATH = Path(__file__).parent / "dashboard.html"
REPORT_FILE    = Path("/tmp/redtail_report.html")   # Claude Code writes here

# Add scraper to path so we can import analysis + claude_report directly
sys.path.insert(0, str(SCRAPER_DIR))

app = FastAPI(title="Redtail Intelligence Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PLATFORM_IDS = ["reddit", "steam", "googleplay", "appstore", "forbes", "toucharcade", "pocketgamer"]
SUPPORTED_YEARS = [2022, 2023, 2024, 2025]

# ── Global state ───────────────────────────────────────────────────────────────
_lock = threading.Lock()

def _blank_year_state():
    return {
        "status": "idle",
        "platforms": {p: "idle" for p in PLATFORM_IDS},
        "log": [],
        "started_at": None,
        "finished_at": None,
    }

_scrape_state: dict[str, dict] = {str(y): _blank_year_state() for y in SUPPORTED_YEARS}
_report_state = {"status": "idle", "started_at": None, "finished_at": None, "error": None}
_latest_report_html: str | None = None


def _update_platform(year_str: str, platform: str, status: str):
    with _lock:
        if year_str in _scrape_state and platform in _scrape_state[year_str]["platforms"]:
            _scrape_state[year_str]["platforms"][platform] = status


def _run_scraping_job(year: int):
    year_str = str(year)
    with _lock:
        _scrape_state[year_str]["status"] = "running"
        _scrape_state[year_str]["started_at"] = datetime.now().isoformat()
        _scrape_state[year_str]["log"] = []
        for p in PLATFORM_IDS:
            _scrape_state[year_str]["platforms"][p] = "pending"

    try:
        cmd = [sys.executable, "main.py", "--scrape-only", "--year", str(year)]
        proc = subprocess.Popen(
            cmd,
            cwd=str(SCRAPER_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for raw in proc.stdout:
            line = raw.rstrip()
            with _lock:
                _scrape_state[year_str]["log"].append(line)
            if line.startswith("STATUS:"):
                parts = line.split(":", 2)
                if len(parts) == 3:
                    _update_platform(year_str, parts[1], parts[2])

        proc.wait()
        final = "done" if proc.returncode == 0 else "error"
        with _lock:
            _scrape_state[year_str]["status"] = final
            _scrape_state[year_str]["finished_at"] = datetime.now().isoformat()

    except Exception as exc:
        with _lock:
            _scrape_state[year_str]["status"] = "error"
            _scrape_state[year_str]["log"].append(str(exc))
            _scrape_state[year_str]["finished_at"] = datetime.now().isoformat()


# ── Request models ─────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    year: int

class ReportRequest(BaseModel):
    backtest_years:   list[int]
    validation_years: list[int] = []


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_PATH.read_text()


@app.get("/api/available-years")
def available_years():
    """Return years that have scraped data files."""
    from config import DATA_DIR
    years = []
    for year in SUPPORTED_YEARS:
        year_dir = Path(DATA_DIR) / str(year)
        if year_dir.exists():
            files = list(year_dir.glob("*.json"))
            # Exclude analysis_results.json when counting data files
            data_files = [f for f in files if f.name != "analysis_results.json"]
            if data_files:
                years.append({
                    "year": year,
                    "files": len(data_files),
                    "platforms": [f.stem.replace("_data", "") for f in data_files],
                })
    return years


@app.post("/api/scrape")
def start_scrape(req: ScrapeRequest):
    year     = req.year
    year_str = str(year)
    if year not in SUPPORTED_YEARS:
        return JSONResponse({"error": f"Year must be one of {SUPPORTED_YEARS}"}, status_code=400)
    with _lock:
        if _scrape_state[year_str]["status"] == "running":
            return JSONResponse({"error": f"Already scraping {year}"}, status_code=409)
    threading.Thread(target=_run_scraping_job, args=(year,), daemon=True).start()
    return {"status": "started", "year": year}


@app.get("/api/scrape/status")
def get_scrape_status(year: int = None):
    with _lock:
        if year:
            return dict(_scrape_state.get(str(year), _blank_year_state()))
        return {y: dict(s) for y, s in _scrape_state.items()}


def _run_report_job(backtest_years: list, validation_years: list):
    """Background thread: run analysis + LLM generation, update _report_state."""
    global _latest_report_html

    from analysis.sentiment import run as analysis_run, extract_quotes
    from report.claude_report import generate_report_html
    from config import get_year_dir

    try:
        analysis_by_year: dict = {}
        quotes_by_year:   dict = {}

        all_years = list(set(backtest_years + validation_years))
        for year in all_years:
            data_dir = str(get_year_dir(year))
            print(f"[server] Analysing {year} from {data_dir}")
            try:
                a = analysis_run(data_dir=data_dir)
                analysis_by_year[str(year)] = a
                quotes_by_year[str(year)]   = extract_quotes(data_dir=data_dir, n=25)
            except Exception as e:
                print(f"[server] Analysis error {year}: {e}")
                analysis_by_year[str(year)] = {}
                quotes_by_year[str(year)]   = []

        html = generate_report_html(
            backtest_years   = backtest_years,
            validation_years = validation_years,
            analysis_by_year = analysis_by_year,
            quotes_by_year   = quotes_by_year,
        )

        _latest_report_html = html
        REPORT_FILE.write_text(html)   # persist so it survives server restarts
        with _lock:
            _report_state["status"]      = "done"
            _report_state["finished_at"] = datetime.now().isoformat()
        print("[server] Report generation complete.")

    except Exception as exc:
        print(f"[server] Report generation failed: {exc}")
        with _lock:
            _report_state["status"]      = "error"
            _report_state["error"]       = str(exc)
            _report_state["finished_at"] = datetime.now().isoformat()


@app.post("/api/report")
def generate_report(req: ReportRequest):
    """Start report generation in background; return immediately so the browser doesn't hang."""
    if not req.backtest_years:
        return JSONResponse({"error": "Select at least one year to analyse"}, status_code=400)

    with _lock:
        if _report_state["status"] == "running":
            return JSONResponse({"error": "Report already generating"}, status_code=409)
        _report_state["status"]      = "running"
        _report_state["started_at"] = datetime.now().isoformat()
        _report_state["error"]       = None
        _report_state["finished_at"] = None

    threading.Thread(
        target=_run_report_job,
        args=(req.backtest_years, req.validation_years),
        daemon=True,
    ).start()

    return {"status": "started"}  # instant response — dashboard polls /api/report/status


@app.get("/api/report/html", response_class=HTMLResponse)
def get_report_html():
    # In-memory report (from API generation) takes priority
    if _latest_report_html is not None:
        return HTMLResponse(_latest_report_html)
    # Fall back to file written by Claude Code in this terminal
    if REPORT_FILE.exists():
        return HTMLResponse(REPORT_FILE.read_text())
    return HTMLResponse(
        "<body style='background:#0a0a0a;color:#555;font-family:sans-serif;"
        "display:flex;align-items:center;justify-content:center;height:100vh;"
        "margin:0;font-size:14px'>No report yet — select years and click Generate Report</body>"
    )


@app.get("/api/report/status")
def get_report_status():
    with _lock:
        return dict(_report_state)


@app.get("/api/test-claude")
def test_claude():
    """Smoke-test: verify the claude CLI responds to a trivial prompt."""
    import shutil, subprocess
    claude_path = shutil.which("claude")
    if not claude_path:
        return JSONResponse({"ok": False, "error": "claude not found on PATH"}, status_code=500)

    print("[server] Testing claude CLI with a short prompt...")
    try:
        r = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", "Say the single word: HELLO"],
            capture_output=True, text=True, timeout=60, cwd="/tmp",
        )
        print(f"[server] test returncode={r.returncode}")
        print(f"[server] test stdout={repr(r.stdout[:300])}")
        print(f"[server] test stderr={repr(r.stderr[:300])}")
        return {
            "ok": bool(r.stdout.strip()) and r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout[:500],
            "stderr": r.stderr[:500],
            "claude_path": claude_path,
        }
    except subprocess.TimeoutExpired:
        return JSONResponse({"ok": False, "error": "claude timed out (60s)"}, status_code=500)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 52)
    print("  REDTAIL INTELLIGENCE DASHBOARD")
    print("  Open  http://localhost:8000  in your browser")
    print("=" * 52 + "\n")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
