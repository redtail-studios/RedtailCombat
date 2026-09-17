import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import WORLD_COUNTRIES from '@/lib/competition/worldCountries.json';

// Real 110m-resolution country borders (Natural Earth via world-atlas,
// simplified with Ramer-Douglas-Peucker) instead of a handful of hand-drawn
// continent blobs — every country reads as an actual bordered shape, not a
// rough outline. A curated subset gets a label so the world view reads like
// an annotated blueprint even before any regional data has been fetched.
const MAJOR_COUNTRIES = new Set([
  'United States of America', 'Canada', 'Brazil', 'Argentina', 'United Kingdom',
  'France', 'Germany', 'Spain', 'Italy', 'Russia', 'China', 'Japan',
  'South Korea', 'India', 'Australia', 'Indonesia', 'Mexico', 'Nigeria',
  'Egypt', 'South Africa', 'Saudi Arabia', 'Turkey', 'Sweden', 'Poland',
  'Ukraine', 'New Zealand', 'Vietnam', 'Thailand', 'Philippines',
]);
const LABELED = WORLD_COUNTRIES.filter(c => MAJOR_COUNTRIES.has(c.name));

const rad = Math.PI / 180;
function project(lon, lat, rotation, tilt = 0) {
  const a = (lon + rotation) * rad, b = lat * rad, t = tilt * rad;
  return { x: 360 + 226 * Math.cos(b) * Math.sin(a), y: 270 - 226 * (Math.sin(b)*Math.cos(t)-Math.cos(b)*Math.cos(a)*Math.sin(t)), z: Math.sin(b)*Math.sin(t)+Math.cos(b)*Math.cos(a)*Math.cos(t) };
}
function line(points, rotation, tilt) {
  let visible = false;
  return points.map(([lon, lat]) => {
    const p = project(lon, lat, rotation, tilt);
    if (p.z < 0) { visible = false; return ''; }
    const command = visible ? 'L' : 'M'; visible = true;
    return `${command}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
  }).join(' ');
}
const GRID = [
  ...[-60,-30,0,30,60].map(lat => Array.from({length:121},(_,i)=>[-180+i*3,lat])),
  ...Array.from({length:12},(_,i)=>Array.from({length:61},(_,j)=>[i*30-180,-90+j*3])),
];

export default function CompetitionGlobe({ games, selected, onSelect, gameName }) {
  const [rotation, setRotation] = useState(15);
  const [playing, setPlaying] = useState(true);
  const drag = useRef(null);
  const countries = [...new Map(games.map(g=>[g.country,{name:g.country,latitude:g.latitude,longitude:g.longitude}])).values()];
  const country = countries.find(c=>c.name===selected);
  const countryGames = games.filter(g=>g.country===country?.name);
  const longitude = country?.longitude;
  const initialLongitude = countries[0]?.longitude;
  useEffect(()=>{const target=Number.isFinite(longitude)?longitude:initialLongitude;if(Number.isFinite(target)){setRotation(-target);setPlaying(false);}},[selected,longitude,initialLongitude]);
  useEffect(()=>{
    if(!playing)return;
    const timer=setInterval(()=>setRotation(r=>(r+.35)%360),40);
    return ()=>clearInterval(timer);
  },[playing]);
  const tilt = country?.latitude || 0;
  const width = country ? 300 : 720, height = width*550/720;
  const left = 360-width/2, top = 270-height/2;
  const reset = ()=>{onSelect('');setRotation(15);setPlaying(true);};
  const borders = useMemo(() => WORLD_COUNTRIES.map(c => ({
    name: c.name,
    d: c.rings.map(ring => line([...ring, ring[0]], rotation, tilt)).join(' '),
  })), [rotation, tilt]);
  return <div>
    <div className="flex flex-wrap justify-between gap-3 items-center px-5 pt-4 font-mono text-[10px] text-platinum/50">
      <span>{country ? `${country.name.toUpperCase()} · COUNTRY VIEW · 2.4×` : 'DRAG TO EXPLORE · CLICK A COUNTRY DOT'}</span>
      <div className="flex gap-2">
        {country && <button onClick={reset} className="px-3 border border-moss/40 text-moss">Back to world</button>}
        <button aria-label={playing?'Pause globe':'Rotate globe'} onClick={()=>setPlaying(!playing)} className="p-2 border border-white/15 hover:text-moss">{playing?<Pause size={13}/>:<Play size={13}/>}</button>
        <button aria-label="Reset globe" onClick={reset} className="p-2 border border-white/15 hover:text-moss"><RotateCcw size={13}/></button>
      </div>
    </div>
    <div className="relative w-full aspect-[720/550] overflow-hidden" role="group" aria-label={`Audience country map for ${gameName}`}>
      <svg viewBox={`${left} ${top} ${width} ${height}`} className="absolute inset-0 w-full h-full touch-none select-none" aria-hidden="true"
        onPointerDown={e=>{drag.current={x:e.clientX,rotation};e.currentTarget.setPointerCapture(e.pointerId);setPlaying(false);}}
        onPointerMove={e=>{if(drag.current)setRotation(drag.current.rotation+(e.clientX-drag.current.x)*.45);}}
        onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}}>
        <defs>
          <radialGradient id="competition-ocean" cx="35%" cy="30%"><stop offset="0" stopColor="#0f2436"/><stop offset=".75" stopColor="#081420"/><stop offset="1" stopColor="#04080d"/></radialGradient>
        </defs>
        <circle cx="360" cy="270" r="226" fill="url(#competition-ocean)" stroke="#8FB3FF" strokeOpacity=".3"/>
        {GRID.map((p,i)=><path key={i} d={line(p,rotation,tilt)} fill="none" stroke="#8FB3FF" strokeOpacity=".08" strokeWidth=".6"/>)}
        {borders.map(b=><path key={b.name} d={b.d} fill="none" stroke="#BFE3FF" strokeOpacity=".5" strokeWidth=".85" strokeLinejoin="round"/>)}
      </svg>
      {!country && LABELED.map(c=>{
        const point=project(c.centroid[0],c.centroid[1],rotation,tilt);
        const x=(point.x-left)/width*100,y=(point.y-top)/height*100;
        if(point.z<0.08 || x<2 || x>98 || y<2 || y>98)return null;
        return <span key={c.name} className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 font-mono text-[8px] uppercase tracking-wider text-[#BFE3FF]/50 whitespace-nowrap" style={{left:`${x}%`,top:`${y}%`}}>{c.name}</span>;
      })}
      {countries.map(c=>{
        const point=project(c.longitude,c.latitude,rotation,tilt);
        const x=(point.x-left)/width*100,y=(point.y-top)/height*100;
        if(point.z<0 || x<0 || x>100 || y<0 || y>100)return null;
        const active=c.name===selected;
        const count=new Set(games.filter(g=>g.country===c.name).map(g=>g.competitor)).size;
        return <button key={c.name} type="button" aria-label={`Explore ${c.name}, ${count} ${count===1?'game':'games'}`} aria-pressed={active}
          onClick={()=>{setRotation(-c.longitude);setPlaying(false);onSelect(c.name);}}
          className="absolute z-10 w-11 h-11 -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-moss group"
          style={{left:`${x}%`,top:`${y}%`}}>
          <span className={`pointer-events-none absolute w-7 h-7 rounded-full border motion-safe:animate-pulse ${active?'border-pulse bg-pulse/20':'border-moss bg-moss/10 group-hover:bg-moss/30'}`}/>
          <span className={`pointer-events-none w-2 h-2 rounded-full ${active?'bg-pulse':'bg-moss'}`}/>
          <span className={`pointer-events-none absolute bottom-10 whitespace-nowrap bg-ink/90 px-2 py-1 font-mono text-[10px] ${active?'text-pulse':'text-platinum'}`}>{c.name} · {count}</span>
        </button>;
      })}
    </div>
    {country && <section aria-live="polite" aria-label={`Games in ${country.name}`} className="mx-5 mb-5 p-4 border border-moss/30 bg-ink">
      <h3 className="font-pixel text-sm text-moss mb-3">Games in {country.name}</h3>
      <p className="font-mono text-[10px] text-platinum/50 mb-4">Competitors with a sourced regional observation here. Missing games are not evidence of no audience.</p>
      <div className="space-y-3">{countryGames.map(g=><div key={g.competitor} className="border-t border-white/10 pt-3">
        <p className="font-mono text-xs text-platinum">{g.competitor}</p>
        <p className="font-mono text-xs text-moss mt-1">Search interest: {g.value ?? 'Unavailable'} / 100</p>
        <p className="font-mono text-[10px] text-platinum/40 mt-1">{g.period}</p>
        {g.sourceUrl && <a className="font-mono text-[10px] text-platinum/60 underline" href={g.sourceUrl} target="_blank" rel="noreferrer">View source ↗</a>}
      </div>)}</div>
    </section>}
    <div className="px-5 pb-5"><label className="flex items-center gap-4 text-[10px] font-mono text-platinum/50">ROTATE<input aria-label="Globe rotation" type="range" min="-180" max="180" value={((rotation+180)%360+360)%360-180} onChange={e=>{setPlaying(false);setRotation(Number(e.target.value));}} className="flex-1 accent-[#B4FF39]"/></label></div>
  </div>;
}
