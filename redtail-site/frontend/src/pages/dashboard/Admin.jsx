import React, { useEffect, useState, useCallback } from 'react';
import { ShieldCheck, Plus, Copy, Check, Loader2, Lock } from 'lucide-react';
import { useDashboardAuth } from '@/lib/DashboardAuthContext';

function usernameFor(name) {
  return (name || '').toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 32);
}
function passwordFor(username) {
  return username ? `redt@il${username}@2026` : '';
}

function CopyButton({ value }) {
  const [copied, setCopied] = useState(false);
  if (!value) return null;
  return (
    <button
      type="button"
      title="Copy"
      onClick={async () => {
        try { await navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard unavailable */ }
      }}
      className="text-platinum/30 hover:text-platinum transition-colors flex-shrink-0"
    >
      {copied ? <Check className="w-3 h-3 text-moss" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

export default function Admin() {
  const { dashboardUser, dashboardPassword, isAdminUser } = useDashboardAuth();
  const [accounts, setAccounts] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [unauthorized, setUnauthorized] = useState(false);

  const [displayName, setDisplayName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [tier, setTier] = useState('member');
  const [usernameTouched, setUsernameTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [created, setCreated] = useState(null);

  const load = useCallback(async () => {
    setLoadError('');
    try {
      const r = await fetch('/api/lore/admin/accounts/list', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: dashboardUser.username, password: dashboardPassword }),
      });
      if (r.status === 401) { setUnauthorized(true); return; }
      const d = await r.json().catch(() => null);
      if (!r.ok || !d) throw new Error('Could not load accounts.');
      setAccounts(d.accounts);
    } catch (e) {
      setLoadError(e.message || 'Could not load accounts.');
    }
  }, [dashboardUser?.username, dashboardPassword]);

  useEffect(() => { if (dashboardUser?.username && dashboardPassword) load(); }, [load, dashboardUser?.username, dashboardPassword]);

  const onNameChange = (value) => {
    setDisplayName(value);
    if (!usernameTouched) setUsername(usernameFor(value));
  };
  useEffect(() => {
    if (!passwordTouched) setPassword(passwordFor(username));
  }, [username, passwordTouched]);

  const resetForm = () => {
    setDisplayName(''); setUsername(''); setPassword(''); setTier('member');
    setUsernameTouched(false); setPasswordTouched(false);
  };

  const submit = async (e) => {
    e.preventDefault();
    setCreateError(''); setCreated(null); setCreating(true);
    try {
      const r = await fetch('/api/lore/admin/accounts/create', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          adminUsername: dashboardUser.username, adminPassword: dashboardPassword,
          username, password, displayName, tier,
        }),
      });
      const d = await r.json().catch(() => null);
      if (!r.ok || !d || d.error) throw new Error(d?.error || 'Could not create this account.');
      setCreated(d.account);
      resetForm();
      load();
    } catch (e) {
      setCreateError(e.message || 'Could not create this account.');
    } finally {
      setCreating(false);
    }
  };

  if (unauthorized) {
    return (
      <div className="px-6 py-6 max-w-2xl mx-auto text-center">
        <Lock className="w-5 h-5 text-platinum/20 mx-auto mb-3" />
        <p className="font-mono text-xs text-platinum/40">You don't have access to this page. Only admin-tier accounts can manage logins.</p>
      </div>
    );
  }

  return (
    <div className="px-6 py-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-2 mb-2">
        <ShieldCheck className="w-3.5 h-3.5 text-pulse" />
        <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Admin only</span>
      </div>
      <h1 className="font-pixel text-base text-platinum mb-2">Team logins</h1>
      <p className="font-mono text-xs text-platinum/40 mb-6">
        Create and view dashboard logins without needing a code deploy. Each account's data (reports, portfolio) is fully isolated.
      </p>

      <form onSubmit={submit} className="bg-panel border border-white/5 p-4 pixel-clip-sm mb-6 space-y-3">
        <div className="flex items-center gap-2 mb-1">
          <Plus className="w-3.5 h-3.5 text-moss" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">New account</span>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 block mb-1">Full name</span>
            <input value={displayName} onChange={e => onNameChange(e.target.value)} placeholder="Jordan Lee"
              className="w-full bg-ink border border-white/10 px-3 py-2 font-mono text-xs text-platinum focus:border-moss/50 outline-none" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 block mb-1">Access level</span>
            <select value={tier} onChange={e => setTier(e.target.value)}
              className="w-full bg-ink border border-white/10 px-3 py-2 font-mono text-xs text-platinum focus:border-moss/50 outline-none">
              <option value="member">Member — own data only</option>
              <option value="admin">Admin — can manage all logins</option>
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 block mb-1">Username</span>
            <input value={username} onChange={e => { setUsername(usernameFor(e.target.value)); setUsernameTouched(true); }} placeholder="jordanlee"
              className="w-full bg-ink border border-white/10 px-3 py-2 font-mono text-xs text-platinum focus:border-moss/50 outline-none" />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 block mb-1">Password</span>
            <input value={password} onChange={e => { setPassword(e.target.value); setPasswordTouched(true); }} placeholder="redt@iljordanlee@2026"
              className="w-full bg-ink border border-white/10 px-3 py-2 font-mono text-xs text-platinum focus:border-moss/50 outline-none" />
          </label>
        </div>
        {createError && <p role="alert" className="font-mono text-xs text-pulse">{createError}</p>}
        {created && <p role="status" className="font-mono text-xs text-moss">Created "{created.username}" — share the username and password above with them directly.</p>}
        <button type="submit" disabled={creating || !username || !password}
          className="flex items-center gap-2 px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 disabled:opacity-30 disabled:pointer-events-none transition-opacity pixel-clip-sm">
          {creating ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Creating…</> : 'Create account'}
        </button>
      </form>

      {loadError && <p role="alert" className="font-mono text-xs text-pulse mb-4">{loadError}</p>}
      {!accounts && !loadError && <p className="font-mono text-xs text-platinum/40">Loading accounts…</p>}
      {accounts && (
        <div className="bg-panel border border-white/5 pixel-clip-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 px-4 py-3">Name</th>
                  <th className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 px-4 py-3">Username</th>
                  <th className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 px-4 py-3">Password</th>
                  <th className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 px-4 py-3">Access</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map(a => (
                  <tr key={a.username} className="border-b border-white/5 last:border-0">
                    <td className="font-mono text-xs text-platinum px-4 py-3 whitespace-nowrap">{a.displayName}</td>
                    <td className="font-mono text-xs text-platinum/70 px-4 py-3"><span className="flex items-center gap-2">{a.username}<CopyButton value={a.username} /></span></td>
                    <td className="font-mono text-xs text-platinum/70 px-4 py-3"><span className="flex items-center gap-2">{a.password}<CopyButton value={a.password} /></span></td>
                    <td className="font-mono text-xs px-4 py-3">
                      <span className={a.tier === 'admin' ? 'text-pulse' : 'text-platinum/50'}>{a.tier === 'admin' ? 'Admin' : 'Member'}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
