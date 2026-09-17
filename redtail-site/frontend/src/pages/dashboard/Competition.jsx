import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, Globe2, ChevronRight } from 'lucide-react';
import { useLoreReports } from '@/lib/LoreReportsContext';
import { useDashboardAuth } from '@/lib/DashboardAuthContext';
import CompetitionTabs from '@/components/dashboard/CompetitionTabs';
import DecisionWorkspace from '@/components/dashboard/DecisionWorkspace';
import MarketWelcome from '@/components/dashboard/MarketWelcome';

const button = 'inline-flex items-center justify-center gap-2 px-4 py-3 bg-pulse text-ink font-mono text-xs pixel-clip-sm hover:opacity-90';
export default function Competition() {
  const { gameId } = useParams();
  return <GameWorkspace key={gameId || 'choose-game'} routedGameId={gameId}/>;
}
function GameWorkspace({routedGameId}) {
  const [section, setSection] = useState('competition');
  const { portfolio, reports, loaded, saveError } = useLoreReports();
  // The nav's "Competition" link (no gameId in the URL) used to just show the
  // generic top-20-trending globe forever, even once the studio has real
  // games — once they have at least one, default straight to its real
  // competitor data instead, with a picker if there's more than one.
  const [pickedGameId, setPickedGameId] = useState('');
  const isLanding = !routedGameId;
  const gameId = routedGameId || pickedGameId || portfolio[0]?.id || '';
  const game = portfolio.find(g => g.id === gameId);
  const report = reports.find(r => r.id === game?.lastReportId);
  const { dashboardPassword, dashboardUser } = useDashboardAuth();
  const year = '2026';
  const credentials = {username: dashboardUser?.username, password: dashboardPassword, gameId, year: Number(year), cachedOnly: !!report && !game?.documentId};
  const query = useQuery({
    queryKey: ['workspace', dashboardUser?.username, gameId, year], enabled: !!game && !!dashboardPassword,
    staleTime: 5 * 60 * 1000, retry: false,
    queryFn: async ({ signal }) => {
      const response = await fetch('/api/lore/workspace-analysis', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(credentials), signal});
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Analysis unavailable.');
      return data;
    },
  });
  const regionalQuery = useQuery({
    queryKey: ['workspace-regions', dashboardUser?.username, gameId, year], enabled:false, retry:false, staleTime:86400000,
    queryFn: async () => {
      const response=await fetch('/api/lore/workspace-regions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)});
      const data=await response.json();if(!response.ok)throw new Error(data.error);return data;
    }
  });
  const snapshot = query.data;
  const comparables = query.data?.competitors || [];
  const enrichedGame = {...game, ...query.data, ...regionalQuery.data};
  if (!loaded) return <div className="p-8 font-mono text-sm text-platinum/60" role="status">Loading your games…</div>;
  if (isLanding && portfolio.length === 0) return <div className="max-w-[1500px] mx-auto p-4 sm:p-8"><MarketWelcome/></div>;
  if (!game) return <div className="max-w-3xl mx-auto px-6 py-20 text-center"><Globe2 className="mx-auto w-12 h-12 text-pulse mb-8"/><h1 className="font-pixel text-xl text-platinum mb-5">{routedGameId ? 'Game not found' : 'Your game starts here.'}</h1><p className="font-mono text-sm text-platinum/50 leading-relaxed mb-8">{routedGameId ? 'Choose a saved game from your portfolio or upload a new game.' : 'Upload your game design document to create your Competition workspace and explore games in its genre.'}</p><Link className={button} to="/dashboard/analyze?tab=game"><Plus size={16}/>Add your game</Link><Link to="/dashboard/portfolio" className="block mt-6 font-mono text-xs text-platinum/60 underline">View portfolio</Link></div>;
  return <div className="max-w-[1500px] mx-auto p-4 sm:p-8 text-platinum">
    <div className="font-mono text-[10px] text-platinum/40 flex items-center gap-2 mb-6"><Link to="/dashboard/portfolio" className="hover:text-platinum">MY GAMES</Link><ChevronRight size={12}/><span className="truncate">{game.name}</span></div>
    <header className="flex flex-wrap items-end justify-between gap-5 mb-8">
      <div><p className="font-mono text-[10px] text-moss tracking-[.2em] uppercase mb-3">YOUR GAME / MARKET INTELLIGENCE</p><h1 className="font-pixel text-xl sm:text-3xl leading-relaxed break-words">{game.name}<span className="text-pulse">_</span></h1></div>
      <div className="flex items-center gap-3">
        {isLanding && portfolio.length > 1 && (
          <select
            aria-label="Choose which game to view"
            value={gameId}
            onChange={(e) => setPickedGameId(e.target.value)}
            className="font-mono text-xs bg-panel border border-white/15 px-3 py-3 text-platinum hover:border-pulse/50"
          >
            {portfolio.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        )}
        <Link to="/dashboard/analyze?tab=game" className="font-mono text-xs border border-white/15 px-4 py-3 hover:border-pulse flex items-center gap-2"><Plus size={14}/>Add a game</Link>
      </div>
    </header>
    <nav aria-label="Game workspace sections" className="flex flex-wrap gap-2 items-center border-y border-white/10 py-4 mb-7">{[['competition','01. Competition'],['experience','02. Player experience'],['focus','03. Your focus'],['redesign','04. Redesign']].map(([id,label]) => <button key={id} aria-current={section === id ? 'page' : undefined} onClick={()=>setSection(id)} className={`font-mono text-xs px-4 py-3 border ${section === id ? 'bg-pulse/10 border-pulse/40 text-pulse' : 'border-white/10 text-platinum/60 hover:border-white/30'}`}>{label}</button>)}</nav>
    {saveError && <p role="alert" className="mb-4 text-pulse font-mono text-xs">{saveError}</p>}
    {query.isFetching && <p role="status" className="mb-5 font-mono text-sm text-moss">Analysing {game.name} against market data. The first analysis can take a minute.</p>}
    {query.isError && <p role="alert" className="mb-5 border border-pulse/40 bg-pulse/5 p-5 font-mono text-sm text-pulse">Analysis for {game.name} could not finish: {query.error.message} <button className="underline" onClick={()=>query.refetch()}>Retry analysis</button></p>}
    {section === 'competition' && query.data?.positioning && query.data?.genreFit && <section className="mb-6 p-5 border border-moss/20 bg-panel"><h2 className="font-pixel text-sm mb-3">Why would someone choose your game?</h2><p className="font-mono text-xs text-platinum/70 leading-relaxed">{query.data.positioning}</p><p className="font-mono text-[10px] text-platinum/40 mt-3">AI interpretation of {query.data.genreFit?.document} · {query.data.genreFit?.model} · {query.data.analysedAt ? new Date(query.data.analysedAt).toLocaleString() : ''}</p></section>}
    {section === 'competition' && (!query.isPending && !query.isError) && <CompetitionTabs regionalQuery={regionalQuery} key={`${game.id}:${year}`} game={enrichedGame} comparables={comparables} year={year} query={query} snapshot={snapshot} initialTab={isLanding ? 'Competition' : 'Genre'}/>}
    {query.data && <DecisionWorkspace key={`${game.id}:${query.data.analysedAt}`} credentials={{...credentials, analysisId: query.data.analysisId}} analysis={query.data} section={section} onNavigate={setSection}/>}

  </div>;
}
