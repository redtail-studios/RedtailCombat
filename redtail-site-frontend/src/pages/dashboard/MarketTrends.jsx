import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Newspaper, TrendingUp, ExternalLink, Search, Lock, Rocket, BarChart3 } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip,
} from 'recharts';
import { chartTooltipStyle, chartTickFont } from '@/lib/dashboardData';
import { useLoreReports } from '@/lib/LoreReportsContext';
import SignalAnalysis from '@/components/dashboard/SignalAnalysis';

function sentimentTag(sentiment) {
  const c = sentiment?.compound ?? 0;
  if (c >= 0.2) return { label: 'POSITIVE', color: '#B4FF39' };
  if (c <= -0.2) return { label: 'NEGATIVE', color: '#FF2E2E' };
  return { label: 'NEUTRAL', color: '#8FB3FF' };
}

function trendColor(avg) {
  if (avg >= 60) return '#B4FF39';
  if (avg >= 30) return '#8FB3FF';
  return '#FF2E2E';
}

function safeDate(raw) {
  const d = new Date(raw);
  return isNaN(d.getTime()) ? null : d;
}

export default function MarketTrends() {
  const navigate = useNavigate();
  const { reports } = useLoreReports();
  const hasReports = reports.length > 0;
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/lore/market-snapshot')
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setSnapshot(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  const trends = snapshot?.trends || [];
  const news = snapshot?.news || [];
  const trendChartData = trends
    .filter((t) => typeof t.avg_interest === 'number')
    .map((t) => ({ name: t.term, value: t.avg_interest, genre: t.genre }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      {/* Live ticker — real recent headlines */}
      {news.length > 0 && (
        <div className="flex items-center gap-3 mb-6 overflow-hidden border border-white/5 bg-panel py-2.5 pixel-clip-sm">
          <div className="flex items-center gap-1.5 px-3 flex-shrink-0 font-pixel text-[8px] uppercase tracking-wider text-pulse border-r border-white/5">
            <Newspaper className="w-3 h-3" />
            LIVE
          </div>
          <div className="relative flex-1 overflow-hidden">
            <div className="flex gap-8 whitespace-nowrap animate-ticker">
              {[...news, ...news].slice(0, 24).map((item, i) => (
                <span key={i} className="font-mono text-xs text-platinum/50">
                  <span className="text-pulse">●</span> {item.title}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Page header */}
      <h1 className="font-pixel text-base text-platinum mb-2">Market trends</h1>
      <p className="font-mono text-xs text-platinum/40 mb-6">
        Real Google Trends + gaming-news signal from the {snapshot?.year || '—'} scrape snapshot.
      </p>

      {error && (
        <div className="mb-6 p-4 border border-pulse/30 bg-pulse/5 font-mono text-xs text-pulse pixel-clip-sm">
          Couldn't load market snapshot: {error}
        </div>
      )}

      {/* Recent gaming news — real, ungated */}
      <div className="bg-panel border border-white/5 p-4 pixel-clip-sm mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Newspaper className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Recent gaming-industry news</span>
        </div>
        {news.length > 0 ? (
          <div className="space-y-3">
            {news.slice(0, 5).map((item, i) => {
              const tag = sentimentTag(item.sentiment);
              const date = safeDate(item.date);
              return (
                <a
                  key={i}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="relative block bg-ink border border-white/5 p-4 pl-5 pixel-clip-sm hover:border-white/10 transition-colors group"
                >
                  <div className="absolute left-0 top-0 bottom-0 w-1" style={{ background: tag.color }} />
                  <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                    <span className="font-pixel text-[8px] tracking-wider text-pulse">{item.site || 'NEWS'}</span>
                    {date && (
                      <span className="font-mono text-[10px] text-platinum/30">• {formatDistanceToNow(date, { addSuffix: true })}</span>
                    )}
                    <span className="ml-auto font-mono text-[9px] px-2 py-0.5 pixel-clip-sm" style={{ background: `${tag.color}15`, color: tag.color }}>
                      {tag.label}
                    </span>
                  </div>
                  <h3 className="font-mono text-sm font-medium text-platinum/80 group-hover:text-platinum transition-colors mb-1 flex items-start gap-1.5">
                    <span>{item.title}</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0 mt-1 opacity-0 group-hover:opacity-50 transition-opacity" />
                  </h3>
                  {item.text && (
                    <p className="font-mono text-xs text-platinum/40 leading-relaxed">{item.text}</p>
                  )}
                </a>
              );
            })}
          </div>
        ) : (
          <div className="border-2 border-dashed border-white/10 flex flex-col items-center justify-center py-10 text-center pixel-clip-sm">
            <p className="font-mono text-xs text-platinum/30">
              {snapshot ? 'No cached gaming news yet — run a scrape from the Lore console.' : 'Loading…'}
            </p>
          </div>
        )}
      </div>

      {/* Google Trends — real, always visible, general market data. Not
          affected by whether you've uploaded a game or not. */}
      <div className="bg-panel border border-white/5 p-4 pixel-clip-sm mb-6">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">
            Google search interest — {snapshot?.year || '—'}
          </span>
        </div>
        {trendChartData.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trendChartData} margin={{ left: -15, right: 10, top: 5 }}>
                <XAxis dataKey="name" tick={{ fill: 'rgba(226,226,226,0.4)', fontSize: 9, ...chartTickFont }} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickLine={false} interval={0} angle={-20} textAnchor="end" height={50} />
                <YAxis domain={[0, 100]} tick={{ fill: 'rgba(226,226,226,0.25)', fontSize: 8, ...chartTickFont }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="value" radius={0} barSize={28}>
                  {trendChartData.map((entry, i) => (
                    <Cell key={i} fill={trendColor(entry.value)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap gap-2 mt-3">
              {trends.filter((t) => t.rising_queries?.length).slice(0, 6).map((t, i) => (
                <div key={i} className="font-mono text-[10px] px-2.5 py-1 bg-white/5 text-platinum/50 pixel-clip-sm">
                  <span className="text-moss">{t.term}:</span> {t.rising_queries[0]}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="border-2 border-dashed border-white/10 flex flex-col items-center justify-center py-10 text-center pixel-clip-sm">
            <Search className="w-4 h-4 text-platinum/20 mb-2" />
            <p className="font-mono text-xs text-platinum/40 mb-1">No Google Trends data cached for {snapshot?.year || 'this year'} yet.</p>
            <a href="/lore" className="font-mono text-xs text-moss hover:underline">Run a scrape from the Lore console →</a>
          </div>
        )}
      </div>

      {/* Signal Simulator + Competitor Radar — real, computed live from the
          2022-2026 scraped data (analysis.py, no LLM call). Locked behind a
          blur + overlay until you have a report, then just themselves,
          unblurred. Never swapped for anything else. */}
      <div className="bg-panel border border-white/5 p-4 pixel-clip-sm">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Market signal simulation</span>
        </div>
        <div className="relative">
          <div className={!hasReports ? 'blur-md opacity-40 pointer-events-none select-none' : ''}>
            <SignalAnalysis />
          </div>
          {!hasReports && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <Lock className="w-5 h-5 text-platinum mb-3" />
              <p className="font-pixel text-[9px] uppercase tracking-wider text-platinum mb-2">Locked</p>
              <p className="font-mono text-xs text-platinum/80 mb-5">Add your game to see the simulation.</p>
              <button
                onClick={() => navigate('/dashboard/analyze?tab=game')}
                className="flex items-center gap-2 px-4 py-2.5 font-mono text-xs font-medium bg-pulse text-ink hover:opacity-90 transition-opacity pixel-clip-sm"
              >
                <Rocket className="w-3.5 h-3.5" /> Analyze your game
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
