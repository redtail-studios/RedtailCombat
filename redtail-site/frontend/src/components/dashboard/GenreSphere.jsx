import React, { useState } from 'react';
const COLORS = ['#B4FF39','#8FB3FF','#E9C779','#B49BDA','#E58A86'];
export default function GenreSphere({ name, genres, selected, onSelect }) {
  const [angle, setAngle] = useState(0);
  return <div className="p-4"><svg viewBox="0 0 720 490" className="w-full" role="group" aria-label="Genre similarity sphere: shorter connections indicate closer genre fit">
    <defs><radialGradient id="genre-glow"><stop stopColor="#B4FF39" stopOpacity=".08"/><stop offset="1" stopColor="#B4FF39" stopOpacity="0"/></radialGradient></defs>
    <circle cx="360" cy="240" r="225" fill="url(#genre-glow)"/>
    {[65,120,175,225].map(r=><circle key={r} cx="360" cy="240" r={r} fill="none" stroke="#8FB3FF" strokeOpacity=".2" strokeDasharray="1 7"/>)}
    {[-60,-30,0,30,60].map(a=><ellipse key={a} cx="360" cy="240" rx={Math.max(30,225*Math.cos(a*Math.PI/180))} ry="225" transform={`rotate(${a+angle} 360 240)`} fill="none" stroke="#8FB3FF" strokeOpacity=".12" strokeDasharray="1 6"/>)}
    {genres.map((g,i)=>{const a=(-105+i*72+angle)*Math.PI/180;const radius=65+(1-g.fit)*160;const x=360+Math.cos(a)*radius,y=240+Math.sin(a)*radius;return <g key={g.name} role="button" tabIndex={0} aria-label={`Select ${g.name}`} aria-pressed={selected===g.name} onClick={()=>onSelect(g.name)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(g.name);}}} className="cursor-pointer"><path d={`M360 240 L${x} ${y}`} stroke={COLORS[i]} strokeDasharray="3 6" strokeOpacity=".6"/><circle cx={x} cy={y} r={selected===g.name?12:8} fill={COLORS[i]} fillOpacity=".2" stroke={COLORS[i]}/><circle cx={x} cy={y} r="3" fill={COLORS[i]}/><text x={x} y={y-22} textAnchor="middle" fill={COLORS[i]} fontFamily="monospace" fontSize="13">{i+1}. {g.name}</text></g>})}
    <circle cx="360" cy="240" r="20" fill="#FF2E2E" fillOpacity=".12" stroke="#FF2E2E"/><circle cx="360" cy="240" r="5" fill="#FF2E2E"/><text x="360" y="277" textAnchor="middle" fill="#E2E2E2" fontFamily="monospace" fontSize="13">{name.slice(0,30)}</text>
    {!genres.length && <text x="360" y="460" textAnchor="middle" fill="#8FB3FF" fontFamily="monospace" fontSize="12">Analyse your document to place five genres.</text>}
  </svg><label className="flex gap-4 font-mono text-[10px] text-platinum/50 items-center">ROTATE VIEW<input type="range" aria-label="Rotate genre sphere" min="-180" max="180" value={angle} onChange={e=>setAngle(Number(e.target.value))} className="flex-1 accent-[#B4FF39]"/></label></div>;
}
