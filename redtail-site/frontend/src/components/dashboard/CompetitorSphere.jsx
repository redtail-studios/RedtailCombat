import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Pause, Play, RotateCcw } from 'lucide-react';
import { createLoreTopology } from '@/lib/competition/loreTopology';
import './competitor-sphere.css';

// Real Steam header art loads for most comparables; anything without a known
// icon URL (Google Play/App Store/RAWG aren't captured by the scrapers yet)
// falls back to a plain initial so the row still looks complete.
function GameIcon({ game }) {
  const [failed, setFailed] = useState(false);
  if (!game.icon || failed) {
    return <span className="cs-game-icon cs-game-icon-fallback" aria-hidden="true">{game.name.charAt(0).toUpperCase()}</span>;
  }
  return <img className="cs-game-icon" src={game.icon} alt="" aria-hidden="true" loading="lazy" onError={() => setFailed(true)} />;
}

export default function CompetitorSphere({ model, selected, pinned, onPreview, onSelect, onUnpin }) {
  const canvas = useRef(null);
  const renderer = useRef(null);
  const callbacks = useRef({ onPreview, onSelect, pinned });
  callbacks.current = { onPreview, onSelect, pinned };
  const [moving, setMoving] = useState(false);
  const [feature, setFeature] = useState(null);
  const selectedId = model.comparables.find(game => game.name === selected)?.id;

  useEffect(() => {
    const graph = createLoreTopology(canvas.current, {
      model,
      colors: { background: '#101416', backgroundLift: '#142321', glow: '#69c9a7', grid: '#66847a', wire: '#78958a', relation: '#83bcf5', core: '#e1ede6', feature: '#b4ed68', comparable: '#83bcf5', selected: '#ff5c60', text: '#d9e4de', muted: '#789087' },
      onHover: node => {
        if (!node || callbacks.current.pinned) return;
        if (node.type === 'comparable') {
          setFeature(null);
          const found = model.comparables.find(game => game.id === node.id);
          if (found) { callbacks.current.onPreview(found.name); graph.setFocus(node.id); }
        } else if (node.type === 'feature') {
          setFeature(model.features.find(item => item.id === node.id));
          graph.setFocus(node.id);
        }
      },
      onSelect: node => {
        if (node.type === 'comparable') {
          setFeature(null);
          const found = model.comparables.find(game => game.id === node.id);
          if (found) callbacks.current.onSelect(found.name);
        } else if (node.type === 'feature') setFeature(model.features.find(item => item.id === node.id));
      },
    });
    renderer.current = graph;
    let inView = true;
    const visibility = () => graph.setVisible(inView && !document.hidden);
    const observer = new IntersectionObserver(entries => { inView = entries[0].isIntersecting; visibility(); });
    observer.observe(canvas.current);
    document.addEventListener('visibilitychange', visibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', visibility); graph.destroy(); renderer.current = null; };
  }, [model]);
  useEffect(() => { renderer.current?.setFocus(feature?.id || selectedId); }, [feature, selectedId, model]);
  useEffect(() => { renderer.current?.setMotion(moving && !pinned); }, [moving, pinned, model]);

  const preview = name => { if (!pinned) { setFeature(null); onPreview(name); } };
  const select = name => { setFeature(null); onSelect(name); };
  const reset = () => { setMoving(false); setFeature(null); onUnpin(); renderer.current?.reset(); renderer.current?.setFocus(selectedId); };
  return <div className="competitor-sphere" onKeyDown={event => { if (event.key === 'Escape') { onUnpin(); setFeature(null); } }}>
    <div className="cs-toolbar"><span>{model.comparables.length} COMPARABLE GAMES <b>·</b> {model.features.length} SHARED TRAITS</span><div className="cs-tools"><button className="cs-tool" onClick={() => { onUnpin(); setMoving(value => !value); }} aria-label={moving && !pinned ? 'Pause competitor globe' : 'Animate competitor globe'}>{moving && !pinned ? <Pause size={14}/> : <Play size={14}/>}</button><button onClick={reset} className="cs-tool" aria-label="Reset competitor globe"><RotateCcw size={14}/></button></div></div>
    <canvas ref={canvas} className="cs-topology" tabIndex={0} role="group" aria-describedby="competitor-map-help" onKeyDown={event => {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home'].includes(event.key)) {
        event.preventDefault(); setMoving(false);
        if (event.key === 'Home') reset();
        else renderer.current?.rotate(event.key === 'ArrowLeft' ? -.18 : event.key === 'ArrowRight' ? .18 : 0, event.key === 'ArrowUp' ? -.12 : event.key === 'ArrowDown' ? .12 : 0);
      }
    }}>Explore {model.core.label} and its comparable games using the buttons below.</canvas>
    <div className="cs-map-caption"><span>DRAG TO ROTATE · HOVER TO EXPLORE</span><span>SCHEMATIC, NOT MARKET DISTANCE</span></div>
    <div className="cs-legend"><span><i className="cs-core-key"/> Your game</span><span><i className="cs-trait-key"/> Shared trait</span><span><i className="cs-game-key"/> Comparable</span><span><i className="cs-selected-key"/> Selected</span></div>
    {feature && <div className="cs-feature-info"><strong>{feature.label}</strong><span>Connected in {feature.evidence.length} saved {feature.evidence.length === 1 ? 'comparison' : 'comparisons'}.</span><button onClick={() => setFeature(null)} aria-label="Close shared trait">×</button></div>}
    <div className="cs-bottom"><div className="cs-rotate"><button className="cs-tool" aria-label="Rotate competitor globe left" onClick={() => renderer.current?.rotate(-.2)}><ArrowLeft size={14}/></button><button className="cs-tool" aria-label="Rotate competitor globe right" onClick={() => renderer.current?.rotate(.2)}><ArrowRight size={14}/></button></div><span className="cs-interaction-hint">{pinned ? 'DETAIL PINNED · SELECT ANOTHER GAME TO SWITCH' : 'SELECT A GAME TO KEEP ITS DETAILS OPEN'}</span></div>
    <div className="cs-game-selectors" role="group" aria-label="Choose a comparable game">{model.comparables.map((game, index) => <button key={game.id} title={game.name} aria-label={`Explore ${game.name}`} aria-pressed={selected === game.name} onFocus={() => preview(game.name)} onPointerEnter={event => { if (event.pointerType !== 'touch') preview(game.name); }} onClick={() => select(game.name)}><GameIcon game={game}/><span>{String(index + 1).padStart(2, '0')}</span>{game.name}</button>)}</div>
    <p id="competitor-map-help" className="cs-help">Connections summarize shared traits in your saved AI comparisons. Hover a game for its evidence; click to keep the detail open.</p>
  </div>;
}
