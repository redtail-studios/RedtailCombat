import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useDashboardAuth } from "@/lib/DashboardAuthContext";
import { useLoreReports } from "@/lib/LoreReportsContext";
import { downloadHtml, slug, escapeHtml } from "@/lib/loreReportUtils";

export const SCRAPE_YEARS = [2022, 2023, 2024, 2025, 2026];

function toggleYear(list, y) {
  return list.includes(y) ? list.filter((v) => v !== y) : [...list, y].sort((a, b) => a - b);
}

function useElapsed(active) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!active) { setElapsed(0); return; }
    const t0 = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(id);
  }, [active]);
  return elapsed;
}

// All the state + API wiring behind the real Lore console (scrape, market
// report, game analysis, redesign) — shared by the public /lore console and
// the dashboard-embedded Analyze page so both stay backed by one real
// implementation instead of two drifting copies.
export function useLoreConsole() {
  const { dashboardPassword } = useDashboardAuth();
  const { addReport, addPortfolioGame } = useLoreReports();
  const [searchParams] = useSearchParams();
  const [view, setView] = useState("console"); // 'console' | 'redesign'

  // ---- Step 1: data snapshot + scrape ----
  const [scrapedAt, setScrapedAt] = useState(null);
  const [availYears, setAvailYears] = useState([]);
  const [platforms, setPlatforms] = useState([]);
  const [scrapeYear, setScrapeYear] = useState(2026);
  const [scrapeStatus, setScrapeStatus] = useState({ status: "idle", platforms: {}, error: null });
  const [scrapeStarting, setScrapeStarting] = useState(false);
  const pollRef = useRef(null);

  const loadStatus = async () => {
    try {
      const d = await (await fetch("/api/lore/status")).json();
      setScrapedAt(d.scraped_at || "unknown");
      setAvailYears(Object.keys(d.years || {}).map(Number).sort((a, b) => a - b));
    } catch (e) {
      console.error("Failed to load Lore status", e);
    }
  };

  useEffect(() => {
    loadStatus();
    (async () => {
      try {
        const d = await (await fetch("/api/lore/env")).json();
        setPlatforms(d.platforms || []);
      } catch (e) { /* ignore */ }
    })();
  }, []);

  const pollScrape = async (year) => {
    clearTimeout(pollRef.current);
    try {
      const d = await (await fetch("/api/lore/scrape/status?year=" + year)).json();
      setScrapeStatus({ status: d.status || "idle", platforms: d.platforms || {}, error: d.error || null });
      if (d.status === "running") {
        pollRef.current = setTimeout(() => pollScrape(year), 1500);
      } else if (d.status === "done") {
        loadStatus();
      }
    } catch (e) { /* ignore */ }
  };

  useEffect(() => {
    pollScrape(scrapeYear);
    return () => clearTimeout(pollRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrapeYear]);

  const startScrape = async () => {
    setScrapeStarting(true);
    try {
      const r = await fetch("/api/lore/scrape", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year: scrapeYear, password: dashboardPassword }),
      });
      const d = await r.json();
      if (!r.ok || d.error) {
        setScrapeStatus((s) => ({ ...s, status: "error", error: d.error || "Failed to start" }));
      } else {
        pollScrape(scrapeYear);
      }
    } catch (e) {
      setScrapeStatus((s) => ({ ...s, status: "error", error: "Server error: " + e.message }));
    } finally {
      setScrapeStarting(false);
    }
  };

  const scrapeMeta = scrapeStatus.status === "running" ? `Scraping ${scrapeYear}…`
    : scrapeStatus.status === "done" ? `${scrapeYear} scrape complete`
    : scrapeStatus.status === "error" ? (scrapeStatus.error || `${scrapeYear} scrape failed`)
    : `Ready to scrape ${scrapeYear}`;

  // ---- Step 2 (market report) ----
  const [rMode, setRMode] = useState("analyse");
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") === "game" ? "game" : "market");
  const [analyseSel, setAnalyseSel] = useState([]);
  const [backSel, setBackSel] = useState([]);
  const [valSel, setValSel] = useState([]);
  const [rdYear, setRdYear] = useState(2026);
  const [reportState, setReportState] = useState({ status: "idle", html: null, error: null, label: "" });
  const reportElapsed = useElapsed(reportState.status === "loading");

  const btYears = rMode === "analyse" ? analyseSel : backSel;
  const repDisabled = btYears.length === 0;
  const repMeta = rMode === "analyse"
    ? (analyseSel.length ? `Analysing ${analyseSel.join(", ")}` : "Select at least one year")
    : (!backSel.length ? "Select backtest years" : !valSel.length ? `Backtest ${backSel.join(", ")} (add validation years)` : `Backtest ${backSel.join(", ")} → validate ${valSel.join(", ")}`);

  const genReport = async () => {
    const bt = rMode === "analyse" ? analyseSel : backSel;
    const val = rMode === "backtest" ? valSel : [];
    if (!bt.length) return;
    const year = bt[bt.length - 1];
    setRdYear(year);
    const label = val.length ? `backtest ${bt.join(", ")} → validate ${val.join(", ")}` : bt.join(", ");
    setReportState({ status: "loading", html: null, error: null, label });
    try {
      const r = await fetch("/api/lore/report", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backtest_years: bt, validation_years: val, password: dashboardPassword }),
      });
      const d = await r.json();
      if (!r.ok || d.error) setReportState({ status: "error", html: null, error: d.error || "error", label });
      else {
        setReportState({ status: "done", html: d.html, error: null, label });
        addReport({ type: "market", label, html: d.html, gameName: null });
      }
    } catch (e) {
      setReportState({ status: "error", html: null, error: e.message, label });
    }
  };

  // ---- Step 2 (analyse your own game) ----
  const [gameFile, setGameFile] = useState(null);
  const [gameSel, setGameSel] = useState([]);
  const [gameReportState, setGameReportState] = useState({ status: "idle", html: null, gameName: null, error: null, label: "" });
  const gameReportElapsed = useElapsed(gameReportState.status === "loading");
  const [redesignFile, setRedesignFile] = useState(null);

  const gameRepDisabled = !gameFile || gameSel.length === 0;
  const gameRepMeta = !gameFile ? "Upload a PDF" : (gameSel.length ? `Analysing your game against ${gameSel.join(", ")}` : "Select at least one year");

  const genGameReport = async () => {
    if (!gameFile || !gameSel.length) return;
    const year = gameSel[gameSel.length - 1];
    setRdYear(year);
    const label = gameSel.join(", ");
    setGameReportState({ status: "loading", html: null, gameName: null, error: null, label });
    try {
      const fd = new FormData();
      fd.append("file", gameFile); fd.append("years", gameSel.join(",")); fd.append("password", dashboardPassword);
      const r = await fetch("/api/lore/game-report", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || d.error) setGameReportState({ status: "error", html: null, gameName: null, error: d.error || "error", label });
      else {
        setGameReportState({ status: "done", html: d.html, gameName: d.game, error: null, label });
        setRedesignFile(gameFile);
        const reportId = addReport({ type: "game", label, html: d.html, gameName: d.game });
        addPortfolioGame({ name: d.game, lastYears: label, lastReportId: reportId });
      }
    } catch (e) {
      setGameReportState({ status: "error", html: null, gameName: null, error: e.message, label });
    }
  };

  const goRedesignFromGame = () => setView("redesign");

  // ---- Step 3: redesign ----
  const [redesignState, setRedesignState] = useState({ status: "idle", headline: null, modifications: [], error: null });
  const redesignElapsed = useElapsed(redesignState.status === "loading");

  const genRedesign = async () => {
    if (!redesignFile) return;
    setRedesignState({ status: "loading", headline: null, modifications: [], error: null });
    try {
      const fd = new FormData();
      fd.append("file", redesignFile); fd.append("year", rdYear); fd.append("password", dashboardPassword);
      const r = await fetch("/api/lore/snapshot", { method: "POST", body: fd });
      const d = await r.json();
      if (!r.ok || d.error) setRedesignState({ status: "error", headline: null, modifications: [], error: d.error || "error" });
      else setRedesignState({ status: "done", headline: d.headline || "", modifications: d.modifications || [], error: null });
    } catch (e) {
      setRedesignState({ status: "error", headline: null, modifications: [], error: e.message });
    }
  };

  const downloadRedesign = () => {
    if (redesignState.status !== "done") return;
    const feats = (redesignState.modifications || []).map((m, i) => `
      <div class="feat">
        ${m.image_b64 ? `<img src="data:image/png;base64,${m.image_b64}" style="max-width:100%;border-radius:8px;display:block;margin-bottom:12px">` : ""}
        <h3 style="color:#ff6b2b;margin:0 0 8px">${i + 1}. ${escapeHtml(m.change || "")}</h3>
        <p><b>Signal:</b> ${escapeHtml(m.finding || "")}</p>
        <p>${escapeHtml(m.why || "")}</p>
      </div>`).join("");
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${escapeHtml(redesignState.headline || "Lore Redesign")}</title>
<style>body{background:#0a0a0a;color:#e8e8e8;font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;line-height:1.6;max-width:900px;margin:0 auto;padding:40px 24px}
h1{color:#ff6b2b} .feat{background:#141414;border:1px solid #222;border-radius:12px;padding:20px;margin:16px 0}</style></head>
<body><h1>${escapeHtml(redesignState.headline || "")}</h1>${feats}</body></html>`;
    downloadHtml(html, `lore-redesign-${slug(redesignState.headline || rdYear)}.html`);
  };

  return {
    view, setView,
    // Step 1
    scrapedAt, availYears, platforms, scrapeYear, setScrapeYear, scrapeStatus, scrapeStarting, scrapeMeta, startScrape,
    // Step 2 — market report
    rMode, setRMode, activeTab, setActiveTab, analyseSel, backSel, valSel,
    onToggleAnalyse: (y) => setAnalyseSel((s) => toggleYear(s, y)),
    onToggleBack: (y) => setBackSel((s) => toggleYear(s, y)),
    onToggleVal: (y) => setValSel((s) => toggleYear(s, y)),
    repMeta, repDisabled,
    reportState: { ...reportState, elapsed: reportElapsed },
    genReport,
    downloadReport: () => downloadHtml(reportState.html, `lore-market-report-${slug(rdYear)}.html`),
    // Step 2 — analyse your game
    gameFile, setGameFile, gameSel,
    onToggleGame: (y) => setGameSel((s) => toggleYear(s, y)),
    gameRepMeta, gameRepDisabled,
    gameReportState: { ...gameReportState, elapsed: gameReportElapsed },
    genGameReport,
    downloadGameReport: () => downloadHtml(gameReportState.html, `lore-game-report-${slug(gameReportState.gameName)}.html`),
    goRedesignFromGame,
    // Step 3 — redesign
    rdYear, redesignFile, setRedesignFile,
    redesignState: { ...redesignState, elapsed: redesignElapsed },
    genRedesign, downloadRedesign,
  };
}
