import { useMemo, useState } from 'react';
import { createComparisonMap } from '@/lib/competition/comparisonMap';
import GenreSphere from './GenreSphere';
import CompetitionGlobe from './CompetitionGlobe';
import CompetitorSphere from './CompetitorSphere';

const tabLabels=['Genre','Competition','Demographics'];
export default function CompetitionTabs({game,comparables,year,query,snapshot,regionalQuery,initialTab='Genre'}) {
  const [tab,setTab]=useState(initialTab);
  const [selectedGenre,setSelectedGenre]=useState('');
  const [selectedGame,setSelectedGame]=useState('');
  const [gamePinned,setGamePinned]=useState(false);
  const [selectedCountry,setSelectedCountry]=useState('');
  const genres=(game.genreFit?.genres||[]);
  const chosenGenre=genres.find(g=>g.name===selectedGenre)||genres[0];
  const competitors=useMemo(()=>comparables.slice(0,5),[comparables]);
  const comparisonMap=useMemo(()=>createComparisonMap(competitors,game.name),[competitors,game.name]);
  const chosenGame=competitors.find(g=>g.name===selectedGame)||competitors[0];
  const regions=(game.audienceRegions||[]).filter(r=>competitors.some(c=>c.name===r.competitor)&&Number.isFinite(r.latitude)&&Number.isFinite(r.longitude)&&Math.abs(r.latitude)<=90&&Math.abs(r.longitude)<=180&&r.source&&r.metric&&r.period).map(r=>({...r,name:`${r.competitor} · ${r.country}`}));
  const title=tab==='Genre'?'Where does your game belong?':tab==='Competition'?'Who shares your playing field?':'Where is your audience?';
  return <>
    <div className="flex flex-wrap justify-between items-center gap-4 mb-5"><div role="tablist" aria-label="Competition views" className="flex border border-white/15 max-w-full">{tabLabels.map((label,i)=><button key={label} id={`tab-${label}`} role="tab" aria-selected={tab===label} aria-controls="competition-panel" tabIndex={tab===label?0:-1} onKeyDown={e=>{if(['ArrowRight','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?2:(i+(e.key==='ArrowRight'?1:2))%3;setTab(tabLabels[next]);document.getElementById(`tab-${tabLabels[next]}`)?.focus();}}} onClick={()=>{setTab(label);if(label==='Demographics'&&!regionalQuery.data&&!regionalQuery.isFetching)regionalQuery.refetch();}} className={`px-3 sm:px-5 py-4 font-mono text-xs border-b-2 ${tab===label?'text-moss border-moss bg-moss/5':'text-platinum/50 border-transparent hover:text-platinum'}`}>{label}</button>)}</div></div>
    <div id="competition-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className={`grid ${tab==='Competition'?'lg:grid-cols-[minmax(0,1fr)_280px]':'lg:grid-cols-[minmax(0,1.65fr)_minmax(260px,1fr)]'} gap-5`}>
      <section className="bg-panel border border-white/10 pixel-clip overflow-hidden"><div className="p-5 sm:p-6 border-b border-white/10"><p className="font-mono text-[10px] text-moss tracking-widest mb-3">01 / {tab.toUpperCase()}</p><h2 className="font-pixel text-base sm:text-xl leading-relaxed">{title}</h2><p className="font-mono text-xs text-platinum/50 mt-3 leading-relaxed">{tab==='Genre'?'Your game, connected to its five closest genres. Shorter lines indicate stronger similarity.':tab==='Competition'?'Explore the shared traits connecting your game to its closest comparables.':'Where each of your five closest competitor games is searched the most — not where your own game would do well, and not where those games were made.'}</p></div>
        {tab==='Genre' && <><GenreSphere name={game.name} genres={genres} selected={chosenGenre?.name} onSelect={setSelectedGenre}/><p className="px-5 pb-5 font-mono text-[10px] text-platinum/40">Distance = inferred genre similarity, not demand or likelihood of success.</p></>}
        {tab==='Competition' && <>
          {query.isFetching && <p role="status" className="px-5 pt-5 font-mono text-xs text-moss">Loading comparisons…</p>}
          {(query.isError||snapshot?.error)&&<p role="alert" className="p-5 font-mono text-xs text-pulse">Comparison data unavailable. Retry the analysis to load comparisons.</p>}
          {!competitors.length&&!query.isFetching&&<p className="font-mono text-sm text-platinum/50 py-16 text-center">No competitor records for this game yet.</p>}
          {!!competitors.length && <CompetitorSphere model={comparisonMap} selected={chosenGame?.name} pinned={gamePinned} onPreview={setSelectedGame} onSelect={name=>{setSelectedGame(name);setGamePinned(true);}} onUnpin={()=>setGamePinned(false)}/>}
        </>}
        {tab==='Demographics' && <><div className="p-5 font-mono text-xs text-platinum/60"><p>Each score is one competitor game's own Google search interest by country for {year}, normalized to that game's own peak (100 = its single most-interested country). It shows where that one competitor is searched the most — never your game's odds there, never a count of players, and never where a game's studio is based.</p><button disabled={regionalQuery.isFetching||!competitors.length} onClick={()=>regionalQuery.refetch()} className="mt-3 text-moss disabled:opacity-40">{regionalQuery.isFetching?'Fetching live regional interest…':'Fetch regional interest ↻'}</button>{regionalQuery.isError&&<p role="alert" className="text-pulse">{regionalQuery.error.message}</p>}{game.regionalCoverage?.length>0 && <details className="mt-3"><summary className="cursor-pointer text-[10px]">Data coverage</summary>{game.regionalCoverage.map(c=><p key={c.competitor} className="mt-2 text-[10px]">{c.competitor}: {c.status}</p>)}</details>}</div><CompetitionGlobe games={regions} gameName={game.name} selected={selectedCountry} onSelect={setSelectedCountry}/><p className="font-mono text-[10px] text-platinum/40 px-5 pb-5">Scores aren't comparable across different competitors — each is relative only to its own peak country.</p></>}
      </section>
      <aside className="space-y-4">
        {tab!=='Demographics' && <section className={`p-5 bg-panel border border-white/10 ${tab==='Competition'?'cs-detail font-mono':''}`} aria-label={tab==='Competition'?'Competitor detail':'Genre fit'} aria-live="polite"><p className="font-mono text-[10px] text-pulse tracking-widest mb-4">{tab==='Genre'?'GENRE FIT':tab==='Competition'?'COMPETITOR DETAIL':'REGIONAL EVIDENCE'}</p>
          {tab==='Genre'&&(chosenGenre?<><div className="flex items-center justify-between gap-3 mb-4"><h3 className="font-pixel text-sm text-moss">{chosenGenre.name}</h3>{genres[0]?.name===chosenGenre.name && <span className="font-pixel text-xs text-pulse tracking-wider flex-shrink-0">CLOSEST</span>}</div><p className="font-mono text-xs leading-relaxed text-platinum/70">{chosenGenre.reason}</p><blockquote className="mt-5 border-l border-moss/40 pl-3 text-xs font-mono text-platinum/50">{chosenGenre.evidence}</blockquote><p className="font-mono text-[10px] text-platinum/35 mt-4">Relative fit {typeof chosenGenre.fit === 'number' ? chosenGenre.fit.toFixed(2) : '—'} / 1 · not measured demand.</p></>:<p className="font-mono text-xs leading-relaxed text-platinum/60">Genre analysis is not available for this game yet.</p>)}
          {tab==='Competition'&&(chosenGame?<>
            <div className="cs-detail-state"><span>{gamePinned?'PINNED FOR READING':'HOVER A GAME TO EXPLORE'}</span>{gamePinned&&<button onClick={()=>setGamePinned(false)}>Unpin details</button>}</div>
            <h3 className="cs-detail-title font-pixel text-sm text-moss">{chosenGame.name}</h3>
            <div className="cs-detail-metrics"><div><strong>0{competitors.indexOf(chosenGame)+1}</strong><span>AI-ranked match</span></div><div><strong>{chosenGame.reviewCount ?? chosenGame.mentions ?? '—'}</strong><span>Reviews in the dataset</span></div></div>
            <div className="cs-detail-traits">{comparisonMap.features.filter(trait=>trait.evidence.some(item=>item.game===chosenGame.name)).map(trait=><span key={trait.id} title={trait.evidence.find(item=>item.game===chosenGame.name)?.quote}>{trait.label}</span>)}</div><p className="cs-detail-label">WHY THIS GAME IS COMPARABLE</p><p className="cs-detail-reason">{chosenGame.reason}</p>
            {chosenGame.quote && <details key={chosenGame.name}><summary>Read the source excerpt ↗</summary><blockquote>{chosenGame.quote}</blockquote></details>}
            <p className="text-[10px] text-platinum/40 mt-5">{({googleplay:'Google Play',steam:'Steam',steamtrending:'Steam',appstore:'App Store',rawg:'RAWG'})[chosenGame.source]||chosenGame.source} · {year}</p>
            <p className="text-[9px] text-platinum/35 mt-2 leading-relaxed">Matches are inferred from your game document. Saved reviews are not total players or sales.</p>
          </>:<p className="font-mono text-xs text-platinum/50">Competitor details appear when source records are available.</p>)}
        </section>}
        {tab==='Genre'&&genres.map((g,i)=><button key={g.name} onClick={()=>setSelectedGenre(g.name)} aria-pressed={chosenGenre?.name===g.name} className={`w-full p-4 text-left border font-mono text-xs ${chosenGenre?.name===g.name?'border-moss/50 text-moss':'border-white/10 text-platinum/60'}`}><div className="flex items-center justify-between gap-2"><span><span className="mr-3 text-platinum/30">0{i+1}</span>{g.name}</span>{i===0 && <span className="font-pixel text-[10px] text-pulse tracking-wider flex-shrink-0">CLOSEST</span>}</div><span className="block mt-2 text-platinum/40 text-[10px]">Relative fit {typeof g.fit === 'number' ? g.fit.toFixed(2) : '—'} / 1</span></button>)}
        {tab==='Demographics' && <p className="font-mono text-xs text-platinum/60">{regions.length?'Select a country to see which competitors peak there, and by how much (relative to each one\'s own worldwide high).':regionalQuery.isFetching?'Loading regional data…':'No regional measurements available for these games.'}</p>}
        {tab==='Demographics'&&[...new Set(regions.map(r=>r.country))].map(country=><button key={country} aria-pressed={selectedCountry===country} onClick={()=>setSelectedCountry(country)} className="w-full text-left p-3 border border-white/10 font-mono text-xs text-platinum/60 hover:border-moss/40">{country} · {new Set(regions.filter(r=>r.country===country).map(r=>r.competitor)).size} games</button>)}
      </aside>
    </div>
  </>;
}
