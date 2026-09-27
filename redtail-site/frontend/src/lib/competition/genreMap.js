// Same 3D wireframe-globe topology the Competition tab uses (loreTopology.js),
// applied to the 5 closest genres instead of comparable games. Genres have no
// "shared trait" concept between each other, so every genre connects straight
// to the core (an empty `links` array on every comparable — loreTopology.js
// already draws a direct core edge for any comparable with no feature links).
const DIRECTIONS = [[-1.62, -.64, .78], [1.5, -.54, .86], [-1.4, .82, -.82], [1.5, .76, -.74], [0, 1.63, .3]]
  .map(v => { const len = Math.hypot(...v); return v.map(c => c / len); });

function shortName(name) {
  const title = name.split(/\s*:\s*|\s+[–—-]\s+/)[0];
  return title.length > 23 ? `${title.slice(0, 21).trim()}…` : title;
}

export function createGenreMap(genres, gameName) {
  const comparables = genres.slice(0, 5).map((g, i) => {
    const dir = DIRECTIONS[i % DIRECTIONS.length];
    // Distance from the core still encodes fit — closer means a stronger
    // match — the same "shorter lines = stronger similarity" semantic the
    // flat 2D genre view used, just on a 3D globe now.
    const fit = typeof g.fit === 'number' ? g.fit : 0.5;
    const radius = 0.85 + (1 - fit) * 1.15;
    return {
      id: `genre-${i}`, name: g.name, label: g.name.toUpperCase(), shortLabel: shortName(g.name).toUpperCase(),
      p: dir.map(c => c * radius), links: [], fit: g.fit, reason: g.reason, evidence: g.evidence,
    };
  });
  return {
    core: { id: 'uploaded-game', label: gameName.toUpperCase(), shortLabel: shortName(gameName).toUpperCase(), p: [0, 0, 0] },
    features: [],
    comparables,
  };
}
