import React, { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, ResponsiveContainer, Tooltip, Legend,
} from 'recharts';
import { Rocket, Swords } from 'lucide-react';
import { scoreColor, chartTooltipStyle, chartTickFont } from '@/lib/dashboardData';

const YEARS = [2022, 2023, 2024, 2025, 2026];
const LINE_COLORS = ['#FF2E2E', '#B4FF39', '#8FB3FF'];

function verdict(topScore) {
  if (topScore >= 8) return { label: 'STRONG', color: '#B4FF39' };
  if (topScore >= 5) return { label: 'MODERATE', color: '#8FB3FF' };
  return { label: 'EARLY', color: '#FF2E2E' };
}

const SimTile = ({ label, value, color }) => (
  <div className="border border-white/5 bg-panel p-2.5 pixel-clip-sm">
    <div className="font-pixel text-[6px] uppercase tracking-wider text-platinum/30 mb-1">{label}</div>
    <div className="font-mono text-sm font-bold" style={{ color: color || '#E2E2E2' }}>{value}</div>
  </div>
);

export default function SignalAnalysis() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [year, setYear] = useState(2026);
  const [selectedCompetitors, setSelectedCompetitors] = useState([]);
  const [genres, setGenres] = useState([]); // [{id, label}]
  const [genre, setGenre] = useState(null); // null = all genres (aggregate)

  useEffect(() => {
    fetch('/api/lore/env')
      .then((r) => r.json())
      .then((d) => {
        const active = d.active_genres || [];
        setGenres(active.map((id) => ({ id, label: d.genres?.[id] || id })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    const qs = genre ? `?genre=${encodeURIComponent(genre)}` : '';
    fetch(`/api/lore/signal-analysis${qs}`)
      .then((r) => r.json())
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [genre]);

  const years = data?.years || {};
  const current = years[String(year)] || { total_items: 0, signals: {}, scorecard: {}, competitors: [] };
  const signalNames = Object.keys(current.signals || {});
  const topSignals = [...signalNames].sort((a, b) => (current.signals[b]?.score || 0) - (current.signals[a]?.score || 0)).slice(0, 3);

  // Real signal-score trend across every scraped year, for this year's top 3 signals.
  const trendData = YEARS.map((y) => {
    const yd = years[String(y)];
    const row = { year: y };
    topSignals.forEach((s) => { row[s] = yd?.signals?.[s]?.score ?? null; });
    return row;
  });

  const topScore = current.signals?.[current.scorecard?.top_signal]?.score || 0;
  const v = verdict(topScore);

  const competitors = current.competitors || [];
  const maxMentions = Math.max(1, ...competitors.map((c) => c.mentions));

  useEffect(() => {
    // Default-select up to 2 competitors whenever the year (and so the
    // available competitor list) changes.
    setSelectedCompetitors(competitors.slice(0, 2).map((c) => c.name));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, data]);

  const radarData = useMemo(() => {
    const axes = ['Mentions', 'Positive %', 'Negative %'];
    return axes.map((axis) => {
      const row = { axis };
      competitors.filter((c) => selectedCompetitors.includes(c.name)).forEach((c) => {
        row[c.name] = axis === 'Mentions' ? Math.round((c.mentions / maxMentions) * 10)
          : axis === 'Positive %' ? Math.round(c.positive_pct / 10)
          : Math.round(c.negative_pct / 10);
      });
      return row;
    });
  }, [competitors, selectedCompetitors, maxMentions]);

  if (error) {
    return <div className="col-span-2 font-mono text-xs text-pulse p-4">Couldn't load signal analysis: {error}</div>;
  }

  return (
    <div>
      {genres.length > 0 && (
        <div className="flex items-center gap-1.5 mb-4 flex-wrap">
          <span className="font-mono text-[10px] uppercase tracking-wider text-platinum/30 mr-1">Genre</span>
          <button
            onClick={() => setGenre(null)}
            className={`px-2.5 py-1 pixel-clip-sm font-mono text-[10px] transition-colors ${!genre ? 'bg-platinum text-ink' : 'border border-white/10 text-platinum/40 hover:text-platinum/60'}`}
          >
            All
          </button>
          {genres.map((g) => (
            <button
              key={g.id}
              onClick={() => setGenre(g.id)}
              className={`px-2.5 py-1 pixel-clip-sm font-mono text-[10px] transition-colors ${genre === g.id ? 'bg-platinum text-ink' : 'border border-white/10 text-platinum/40 hover:text-platinum/60'}`}
              title={g.label}
            >
              {g.label}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Left: real signal-score simulator */}
      <div className="bg-panel border border-white/5 p-4 pixel-clip-sm h-full">
        <div className="flex items-center gap-2 mb-3">
          <Rocket className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Signal Simulator</span>
        </div>
        <p className="font-mono text-[10px] text-platinum/40 mb-4">Real demand-signal strength by scraped year</p>

        <div className="flex gap-1.5 mb-4 flex-wrap">
          {YEARS.map((y) => (
            <button
              key={y}
              onClick={() => setYear(y)}
              className={`px-2.5 py-1.5 pixel-clip-sm transition-all ${year === y ? 'bg-pulse text-ink' : 'border border-white/10 text-platinum/40 hover:text-platinum/60 hover:border-white/20'}`}
            >
              <span className="font-mono text-[10px]">{y}</span>
            </button>
          ))}
        </div>

        {current.total_items > 0 ? (
          <>
            <div className="flex items-center gap-2 mb-4">
              <span className="font-pixel text-[8px] px-3 py-1.5 pixel-clip-sm" style={{ background: `${v.color}15`, color: v.color, border: `1px solid ${v.color}30` }}>
                {v.label}
              </span>
              <span className="font-mono text-[10px] text-platinum/30">
                {current.scorecard?.top_signal} leads at {topScore}/10 across {current.total_items} scraped items.
              </span>
            </div>

            <div className="border border-white/5 bg-ink p-3 pixel-clip-sm mb-3">
              <div className="font-pixel text-[6px] uppercase tracking-wider text-platinum/30 mb-1">Top-signal score, 2022 → 2026</div>
              <ResponsiveContainer width="100%" height={130}>
                <LineChart data={trendData} margin={{ left: -15, right: 5, top: 5, bottom: 0 }}>
                  <XAxis dataKey="year" tick={{ fill: 'rgba(226,226,226,0.25)', fontSize: 8, ...chartTickFont }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 10]} tick={{ fill: 'rgba(226,226,226,0.2)', fontSize: 7, ...chartTickFont }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  {topSignals.map((s, i) => (
                    <Line key={s} type="monotone" dataKey={s} name={s} stroke={LINE_COLORS[i]} strokeWidth={2} dot={{ r: 2, fill: LINE_COLORS[i] }} connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <SimTile label="Items analysed" value={current.total_items} />
              <SimTile label="Top signal" value={`${topScore}/10`} color={scoreColor(topScore)} />
              <SimTile label="Positive" value={`${current.scorecard?.positive_pct ?? 0}%`} color="#B4FF39" />
              <SimTile label="Negative" value={`${current.scorecard?.negative_pct ?? 0}%`} color="#FF2E2E" />
            </div>
          </>
        ) : (
          <div className="border-2 border-dashed border-white/10 flex items-center justify-center py-10 text-center pixel-clip-sm">
            <p className="font-mono text-xs text-platinum/30">{data ? `No scraped data for ${year} yet.` : 'Loading…'}</p>
          </div>
        )}
      </div>

      {/* Right: real competitor comparison */}
      <div className="bg-panel border border-white/5 p-4 pixel-clip-sm h-full">
        <div className="flex items-center gap-2 mb-3">
          <Swords className="w-3.5 h-3.5 text-pulse" />
          <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/50">Competitor Radar</span>
        </div>
        <p className="font-mono text-[10px] text-platinum/40 mb-4">Real named-competitor mentions &amp; sentiment, {year}</p>

        {competitors.length > 0 ? (
          <>
            <div className="flex gap-1.5 mb-4 flex-wrap">
              {competitors.slice(0, 4).map((c, i) => {
                const sel = selectedCompetitors.includes(c.name);
                return (
                  <button
                    key={c.name}
                    onClick={() => setSelectedCompetitors((s) => sel ? s.filter((n) => n !== c.name) : s.length >= 2 ? [s[1], c.name] : [...s, c.name])}
                    className="px-3 py-1.5 pixel-clip-sm transition-all"
                    style={{
                      background: sel ? `${LINE_COLORS[i % LINE_COLORS.length]}20` : 'transparent',
                      border: `1px solid ${sel ? LINE_COLORS[i % LINE_COLORS.length] : 'rgba(255,255,255,0.1)'}`,
                      color: sel ? LINE_COLORS[i % LINE_COLORS.length] : 'rgba(226,226,226,0.4)',
                    }}
                  >
                    <span className="font-mono text-[10px]">{c.name}</span>
                  </button>
                );
              })}
            </div>

            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="axis" tick={{ fill: 'rgba(226,226,226,0.4)', fontSize: 9, ...chartTickFont }} />
                <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
                {competitors.filter((c) => selectedCompetitors.includes(c.name)).map((c, i) => (
                  <Radar key={c.name} name={c.name} dataKey={c.name} stroke={LINE_COLORS[i]} fill={LINE_COLORS[i]} fillOpacity={0.25} strokeWidth={2} />
                ))}
                <Legend wrapperStyle={{ fontSize: '9px', fontFamily: '"JetBrains Mono", monospace', color: 'rgba(226,226,226,0.5)' }} iconType="circle" iconSize={6} />
                <Tooltip contentStyle={chartTooltipStyle} />
              </RadarChart>
            </ResponsiveContainer>

            <div className="space-y-1.5 mt-3">
              {competitors.slice(0, 4).map((c, i) => (
                <div key={c.name} className="flex items-center justify-between font-mono text-[10px] text-platinum/40">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: LINE_COLORS[i % LINE_COLORS.length] }} />
                    {c.name}
                  </span>
                  <span>{Math.round(c.mentions)} mentions · {c.positive_pct}% pos</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="border-2 border-dashed border-white/10 flex items-center justify-center py-10 text-center pixel-clip-sm">
            <p className="font-mono text-xs text-platinum/30">{data ? `No named-competitor mentions found for ${year} yet.` : 'Loading…'}</p>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
