// Mock data for the dashboard — represents what a real Lore analysis would return

export const GAMES = [
  {
    id: 'beewitched',
    name: 'BeeWitched',
    genre: 'Cozy Crafting',
    status: 'In Analysis',
    statusColor: '#B4FF39',
    demandScore: 72,
    roi: 3.4,
    conversionRate: 4.2,
    cac: 2.80,
    launchWindow: 'Q1 2027',
    readiness: 68,
    signals: [
      { label: 'Co-op', score: 9.5, hits: 427 },
      { label: 'Fast Prog', score: 8.5, hits: 380 },
      { label: 'PvP', score: 8.3, hits: 290 },
      { label: 'Short-Sess', score: 6.4, hits: 286 },
      { label: 'Cosmetic', score: 2.4, hits: 108 },
    ],
    competitors: [
      { name: 'Genshin Impact', mentions: 79, positive: 75 },
      { name: 'Street Fighter', mentions: 64, positive: 69 },
      { name: 'Candy Crush', mentions: 36, positive: 83 },
      { name: 'Cookie Clicker', mentions: 36, positive: 72 },
    ],
    recommendations: [
      'Add an asynchronous social layer (targets the 9.5/10 co-op signal)',
      'Instrument session length — tune day-clock to 10-20 min sweet spot',
      'Build a shareable score-card moment around the review screen',
    ],
    trendData: [
      { week: 'W1', score: 58 },
      { week: 'W2', score: 62 },
      { week: 'W3', score: 65 },
      { week: 'W4', score: 68 },
      { week: 'W5', score: 70 },
      { week: 'W6', score: 72 },
    ],
  },
  {
    id: 'neon-drift',
    name: 'Neon Drift',
    genre: 'Arcade Racing',
    status: 'Playtesting',
    statusColor: '#8FB3FF',
    demandScore: 81,
    roi: 5.2,
    conversionRate: 6.8,
    cac: 1.90,
    launchWindow: 'Q4 2026',
    readiness: 84,
    signals: [
      { label: 'Short-Sess', score: 8.8, hits: 312 },
      { label: 'Fast Prog', score: 7.9, hits: 245 },
      { label: 'PvP', score: 7.2, hits: 198 },
      { label: 'Co-op', score: 4.1, hits: 87 },
      { label: 'Cosmetic', score: 5.6, hits: 142 },
    ],
    competitors: [
      { name: 'Mario Kart Tour', mentions: 92, positive: 71 },
      { name: 'Asphalt 9', mentions: 54, positive: 78 },
      { name: 'CSR Racing', mentions: 41, positive: 65 },
      { name: 'Real Racing 3', mentions: 38, positive: 80 },
    ],
    recommendations: [
      'Capitalize on short-session dominance with daily challenge events',
      'Add cosmetic car skins (5.6/10 signal is viable for ethical spend)',
      'Position against Mario Kart on gameplay depth, not brand recognition',
    ],
    trendData: [
      { week: 'W1', score: 70 },
      { week: 'W2', score: 73 },
      { week: 'W3', score: 75 },
      { week: 'W4', score: 78 },
      { week: 'W5', score: 80 },
      { week: 'W6', score: 81 },
    ],
  },
];

export const MARKET_SIGNALS = [
  { name: 'Co-op', score: 9.5, hits: 427 },
  { name: 'Fast Prog', score: 8.5, hits: 380 },
  { name: 'PvP', score: 8.3, hits: 290 },
  { name: 'Short-Sess', score: 6.4, hits: 286 },
  { name: 'Cosmetic', score: 2.4, hits: 108 },
];

export const MARKET_TREND = [
  { week: 'W1', coOp: 7.2, shortSess: 5.8, pvp: 6.9 },
  { week: 'W2', coOp: 7.8, shortSess: 5.9, pvp: 7.1 },
  { week: 'W3', coOp: 8.2, shortSess: 6.0, pvp: 7.5 },
  { week: 'W4', coOp: 8.7, shortSess: 6.1, pvp: 7.8 },
  { week: 'W5', coOp: 9.1, shortSess: 6.3, pvp: 8.1 },
  { week: 'W6', coOp: 9.5, shortSess: 6.4, pvp: 8.3 },
];

// Site palette: pulse #FF2E2E, moss #B4FF39, ghost #8FB3FF, platinum #E2E2E2
export const scoreColor = (score) =>
  score >= 8 ? '#B4FF39' : score >= 5 ? '#8FB3FF' : '#FF2E2E';

export const chartTooltipStyle = {
  background: '#15151A',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '0px',
  color: '#E2E2E2',
  fontSize: '11px',
  fontFamily: '"JetBrains Mono", monospace',
};

export const chartTickFont = { fontFamily: '"JetBrains Mono", monospace' };
