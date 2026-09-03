import React, { useState } from 'react';
import {
  RadialBarChart, RadialBar, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Cell,
  AreaChart, Area, ResponsiveContainer, Tooltip,
} from 'recharts';
import { ChevronDown, Target, DollarSign, Calendar, Zap, TrendingUp, Lightbulb } from 'lucide-react';
import { scoreColor, chartTooltipStyle, chartTickFont } from '@/lib/dashboardData';

const MetricTile = ({ icon: Icon, label, value, accent }) => (
  <div className="border border-white/5 bg-panel p-3 pixel-clip-sm">
    <div className="flex items-center gap-1.5 mb-1.5">
      <Icon className="w-3 h-3" style={{ color: accent || 'rgba(226,226,226,0.4)' }} />
      <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40">{label}</span>
    </div>
    <div className="font-mono text-base font-medium text-platinum">{value}</div>
  </div>
);

export default function GameCard({ game }) {
  const [expanded, setExpanded] = useState(false);

  const gaugeData = [{ name: 'Demand', value: game.demandScore, fill: '#FF2E2E' }];
  const signalData = game.signals.map(s => ({
    name: s.label,
    score: s.score,
    fill: scoreColor(s.score),
  }));

  return (
    <div className="bg-panel border border-white/5 p-5 pixel-clip hover:border-white/10 transition-colors">
      {/* Header: game name + prominent ROI & score */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 pixel-clip-sm bg-ink border border-white/5 flex items-center justify-center flex-shrink-0">
            <Target className="w-4 h-4 text-pulse" />
          </div>
          <div>
            <h3 className="font-pixel text-sm text-platinum">{game.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="font-mono text-[10px] text-platinum/40">{game.genre}</span>
              <span
                className="font-mono text-[10px] px-2 py-0.5 pixel-clip-sm"
                style={{ background: `${game.statusColor}15`, color: game.statusColor }}
              >
                {game.status}
              </span>
            </div>
          </div>
        </div>

        {/* Strong metrics at the end */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-right">
            <div className="flex items-center gap-1 justify-end mb-0.5">
              <TrendingUp className="w-3 h-3 text-moss" />
              <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40">ROI</span>
            </div>
            <div className="font-mono text-xl font-bold text-moss">{game.roi}x</div>
          </div>
          <div className="text-center px-3 py-2 pixel-clip-sm border border-pulse/20 bg-pulse/8">
            <div className="font-pixel text-2xl font-bold text-pulse text-glow-red leading-none">
              {game.demandScore}
            </div>
            <div className="font-mono text-[8px] text-platinum/40 mt-1">FIT / 100</div>
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {/* Radial gauge */}
        <div className="border border-white/5 bg-ink p-3 pixel-clip-sm">
          <div className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40 mb-1">Demand Fit</div>
          <div className="relative">
            <ResponsiveContainer width="100%" height={120}>
              <RadialBarChart
                data={gaugeData}
                innerRadius="72%"
                outerRadius="100%"
                startAngle={90}
                endAngle={-270}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                <RadialBar dataKey="value" cornerRadius={0} background={{ fill: 'rgba(255,255,255,0.05)' }} />
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="font-mono text-xl font-bold text-platinum">{game.demandScore}</span>
              <span className="font-mono text-[9px] text-platinum/30">/ 100</span>
            </div>
          </div>
        </div>

        {/* Signal breakdown bars */}
        <div className="border border-white/5 bg-ink p-3 pixel-clip-sm md:col-span-2">
          <div className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40 mb-1">Signal Breakdown</div>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={signalData} layout="vertical" margin={{ left: -10, right: 10, top: 5 }}>
              <XAxis type="number" domain={[0, 10]} tick={{ fill: 'rgba(226,226,226,0.3)', fontSize: 8, ...chartTickFont }} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fill: 'rgba(226,226,226,0.5)', fontSize: 9, ...chartTickFont }} axisLine={false} tickLine={false} width={65} />
              <Tooltip contentStyle={chartTooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="score" radius={0} barSize={14}>
                {signalData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Metrics tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <MetricTile icon={Zap} label="Conv. Rate" value={`${game.conversionRate}%`} accent="#FF2E2E" />
        <MetricTile icon={DollarSign} label="CAC" value={`$${game.cac}`} accent="#B4FF39" />
        <MetricTile icon={Calendar} label="Launch" value={game.launchWindow} accent="#8FB3FF" />
        <div className="border border-white/5 bg-panel p-3 pixel-clip-sm">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Target className="w-3 h-3 text-moss" />
            <span className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40">Readiness</span>
          </div>
          <div className="font-mono text-base font-medium text-platinum">{game.readiness}%</div>
          <div className="mt-1.5 h-1 overflow-hidden bg-white/5">
            <div
              className="h-full"
              style={{ width: `${game.readiness}%`, background: scoreColor(game.readiness / 10) }}
            />
          </div>
        </div>
      </div>

      {/* Trend sparkline */}
      <div className="border border-white/5 bg-ink p-3 pixel-clip-sm mb-4">
        <div className="flex items-center justify-between mb-1">
          <div className="font-pixel text-[7px] uppercase tracking-wider text-platinum/40">6-Week Score Trend</div>
          <div className="flex items-center gap-1 font-mono text-[10px] text-moss">
            <TrendingUp className="w-3 h-3" /> +{game.trendData[5].score - game.trendData[0].score} pts
          </div>
        </div>
        <ResponsiveContainer width="100%" height={70}>
          <AreaChart data={game.trendData} margin={{ left: 0, right: 0, top: 5, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${game.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FF2E2E" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#FF2E2E" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="week" tick={{ fill: 'rgba(226,226,226,0.3)', fontSize: 8, ...chartTickFont }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={chartTooltipStyle} cursor={{ stroke: 'rgba(255,46,46,0.3)' }} />
            <Area type="monotone" dataKey="score" stroke="#FF2E2E" strokeWidth={2} fill={`url(#grad-${game.id})`} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Recommendations (collapsible) */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left font-mono text-xs text-platinum/50 hover:text-platinum/70 transition-colors"
      >
        <Lightbulb className="w-3.5 h-3.5 text-moss" />
        <span>{game.recommendations.length} strategic recommendations</span>
        <ChevronDown
          className="w-4 h-4 ml-auto transition-transform"
          style={{ transform: expanded ? 'rotate(180deg)' : 'none' }}
        />
      </button>
      {expanded && (
        <div className="mt-3 space-y-2">
          {game.recommendations.map((rec, i) => (
            <div
              key={i}
              className="flex items-start gap-2 bg-ink border border-white/5 p-3 pixel-clip-sm"
            >
              <span className="flex-shrink-0 w-5 h-5 pixel-clip-sm flex items-center justify-center font-pixel text-[8px] text-pulse bg-pulse/10 mt-0.5">
                {i + 1}
              </span>
              <span className="font-mono text-xs text-platinum/60 leading-relaxed">{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
