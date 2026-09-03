import { createContext, useState, useContext } from 'react';

const DashboardAuthContext = createContext();

const VALID_USERNAME = 'lore';
const VALID_PASSWORD = 'redtaillore@2026';
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

  const dashboardLogin = (username, password) => {
    const isOwner = username === VALID_USERNAME && password === VALID_PASSWORD;
    const isGuest = username === GUEST_USERNAME && password === GUEST_PASSWORD && Date.now() < GUEST_EXPIRES;
    if (isOwner || isGuest) {
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
      value={{ dashboardUser, isDashboardAuthenticated, dashboardPassword, dashboardLogin, dashboardLogout }}
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
