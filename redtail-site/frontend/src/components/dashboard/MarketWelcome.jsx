import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight, Pause, Play, Plus, RotateCcw } from 'lucide-react';
import { createLoreTopology } from '@/lib/competition/loreTopology';
import './market-welcome.css';

const EMPTY_GAMES = [];
function createMarketMap(games) {
  const nodes = games.map((game, i) => {
    const y = 1 - (i + .5) / games.length * 2;
    const radius = Math.sqrt(1 - y * y);
    const angle = i * Math.PI * (3 - Math.sqrt(5));
    const name = game.name.replace(/:.*$/, '');
    return { id: game.id, label: game.name.toUpperCase(), shortLabel: (name.length > 21 ? `${name.slice(0, 19).trim()}…` : name).toUpperCase(), p: [Math.cos(angle) * radius * 1.6, y * 1.5, Math.sin(angle) * radius * 1.6], links: [] };
  });
  // A sparse decorative web around the sphere, not inferred game similarity.
  const connected = new Set();
  nodes.forEach(node => {
    const distance = other => node.p.reduce((sum, value, axis) => sum + (value - other.p[axis]) ** 2, 0);
    nodes.filter(other => other.id !== node.id).sort((a, b) => distance(a) - distance(b)).slice(0, 3).forEach(other => {
      const key = [node.id, other.id].sort().join(':');
      if (!connected.has(key)) { node.links.push(other.id); connected.add(key); }
    });
  });
  return { core: { id: 'your-next-game', label: 'YOUR GAME', p: [0, 0, 0] }, features: [], comparables: nodes };
}

export default function MarketWelcome() {
  const [moving, setMoving] = useState(true);
  const [selected, setSelected] = useState(null);
  const canvas = useRef(null);
  const renderer = useRef(null);
  const query = useQuery({
    queryKey: ['discover-games'], staleTime: 5 * 60 * 1000, retry: 1, refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      const response = await fetch('/api/lore/discover-games', { signal });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Trending games could not load.');
      return data;
    },
  });
  const games = query.data?.games || EMPTY_GAMES;
  const model = useMemo(() => createMarketMap(games), [games]);
  const game = games.find(item => item.id === selected);
  useEffect(() => {
    const graph = createLoreTopology(canvas.current, {
      model, variant: 'discovery',
      colors: { background: '#101416', backgroundLift: '#142622', glow: '#69c9a7', feature: '#b4ed68', comparable: '#83bcf5', relation: '#83bcf5', selected: '#ff6467', core: '#edfff1' },
      onHover: node => { if (node?.type === 'comparable') { setSelected(node.id); graph.setFocus(node.id); } },
      onSelect: node => { if (node?.type === 'comparable') { setSelected(node.id); graph.setFocus(node.id); } },
    });
    renderer.current = graph;
    let inView = true;
    const visibility = () => graph.setVisible(inView && !document.hidden);
    const observer = new IntersectionObserver(entries => { inView = entries[0].isIntersecting; visibility(); });
    observer.observe(canvas.current); document.addEventListener('visibilitychange', visibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', visibility); graph.destroy(); renderer.current = null; };
  }, [model]);
  useEffect(() => { renderer.current?.setMotion(moving); }, [moving, model]);
  const choose = id => { setMoving(false); setSelected(id); renderer.current?.setFocus(id); };
  const reset = () => { setSelected(null); renderer.current?.reset(); setMoving(true); };
  return <section className="market-welcome" aria-label="Explore the market before adding your game">
    <div className="mw-top"><div><span className="mw-eyebrow">THE PLAYING FIELD</span><p>{games.length ? `${games.length === 20 ? 'TOP 20' : `${games.length} GAMES`} · STEAM TRENDING` : 'YOUR NEXT CHAPTER STARTS HERE'}</p></div><div className="mw-tools"><button onClick={() => setMoving(value => !value)} aria-label={moving ? 'Pause market globe' : 'Play market globe'}>{moving ? <Pause size={15}/> : <Play size={15}/>}</button><button onClick={reset} aria-label="Reset market globe"><RotateCcw size={15}/></button></div></div>
    <canvas ref={canvas} className="mw-canvas" tabIndex={0} role="group" onKeyDown={event => {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home'].includes(event.key)) {
        event.preventDefault(); setMoving(false);
        if (event.key === 'Home') reset();
        else renderer.current?.rotate(event.key === 'ArrowLeft' ? -.18 : event.key === 'ArrowRight' ? .18 : 0, event.key === 'ArrowUp' ? -.12 : event.key === 'ArrowDown' ? .12 : 0);
      }
    }}>Explore the trending games in the list below.</canvas>
    <div className="mw-explore"><span>DRAG TO EXPLORE</span><div aria-live="polite">{game ? <a href={game.sourceUrl} target="_blank" rel="noreferrer"><small>#{game.rank}</small> {game.name} <ArrowUpRight size={13}/></a> : <span>{games.length ? `${games.length} games. Countless possibilities.` : 'Your idea belongs here.'}</span>}</div></div>
    <div className="mw-invitation"><h1>Your game could be next<span>.</span></h1><p>Upload your game design. Find your place in the playing field.</p><Link to="/dashboard/analyze?tab=game" className="mw-add"><Plus size={17}/>Add your game<ArrowUpRight size={17}/></Link></div>
    {query.isPending && <p role="status" className="mw-status">Loading games from the market…</p>}
    {query.isError && <p role="alert" className="mw-status">Trending games couldn’t load. <button onClick={() => query.refetch()}>Try again</button></p>}
    {!!games.length && <footer className="mw-footer"><span>{query.data.source} · Two-week player activity · Snapshot {new Date(query.data.snapshotAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span><span>Connections are illustrative.</span><details><summary>Explore all {games.length} games</summary><div className="mw-game-list">{games.map(item => <button key={item.id} aria-pressed={selected === item.id} onClick={() => choose(item.id)}><small>{String(item.rank).padStart(2, '0')}</small>{item.name}</button>)}</div></details></footer>}
  </section>;
}
