import { createContext, useState, useContext, useEffect } from 'react';

const DashboardAuthContext = createContext();

const VALID_USERNAME = 'lore';
const VALID_PASSWORD = 'redtaillore@2026';
// Second permanent account (co-founders) — mirrors server.py's
// ADMIN_PASSWORD. Same full access as the owner login, separate credential.
const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'redtailadmin@2026';
// Third permanent account (Dakota) — mirrors server.py's DAKOTA_PASSWORD.
// Same full access, own credential, own isolated portfolio/reports (data is
// scoped per-username, same as every other account here).
const DAKOTA_USERNAME = 'dakota';
const DAKOTA_PASSWORD = 'dakotaredtail@2026';
// Fourth permanent account (Andres Sevilla) — mirrors server.py's
// ANDRES_PASSWORD. Same full access, own credential, own isolated data.
const ANDRES_USERNAME = 'andres';
const ANDRES_PASSWORD = 'andresredtail@2026';
// External partner account (Caravela Capital) — mirrors server.py's
// CARAVELA_PASSWORD. Same full access, own credential, own isolated data.
const CARAVELA_USERNAME = 'caravelacapital';
const CARAVELA_PASSWORD = '7ghlZU1IB9hOo1JzyveK';
// Personal demo/preview account (Amritha) — mirrors server.py's
// AMRITHA_PASSWORD. Same full access, own credential, own isolated data.
const AMRITHA_USERNAME = 'amritha';
const AMRITHA_PASSWORD = 'amritha';
// External partner accounts (Cometa, Newtopia) — mirror server.py's
// COMETA_PASSWORD/NEWTOPIA_PASSWORD. Same full access, own credential, own
// isolated data.
const COMETA_USERNAME = 'cometa';
const COMETA_PASSWORD = 'redt@ilcometa2026';
const NEWTOPIA_USERNAME = 'newtopia';
const NEWTOPIA_PASSWORD = 'redt@ilnewtopia2026';
// Personal demo/preview accounts (Mauricio, Santi) — mirror server.py's
// MAURICIO_PASSWORD/SANTI_PASSWORD. Same full access, own credential, own
// isolated data.
const MAURICIO_USERNAME = 'mauricio';
const MAURICIO_PASSWORD = 'redt@ilmauricio2026';
const SANTI_USERNAME = 'santi';
const SANTI_PASSWORD = 'redt@ilsanti2026';
// Personal demo/preview accounts (Daniel Stein, Andres Sevilla) — mirror
// server.py's DANIELSTEIN_PASSWORD/ANDRESSEVILLA_PASSWORD. Same full access,
// own credential, own isolated data. 'andressevilla' is a second, separate
// login for Andres Sevilla alongside the existing 'andres' account above.
const DANIELSTEIN_USERNAME = 'danielstein';
const DANIELSTEIN_PASSWORD = 'redt@ildanielstein@2026';
const ANDRESSEVILLA_USERNAME = 'andressevilla';
const ANDRESSEVILLA_PASSWORD = 'redt@ilandressevilla@2026';
// Time-boxed guest login — mirrors server.py's GUEST_PASSWORD/GUEST_EXPIRES
// (LORE_GUEST_EXPIRES in .env). Keep these two in sync — the server is the
// real gate, this just avoids a round-trip for an obviously-expired guess.
const GUEST_USERNAME = 'guest';
const GUEST_PASSWORD = 'loreguest@2026';
const GUEST_EXPIRES = new Date('2027-12-31T23:59:59Z').getTime();

function readStoredSession() {
  const stored = localStorage.getItem('dashboard_auth');
  const storedUser = localStorage.getItem('dashboard_auth_user');
  const storedPw = localStorage.getItem('dashboard_auth_pw');
  // Guest sessions expire on their own — don't restore a stale one.
  if (stored === 'true' && !(storedUser === GUEST_USERNAME && Date.now() >= GUEST_EXPIRES)) {
    return { authenticated: true, username: storedUser || 'lore', password: storedPw || null };
  }
  return { authenticated: false, username: null, password: null };
}

export const DashboardAuthProvider = ({ children }) => {
  // Lazy initializers run synchronously on first render, so a page that
  // mounts straight into a protected route (e.g. a hard refresh on
  // /dashboard) sees the restored session immediately — not one render late.
  const initial = readStoredSession();
  const [dashboardUser, setDashboardUser] = useState(initial.authenticated ? { username: initial.username } : null);
  const [isDashboardAuthenticated, setIsDashboardAuthenticated] = useState(initial.authenticated);
  // The backend has no session token — it re-checks this password on every
  // mutating Lore API call, so we keep it around after login (and restore it
  // on reload, same trust level as the plaintext password already sent with
  // every request).
  const [dashboardPassword, setDashboardPassword] = useState(initial.password);
  // Whether this account can see the admin panel (manage every account).
  // Determined by asking the backend — the real admin-tier check lives there
  // (lore, admin only, see accounts.is_admin) — rather than hardcoding a
  // username list here, so a future admin-tier account created through the
  // panel itself gets the nav link with no frontend change needed.
  const [isAdminUser, setIsAdminUser] = useState(false);
  useEffect(() => {
    if (!dashboardUser?.username || !dashboardPassword) { setIsAdminUser(false); return; }
    let cancelled = false;
    fetch('/api/lore/admin/accounts/list', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: dashboardUser.username, password: dashboardPassword }),
    })
      .then(r => { if (!cancelled) setIsAdminUser(r.ok); })
      .catch(() => { if (!cancelled) setIsAdminUser(false); });
    return () => { cancelled = true; };
  }, [dashboardUser?.username, dashboardPassword]);

  const dashboardLogin = (username, password) => {
    const isOwner = username === VALID_USERNAME && password === VALID_PASSWORD;
    const isAdmin = username === ADMIN_USERNAME && password === ADMIN_PASSWORD;
    const isDakota = username === DAKOTA_USERNAME && password === DAKOTA_PASSWORD;
    const isAndres = username === ANDRES_USERNAME && password === ANDRES_PASSWORD;
    const isCaravela = username === CARAVELA_USERNAME && password === CARAVELA_PASSWORD;
    const isAmritha = username === AMRITHA_USERNAME && password === AMRITHA_PASSWORD;
    const isCometa = username === COMETA_USERNAME && password === COMETA_PASSWORD;
    const isNewtopia = username === NEWTOPIA_USERNAME && password === NEWTOPIA_PASSWORD;
    const isMauricio = username === MAURICIO_USERNAME && password === MAURICIO_PASSWORD;
    const isSanti = username === SANTI_USERNAME && password === SANTI_PASSWORD;
    const isDanielStein = username === DANIELSTEIN_USERNAME && password === DANIELSTEIN_PASSWORD;
    const isAndresSevilla = username === ANDRESSEVILLA_USERNAME && password === ANDRESSEVILLA_PASSWORD;
    const isGuest = username === GUEST_USERNAME && password === GUEST_PASSWORD && Date.now() < GUEST_EXPIRES;
    if (isOwner || isAdmin || isDakota || isAndres || isCaravela || isAmritha || isCometa || isNewtopia || isMauricio || isSanti || isDanielStein || isAndresSevilla || isGuest) {
      localStorage.setItem('dashboard_auth', 'true');
      localStorage.setItem('dashboard_auth_user', username);
      localStorage.setItem('dashboard_auth_pw', password);
      setDashboardUser({ username });
      setIsDashboardAuthenticated(true);
      setDashboardPassword(password);
      return { success: true };
    }
    return { success: false, error: 'Invalid username or password' };
  };

  const dashboardLogout = () => {
    localStorage.removeItem('dashboard_auth');
    localStorage.removeItem('dashboard_auth_user');
    localStorage.removeItem('dashboard_auth_pw');
    setDashboardUser(null);
    setIsDashboardAuthenticated(false);
    setDashboardPassword(null);
  };

  return (
    <DashboardAuthContext.Provider
      value={{ dashboardUser, isDashboardAuthenticated, dashboardPassword, dashboardLogin, dashboardLogout, isAdminUser }}
    >
      {children}
    </DashboardAuthContext.Provider>
  );
};

export const useDashboardAuth = () => {
  const context = useContext(DashboardAuthContext);
  if (!context) {
    throw new Error('useDashboardAuth must be used within DashboardAuthProvider');
  }
  return context;
};
