import React from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDashboardAuth } from '@/lib/DashboardAuthContext';
import { useLoreReports } from '@/lib/LoreReportsContext';
import { TrendingUp, Briefcase, Bell, FileText, CreditCard, Settings, LogOut, ChevronDown, User } from 'lucide-react';
import { LOGO_URL } from '@/lib/teamData';
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

// Market trends (real Google Trends + news, /api/lore/market-snapshot),
// Analyze (the real Lore console — market/game report + redesign), Portfolio
// (real, per-user, backend-persisted), and Reports (real generated Lore
// reports) are wired to real data now — only Updates/Billing/Settings are
// still Base44's fabricated-data scaffolding.
const REAL_DATA_PATHS = ['/dashboard', '/dashboard/analyze', '/dashboard/portfolio', '/dashboard/reports'];

const NAV_SECTIONS = [
  {
    label: 'STUDIO',
    items: [
      { to: '/dashboard', label: 'Market trends', icon: TrendingUp, end: true, badge: null },
      { to: '/dashboard/portfolio', label: 'Portfolio', icon: Briefcase, badge: '0' },
      { to: '/dashboard/updates', label: 'Updates', icon: Bell, badge: '0' },
      { to: '/dashboard/reports', label: 'Reports', icon: FileText, badge: null },
    ],
  },
  {
    label: 'ACCOUNT',
    items: [
      { to: '/dashboard/billing', label: 'Billing', icon: CreditCard, badge: null },
      { to: '/dashboard/settings', label: 'Settings', icon: Settings, badge: null },
    ],
  },
];

export default function DashboardLayout() {
  const { dashboardUser, dashboardLogout } = useDashboardAuth();
  const { portfolio } = useLoreReports();
  const navigate = useNavigate();
  const location = useLocation();
  const isRealDataPage = REAL_DATA_PATHS.includes(location.pathname);
  const badgeFor = (item) => (item.to === '/dashboard/portfolio' ? String(portfolio.length) : item.badge);

  const handleLogout = () => {
    dashboardLogout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-ink">
      {/* Sidebar */}
      <aside className="flex flex-col flex-shrink-0 w-60 h-full border-r border-white/5 bg-ink">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <img src={LOGO_URL} alt="Redtail" className="h-8 w-8 object-contain drop-shadow-[0_0_10px_rgba(255,46,46,0.4)]" />
            <div>
              <div className="font-pixel text-[10px] tracking-wider text-platinum">
                RED<span className="text-pulse">TAIL</span>
              </div>
              <div className="font-mono text-[8px] uppercase tracking-widest text-platinum/40 mt-0.5">
                LORE
              </div>
            </div>
          </div>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 overflow-y-auto py-4">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="mb-5">
              <div className="px-4 mb-2 font-pixel text-[7px] uppercase tracking-widest text-platinum/30">
                {section.label}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-4 py-2.5 font-mono text-xs transition-colors ${
                        isActive ? 'text-pulse' : 'text-platinum/50 hover:text-platinum'
                      }`
                    }
                    style={({ isActive }) => ({
                      borderLeft: isActive ? '2px solid #FF2E2E' : '2px solid transparent',
                      background: isActive ? 'rgba(255,46,46,0.06)' : 'transparent',
                    })}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="flex-1">{item.label}</span>
                    {badgeFor(item) !== null && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-platinum/60 font-mono">
                        {badgeFor(item)}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Profile / logout */}
        <div className="px-4 py-3 border-t border-white/5">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-3 w-full text-left hover:bg-white/5 -mx-1 px-1 py-1 rounded-sm transition-colors">
                <div className="flex items-center justify-center w-7 h-7 pixel-clip-sm bg-pulse/15 font-pixel text-[8px] text-pulse flex-shrink-0">
                  {dashboardUser?.username?.charAt(0).toUpperCase() || 'L'}
                </div>
                <span className="font-mono text-xs text-platinum/60 flex-1 truncate">
                  {dashboardUser?.username || 'lore'}
                </span>
                <ChevronDown className="w-3 h-3 text-platinum/30 flex-shrink-0" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              side="top"
              align="start"
              className="w-52 bg-panel border-white/10 text-platinum rounded-none pixel-clip-sm"
            >
              <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-wider text-platinum/40">
                Signed in as <span className="text-platinum">{dashboardUser?.username}</span>
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/10" />
              <DropdownMenuItem
                onClick={handleLogout}
                className="font-mono text-xs text-platinum/80 focus:bg-pulse/10 focus:text-pulse cursor-pointer"
              >
                <LogOut className="w-3.5 h-3.5 mr-2" /> Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top header */}
        <header className="flex-shrink-0">
          {/* Alert banner */}
          {!isRealDataPage && (
            <div className="px-6 py-1.5 font-mono text-[10px] text-center text-moss/70 border-b border-moss/10 bg-moss/5">
              Mockup only — all data below is fabricated for preview. Nothing here is real market data.
            </div>
          )}

          {/* Header row */}
          <div className="flex items-center justify-between px-6 py-3 border-b border-white/5 bg-ink">
            <span className="font-mono text-[10px] px-3 py-1 rounded-full bg-pulse/10 text-pulse border border-pulse/20">
              0 signals need review
            </span>
            <div className="flex items-center gap-3">
              <button className="font-mono text-[10px] px-3 py-1.5 border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm">
                Reports left 4
              </button>
              <button className="font-mono text-[10px] px-3 py-1.5 bg-platinum text-ink hover:opacity-90 transition-opacity pixel-clip-sm">
                Buy reports
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center justify-center w-7 h-7 pixel-clip-sm bg-pulse/15 font-pixel text-[8px] text-pulse hover:bg-pulse/25 transition-colors">
                    {dashboardUser?.username?.charAt(0).toUpperCase() || 'L'}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  side="bottom"
                  align="end"
                  className="w-52 bg-panel border-white/10 text-platinum rounded-none pixel-clip-sm"
                >
                  <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-wider text-platinum/40 flex items-center gap-2">
                    <User className="w-3 h-3" /> Signed in as <span className="text-platinum">{dashboardUser?.username}</span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-white/10" />
                  <DropdownMenuItem
                    onClick={handleLogout}
                    className="font-mono text-xs text-platinum/80 focus:bg-pulse/10 focus:text-pulse cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5 mr-2" /> Log out
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-ink scanlines">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
