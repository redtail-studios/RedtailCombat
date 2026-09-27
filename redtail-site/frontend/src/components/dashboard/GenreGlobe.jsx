import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Pause, Play, RotateCcw } from 'lucide-react';
import { createLoreTopology } from '@/lib/competition/loreTopology';
import './competitor-sphere.css';

export default function GenreGlobe({ model, selected, onSelect }) {
  const canvas = useRef(null);
  const renderer = useRef(null);
  const callbacks = useRef({ onSelect });
  callbacks.current = { onSelect };
  const [moving, setMoving] = useState(true);
  const selectedId = model.comparables.find(g => g.name === selected)?.id;

  useEffect(() => {
    const graph = createLoreTopology(canvas.current, {
      model,
      colors: { background: '#101416', backgroundLift: '#142321', glow: '#b4ed68', grid: '#66847a', wire: '#78958a', relation: '#8fb3f5', core: '#e1ede6', feature: '#b4ed68', comparable: '#b4ed68', selected: '#ff5c60', text: '#d9e4de', muted: '#789087' },
      onHover: node => {
        if (!node || node.type !== 'comparable') return;
        const found = model.comparables.find(g => g.id === node.id);
        if (found) { callbacks.current.onSelect(found.name); graph.setFocus(node.id); }
      },
      onSelect: node => {
        if (node.type !== 'comparable') return;
        const found = model.comparables.find(g => g.id === node.id);
        if (found) callbacks.current.onSelect(found.name);
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
  useEffect(() => { renderer.current?.setFocus(selectedId); }, [selectedId, model]);
  useEffect(() => { renderer.current?.setMotion(moving); }, [moving, model]);

  const reset = () => { setMoving(true); renderer.current?.reset(); renderer.current?.setFocus(selectedId); };
  return <div className="competitor-sphere">
    <div className="cs-toolbar"><span>{model.comparables.length} CLOSEST GENRES</span><div className="cs-tools"><button className="cs-tool" onClick={() => setMoving(value => !value)} aria-label={moving ? 'Pause genre globe' : 'Rotate genre globe'}>{moving ? <Pause size={14}/> : <Play size={14}/>}</button><button onClick={reset} className="cs-tool" aria-label="Reset genre globe"><RotateCcw size={14}/></button></div></div>
    <canvas ref={canvas} className="cs-topology" tabIndex={0} role="group" aria-describedby="genre-map-help" onKeyDown={event => {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home'].includes(event.key)) {
        event.preventDefault(); setMoving(false);
        if (event.key === 'Home') reset();
        else renderer.current?.rotate(event.key === 'ArrowLeft' ? -.18 : event.key === 'ArrowRight' ? .18 : 0, event.key === 'ArrowUp' ? -.12 : event.key === 'ArrowDown' ? .12 : 0);
      }
    }}>Explore {model.core.label} and its five closest genres using the buttons below.</canvas>
    <div className="cs-map-caption"><span>DRAG TO ROTATE · HOVER TO EXPLORE</span><span>DISTANCE = INFERRED SIMILARITY</span></div>
    <div className="cs-bottom"><div className="cs-rotate"><button className="cs-tool" aria-label="Rotate genre globe left" onClick={() => renderer.current?.rotate(-.2)}><ArrowLeft size={14}/></button><button className="cs-tool" aria-label="Rotate genre globe right" onClick={() => renderer.current?.rotate(.2)}><ArrowRight size={14}/></button></div><span className="cs-interaction-hint">HOVER OR SELECT A GENRE TO SEE ITS FIT</span></div>
    <div className="cs-game-selectors" role="group" aria-label="Choose a genre">{model.comparables.map((g, index) => <button key={g.id} title={g.name} aria-label={`Explore ${g.name}`} aria-pressed={selected === g.name} onFocus={() => onSelect(g.name)} onPointerEnter={event => { if (event.pointerType !== 'touch') onSelect(g.name); }} onClick={() => onSelect(g.name)}><span>{String(index + 1).padStart(2, '0')}</span>{g.name}</button>)}</div>
    <p id="genre-map-help" className="cs-help">Distance from your game reflects inferred genre similarity, not demand or likelihood of success. Hover a genre to see its fit on the right.</p>
  </div>;
}
