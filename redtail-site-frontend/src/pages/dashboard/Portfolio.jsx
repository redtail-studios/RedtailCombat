import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Plus, Gamepad2, FileText, Sparkles, Clock, ArrowRight, RefreshCw } from 'lucide-react';
import { useLoreReports } from '@/lib/LoreReportsContext';

export default function Portfolio() {
  const navigate = useNavigate();
  const { portfolio, reports } = useLoreReports();
  const [showAddForm, setShowAddForm] = useState(false);
  const [gameName, setGameName] = useState('');

  const goAnalyzeGame = () => {
    setShowAddForm(false);
    setGameName('');
    // Hands off to the real Lore analysis flow (dashboard-embedded, keeps
    // the sidebar), which continues into the real redesign step once a
    // report is generated, and adds the game here automatically.
    navigate('/dashboard/analyze?tab=game');
  };

  const gameReports = reports.filter((r) => r.type === 'game');
  const lastAnalysed = portfolio.length
    ? [...portfolio].sort((a, b) => new Date(b.updatedAt || b.addedAt) - new Date(a.updatedAt || a.addedAt))[0]
    : null;

  const STATS = [
    { label: 'Games Tracked', value: String(portfolio.length), sub: 'in your portfolio', icon: Gamepad2, color: '#FF2E2E' },
    { label: 'Reports Generated', value: String(reports.length), sub: 'market + game reports', icon: FileText, color: '#B4FF39' },
    { label: 'Game Analyses', value: String(gameReports.length), sub: 'your games vs. market', icon: Sparkles, color: '#8FB3FF' },
    { label: 'Last Analysed', value: lastAnalysed ? formatDistanceToNow(new Date(lastAnalysed.updatedAt || lastAnalysed.addedAt), { addSuffix: true }) : '—', sub: lastAnalysed?.name || 'no games yet', icon: Clock, color: '#FF2E2E' },
  ];

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-end justify-between mb-6 flex-wrap gap-4">
        <div>
          <h1 className="font-pixel text-base text-platinum mb-2">Portfolio</h1>
          <p className="font-mono text-xs text-platinum/40">
            {portfolio.length ? `${portfolio.length} game${portfolio.length === 1 ? '' : 's'} analysed` : 'No games analysed yet'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-3 py-2 font-mono text-[10px] font-medium bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            New game
          </button>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        {STATS.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-panel border border-white/5 p-4 pixel-clip-sm">
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-3.5 h-3.5" style={{ color: stat.color }} />
                <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40">
                  {stat.label}
                </span>
              </div>
              <div className="font-mono text-2xl font-bold text-platinum mb-1">{stat.value}</div>
              <div className="font-mono text-[10px] text-platinum/30 truncate">{stat.sub}</div>
            </div>
          );
        })}
      </div>

      {/* Games */}
      {portfolio.length > 0 ? (
        <div className="space-y-3">
          {portfolio.map((game) => (
            <div key={game.id} className="bg-panel border border-white/5 p-5 pixel-clip flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 pixel-clip-sm bg-ink border border-white/5 flex items-center justify-center flex-shrink-0">
                  <Gamepad2 className="w-4 h-4 text-pulse" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-pixel text-sm text-platinum truncate">{game.name}</h3>
                  <p className="font-mono text-[10px] text-platinum/40 mt-1">
                    Analysed against {game.lastYears || '—'} · {formatDistanceToNow(new Date(game.updatedAt || game.addedAt), { addSuffix: true })}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => navigate('/dashboard/reports')}
                  className="flex items-center gap-1.5 px-3 py-2 font-mono text-[10px] border border-white/10 text-platinum/60 hover:text-platinum hover:border-white/20 transition-colors pixel-clip-sm"
                >
                  View report <ArrowRight className="w-3 h-3" />
                </button>
                <button
                  onClick={goAnalyzeGame}
                  className="flex items-center gap-1.5 px-3 py-2 font-mono text-[10px] bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
                >
                  <RefreshCw className="w-3 h-3" /> Re-analyse
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="border-2 border-dashed border-white/10 flex flex-col items-center justify-center py-20 text-center pixel-clip-sm">
          <Gamepad2 className="w-5 h-5 text-platinum/20 mb-3" />
          <p className="font-mono text-xs text-platinum/40 mb-1">No games analysed yet.</p>
          <p className="font-mono text-xs text-platinum/30 mb-4">Add a game to see it here, with a link to its real market report.</p>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
          >
            <Plus className="w-3.5 h-3.5" /> Add your first game
          </button>
        </div>
      )}

      {/* Add new game modal */}
      {showAddForm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80"
          onClick={() => setShowAddForm(false)}
        >
          <div
            className="bg-panel border border-white/10 p-6 w-full max-w-md mx-4 pixel-clip"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-pixel text-sm text-platinum mb-4">Add a new game</h3>
            <input
              type="text"
              autoFocus
              placeholder="Game name (optional — we'll use the PDF's title)"
              value={gameName}
              onChange={(e) => setGameName(e.target.value)}
              className="w-full px-4 py-3 font-mono text-sm mb-4 outline-none bg-ink border border-white/10 text-platinum placeholder:text-platinum/20 pixel-clip-sm focus:border-pulse/40"
            />
            <p className="font-mono text-[10px] text-platinum/40 mb-4 leading-relaxed">
              We'll analyze your game's design doc against real scraped market signals and generate a live report — then it's added here automatically.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowAddForm(false); setGameName(''); }}
                className="flex-1 py-2.5 font-mono text-xs border border-white/10 text-platinum/50 hover:text-platinum transition-colors pixel-clip-sm"
              >
                Cancel
              </button>
              <button
                onClick={goAnalyzeGame}
                className="flex-1 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
              >
                Analyze game
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
