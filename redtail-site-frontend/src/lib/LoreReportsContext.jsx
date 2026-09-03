import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useDashboardAuth } from "@/lib/DashboardAuthContext";

const LoreReportsContext = createContext();
const MAX_STORED = 20;
// One-time migration source: before this was per-user + backend-backed, a
// single browser-wide localStorage key held everyone's reports.
const LEGACY_KEY = "lore_reports";

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const LoreReportsProvider = ({ children }) => {
  const { dashboardUser, dashboardPassword, isDashboardAuthenticated } = useDashboardAuth();
  const username = dashboardUser?.username || null;

  const [reports, setReports] = useState([]);
  const [portfolio, setPortfolio] = useState([]);
  const [loaded, setLoaded] = useState(false);
  // Refs mirror state synchronously so two mutations in the same tick (e.g.
  // addReport then addPortfolioGame after a game report finishes) always
  // persist each other's latest value instead of a stale render-time closure.
  const reportsRef = useRef([]);
  const portfolioRef = useRef([]);

  const persist = (nextReports, nextPortfolio) => {
    if (!username || !dashboardPassword) return;
    fetch('/api/lore/user-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: dashboardPassword, reports: nextReports, portfolio: nextPortfolio }),
    }).catch(() => { /* best-effort — local state already reflects the change */ });
  };

  // Hydrate from the backend whenever the logged-in user changes (login,
  // logout, or switching from 'lore' to 'guest' or back).
  useEffect(() => {
    if (!isDashboardAuthenticated || !username || !dashboardPassword) {
      reportsRef.current = []; portfolioRef.current = [];
      setReports([]); setPortfolio([]); setLoaded(false);
      return;
    }
    let cancelled = false;
    setLoaded(false);
    fetch(`/api/lore/user-data?username=${encodeURIComponent(username)}&password=${encodeURIComponent(dashboardPassword)}`)
      .then((r) => r.json())
      .then(async (d) => {
        if (cancelled) return;
        let nextReports = d.reports || [];
        let nextPortfolio = d.portfolio || [];

        // One-time migration for the primary account: fold in whatever was
        // previously saved browser-side under the old unscoped key.
        if (username === 'lore' && nextReports.length === 0 && nextPortfolio.length === 0) {
          try {
            const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || '[]');
            if (Array.isArray(legacy) && legacy.length) {
              nextReports = legacy.slice(0, MAX_STORED);
              localStorage.removeItem(LEGACY_KEY);
              persist(nextReports, nextPortfolio);
            }
          } catch { /* ignore malformed legacy data */ }
        }

        reportsRef.current = nextReports;
        portfolioRef.current = nextPortfolio;
        setReports(nextReports);
        setPortfolio(nextPortfolio);
        setLoaded(true);
      })
      .catch(() => { if (!cancelled) setLoaded(true); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username, dashboardPassword, isDashboardAuthenticated]);

  const addReport = (report) => {
    const entry = { id: makeId(), createdAt: new Date().toISOString(), ...report };
    const next = [entry, ...reportsRef.current].slice(0, MAX_STORED);
    reportsRef.current = next;
    setReports(next);
    persist(next, portfolioRef.current);
    return entry.id;
  };

  const removeReport = (id) => {
    const next = reportsRef.current.filter((r) => r.id !== id);
    reportsRef.current = next;
    setReports(next);
    persist(next, portfolioRef.current);
  };

  // Adds a game to the portfolio, or updates its existing entry (by name) —
  // re-analysing the same game refreshes it rather than duplicating it.
  const addPortfolioGame = (game) => {
    const prev = portfolioRef.current;
    const existing = prev.find((g) => g.name === game.name);
    const next = existing
      ? prev.map((g) => (g.name === game.name ? { ...g, ...game, updatedAt: new Date().toISOString() } : g))
      : [{ id: makeId(), addedAt: new Date().toISOString(), ...game }, ...prev];
    portfolioRef.current = next;
    setPortfolio(next);
    persist(reportsRef.current, next);
  };

  const removePortfolioGame = (id) => {
    const next = portfolioRef.current.filter((g) => g.id !== id);
    portfolioRef.current = next;
    setPortfolio(next);
    persist(reportsRef.current, next);
  };

  return (
    <LoreReportsContext.Provider value={{ reports, addReport, removeReport, portfolio, addPortfolioGame, removePortfolioGame, loaded }}>
      {children}
    </LoreReportsContext.Provider>
  );
};

export const useLoreReports = () => {
  const ctx = useContext(LoreReportsContext);
  if (!ctx) throw new Error("useLoreReports must be used within LoreReportsProvider");
  return ctx;
};
