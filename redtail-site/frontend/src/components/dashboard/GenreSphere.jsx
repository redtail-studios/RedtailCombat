import React, { useState } from 'react';
const COLORS = ['#B4FF39','#8FB3FF','#E9C779','#B49BDA','#E58A86'];
export default function GenreSphere({ name, genres, selected, onSelect }) {
  const [angle, setAngle] = useState(0);
  const [hovered, setHovered] = useState(null);
  const nodes = genres.map((g, i) => {
    const a = (-105 + i * 72 + angle) * Math.PI / 180;
    // Floor raised (was 65) so even a near-1.0 fit still clears the core's
    // own label at y=277 — that overlap is what swallowed one genre's dot.
    const radius = 100 + (1 - g.fit) * 130;
    const x = 360 + Math.cos(a) * radius, y = 240 + Math.sin(a) * radius;
    // Labels sit further out along the same radial line as their node,
    // instead of a fixed vertical offset — so a label never points back
    // toward the center and collides with the core's name underneath it.
    const lx = 360 + Math.cos(a) * (radius + 26), ly = 240 + Math.sin(a) * (radius + 26);
    return { g, i, a, x, y, lx, ly };
  });
  const hoveredNode = hovered != null ? nodes[hovered] : null;
  return <div className="p-4">
    <div className="relative">
      <svg viewBox="0 0 720 490" className="w-full" role="group" aria-label="Genre similarity sphere: shorter connections indicate closer genre fit">
        <defs><radialGradient id="genre-glow"><stop stopColor="#B4FF39" stopOpacity=".08"/><stop offset="1" stopColor="#B4FF39" stopOpacity="0"/></radialGradient></defs>
        <circle cx="360" cy="240" r="225" fill="url(#genre-glow)"/>
        {[65,120,175,225].map(r=><circle key={r} cx="360" cy="240" r={r} fill="none" stroke="#8FB3FF" strokeOpacity=".2" strokeDasharray="1 7"/>)}
        {[-60,-30,0,30,60].map(a=><ellipse key={a} cx="360" cy="240" rx={Math.max(30,225*Math.cos(a*Math.PI/180))} ry="225" transform={`rotate(${a+angle} 360 240)`} fill="none" stroke="#8FB3FF" strokeOpacity=".12" strokeDasharray="1 6"/>)}
        {nodes.map(({g,i,x,y,lx,ly})=>(
          <g key={g.name} role="button" tabIndex={0} aria-label={`Select ${g.name}${g.reason ? `: ${g.reason}` : ''}`} aria-pressed={selected===g.name}
            onClick={()=>onSelect(g.name)}
            onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(g.name);}}}
            onMouseEnter={()=>setHovered(i)} onMouseLeave={()=>setHovered(h=>h===i?null:h)}
            onFocus={()=>setHovered(i)} onBlur={()=>setHovered(h=>h===i?null:h)}
            className="cursor-pointer">
            <path d={`M360 240 L${x} ${y}`} stroke={COLORS[i]} strokeDasharray="3 6" strokeOpacity=".6"/>
            <circle cx={x} cy={y} r={selected===g.name?12:8} fill={COLORS[i]} fillOpacity={hovered===i?.4:.2} stroke={COLORS[i]} strokeWidth={hovered===i?2:1}/>
            <circle cx={x} cy={y} r="3" fill={COLORS[i]}/>
            <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fill={COLORS[i]} fontFamily="monospace" fontSize="13">{i+1}. {g.name}</text>
          </g>
        ))}
        <circle cx="360" cy="240" r="20" fill="#FF2E2E" fillOpacity=".12" stroke="#FF2E2E"/><circle cx="360" cy="240" r="5" fill="#FF2E2E"/><text x="360" y="277" textAnchor="middle" fill="#E2E2E2" fontFamily="monospace" fontSize="13">{name.slice(0,30)}</text>
        {!genres.length && <text x="360" y="460" textAnchor="middle" fill="#8FB3FF" fontFamily="monospace" fontSize="12">Analyse your document to place five genres.</text>}
      </svg>
      {hoveredNode && <div
        className="pointer-events-none absolute z-10 w-56 -translate-x-1/2 p-3 bg-ink/95 border font-mono text-[11px] leading-relaxed text-platinum/80 shadow-lg"
        style={{
          left: `${hoveredNode.x/720*100}%`,
          top: `${hoveredNode.y/490*100}%`,
          transform: `translate(-50%, ${hoveredNode.y < 245 ? '18px' : 'calc(-100% - 18px)'})`,
          borderColor: COLORS[hoveredNode.i],
        }}
      >
        <p className="font-pixel text-[9px] mb-1.5" style={{color: COLORS[hoveredNode.i]}}>{hoveredNode.g.name}</p>
        {hoveredNode.g.reason || 'No description available.'}
      </div>}
    </div>
    <label className="flex gap-4 font-mono text-[10px] text-platinum/50 items-center mt-3">ROTATE VIEW<input type="range" aria-label="Rotate genre sphere" min="-180" max="180" value={angle} onChange={e=>setAngle(Number(e.target.value))} className="flex-1 accent-[#B4FF39]"/></label>
  </div>;
}
