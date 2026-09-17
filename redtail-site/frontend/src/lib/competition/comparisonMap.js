// Summarize explicit shared traits in the saved AI comparison; no new model claims.
/** @type {Array<[string, string, RegExp]>} */
const TRAITS = [
  ['duels', '1V1 DUELS', /\b(?:1v1|1 vs 1|head-to-head|duel\w*)\b/i],
  ['arena', 'ARENA COMBAT', /\barena\b/i],
  ['mobile', 'MOBILE PLAY', /\b(?:mobile|touchscreen|touch-native)\b/i],
  ['ranked', 'RANKED PLAY', /\branked\b/i],
  ['cooldowns', 'COOLDOWNS', /\bcooldown\w*\b/i],
  ['cosmetics', 'COSMETIC ECONOMY', /\bcosmetic\w*\b/i],
  ['cozy', 'COZY PLAY', /\b(?:cozy|low-stress|relaxation)\b/i],
  ['sessions', 'SHORT SESSIONS', /\b(?:short.session|single-session|short match)\w*/i],
  ['touch', 'TACTILE INPUT', /\b(?:tactile|manual input|precision input)\b/i],
  ['collect', 'COLLECTION', /\b(?:collectathon|collection|collecting|collector)\b/i],
  ['puzzle', 'PUZZLE LOOP', /\bpuzzle\b/i],
  ['history', 'NATURAL HISTORY', /\b(?:fossil|natural.history|dinosaurs)\b/i],
  ['social', 'SOCIAL PLAY', /\b(?:social features|social play|co-op|cooperative)\b/i],
  ['story', 'STORY', /\b(?:narrative|story.driven)\b/i],
  ['build', 'BUILDING', /\b(?:building|crafting|construction)\b/i],
  ['rhythm', 'RHYTHM', /\brhythm\b/i],
];
const FEATURE_PLACES = [[-.98, 0, 0], [0, -.9, 0], [.98, 0, 0], [0, .9, 0], [0, 0, .98], [0, 0, -.98]];
const GAME_PLACES = [[-1.62, -.64, .78], [1.5, -.54, .86], [-1.4, .82, -.82], [1.5, .76, -.74], [0, 1.63, .3]];

function sharedComparison(game) {
  // Never create links from the differences / unknowns in the comparison.
  const shared = String(game.reason || '').split(/\b(?:key\s+)?differences?\s*:|\bwhereas\b|\bunlike\b|\bbut\b|\brather than\b|\bhowever\b/i)[0];
  if (!/\b(?:shar\w*|match\w*|overlap\w*|both|closest|parallel|similar)\b/i.test(shared)) return '';
  return shared.replaceAll(game.name, '').split(/(?<=[.!?])\s+/).filter(sentence => !/\b(?:unknown|unavailable|no evidence|not supported|does not|doesn't|lacks)\b/i.test(sentence)).join(' ');
}
function shortName(name) {
  const title = name.split(/\s*:\s*|\s+[–—-]\s+/)[0];
  return title.length > 23 ? `${title.slice(0, 21).trim()}…` : title;
}
function iconFor(game) {
  // Steam's CDN serves a header image at a predictable URL from the app id
  // alone — no scraper change or extra fetch needed, and it works
  // retroactively for every already-scraped Steam/Steam-trending record.
  // Google Play/App Store/RAWG icons aren't captured by the scrapers yet, so
  // there's no real image to show for those sources today.
  if ((game.source === 'steam' || game.source === 'steamtrending') && game.appId) {
    return `https://cdn.akamai.steamstatic.com/steam/apps/${game.appId}/header.jpg`;
  }
  return game.icon || null;
}

export function createComparisonMap(games, gameName) {
  const comparisons = games.slice(0, 5).map(game => ({ game, shared: sharedComparison(game) }));
  const features = TRAITS.map(([id, label, pattern]) => ({
    id, label,
    evidence: comparisons.filter(({ shared }) => pattern.test(shared)).map(({ game, shared }) => ({ game: game.name, quote: shared.trim() })),
  })).filter(trait => trait.evidence.length).slice(0, 6).map((trait, i) => ({ ...trait, p: FEATURE_PLACES[i] }));
  return {
    core: { id: 'uploaded-game', label: gameName.toUpperCase(), shortLabel: shortName(gameName).toUpperCase(), p: [0, 0, 0] },
    features,
    comparables: comparisons.map(({ game }, i) => ({
      id: `game-${i}`, name: game.name, label: game.name.toUpperCase(), shortLabel: shortName(game.name).toUpperCase(), p: GAME_PLACES[i],
      icon: iconFor(game),
      links: features.filter(trait => trait.evidence.some(item => item.game === game.name)).map(trait => trait.id),
    })),
  };
}
