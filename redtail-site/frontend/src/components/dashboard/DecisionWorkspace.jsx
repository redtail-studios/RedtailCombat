import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Check, Clock3, ExternalLink, Loader2, X } from 'lucide-react';
import GameRedesign from './GameRedesign';
import WorkspaceNotice from './WorkspaceNotice';
import { workspacePost } from '@/lib/workspaceApi';
import './decision-workspace.css';

const sources = { googleplay: 'Google Play', steam: 'Steam', appstore: 'App Store' };
const labels = { concern: 'Concern', praise: 'Praise', mixed: 'Both', open: 'Undecided', focus: 'Focus now', later: 'Later' };
const dateLabel = (date) => date ? new Date(`${date.slice(0, 10)}T12:00:00Z`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : 'Date unavailable';
function reviewWeek(date) {
  const day = new Date(date.slice(0, 10));
  day.setUTCDate(day.getUTCDate() - (day.getUTCDay() + 6) % 7);
  return day.toISOString().slice(0, 10);
}

function Ring({ count, total, label, accent = '#b8ff42' }) {
  const value = total ? count / total : 0;
  return <svg viewBox="0 0 100 100" role="img" aria-label={label} className="dw-ring"><circle cx="50" cy="50" r="40" fill="none" stroke="#2b2c31" strokeWidth="6"/><circle cx="50" cy="50" r="40" fill="none" stroke={accent} strokeWidth="6" pathLength="100" strokeDasharray={`${value * 100} 100`} transform="rotate(-90 50 50)" strokeLinecap="round"/><text x="50" y="49" textAnchor="middle" fill="#e3e3dc" fontSize="23">{total ? `${Math.round(value * 100)}%` : '—'}</text><text x="50" y="65" textAnchor="middle" fill="#aaa" fontSize="8">{total ? `${count} / ${total}` : 'NO RATINGS'}</text></svg>;
}
function FocusControl({ topic, value, disabled, onSave }) {
  return <div className="dw-priority" role="group" aria-label={`Priority for ${topic.label}`}>{['focus', 'later', 'open'].map(status => <button key={status} disabled={disabled} aria-pressed={value === status} onClick={() => onSave(topic.id, status)}>{status === 'focus' && <Check size={11}/>} {status === 'later' && <Clock3 size={11}/>} {labels[status]}</button>)}</div>;
}
function Evidence({ selection, competitors, onClose }) {
  const game = competitors.find(c => c.id === selection.cell.competitorId);
  return <aside className="dw-evidence" aria-label="Selected review evidence"><div className="dw-row"><div><span className="dw-eyebrow">REVIEW EVIDENCE</span><h3>{selection.topic.label} · {game.name}</h3></div><button className="dw-icon" aria-label="Close review evidence" onClick={onClose}><X size={18}/></button></div>{selection.cell.evidence.map(item => {
    const review = game.reviews.find(r => r.id === item.reviewId);
    return <div className="dw-quote" key={item.reviewId}><span className={`dw-mark ${item.kind}`}>{labels[item.kind]}</span><blockquote>“{item.quote}”</blockquote><div className="dw-meta">{sources[game.source] || game.source} · {dateLabel(review?.date)}{review?.score ? ` · ${review.score}/5 stars` : ''}</div><details><summary>Read full saved review</summary><p>{review?.text}</p></details>{game.sourceUrl && <a href={game.sourceUrl} target="_blank" rel="noreferrer">Open game’s store page <ExternalLink size={11}/></a>}</div>;
  })}<div className="dw-document"><span className="dw-eyebrow">IN YOUR DESIGN</span><blockquote>“{selection.topic.documentQuote}”</blockquote><p>{selection.topic.designConnection}</p></div></aside>;
}
function ReviewTimeline({ competitors }) {
  const [selected, setSelected] = useState(null);
  const dated = competitors.flatMap(c => c.reviews.filter(r => r.date).map(r => ({ ...r, game: c })));
  if (!dated.length) return <WorkspaceNotice>These saved reviews have no dates. A review timeline will appear when dated reviews are available.</WorkspaceNotice>;
  const times = dated.map(r => new Date(reviewWeek(r.date)).getTime());
  const min = Math.min(...times), max = Math.max(...times), range = max - min || 86400000;
  const plotted = competitors.map(game => ({ game, groups: Object.values(game.reviews.filter(r => r.date).reduce((groups, review) => {
    const key = reviewWeek(review.date);
    if (!groups[key]) groups[key] = { date: key, reviews: [], game };
    groups[key].reviews.push(review); return groups;
  }, {})) }));
  return <div><div className="dw-row dw-subheading"><div><h3>When did players say it?</h3><p>Each dot opens the saved reviews from that week.</p></div><span className="dw-meta">{dated.length} dated · {competitors.reduce((n, c) => n + c.reviewCount - c.datedReviews, 0)} undated</span></div><div className="dw-timeline-scroll"><div className="dw-timeline"><div className="dw-timeline-axis"><span>{dateLabel(new Date(min).toISOString())}</span><span>{dateLabel(new Date(max).toISOString())}</span></div>{plotted.map(({ game, groups }) => <div className="dw-timeline-lane" key={game.id}><span>{game.name}</span><div className="dw-track">{groups.map(group => <button key={group.date} className={selected?.game.id === game.id && selected.date === group.date ? 'selected' : ''} style={{ left: `${4 + (new Date(group.date).getTime() - min) / range * 92}%`, width: Math.min(24, 10 + Math.sqrt(group.reviews.length) * 2), height: Math.min(24, 10 + Math.sqrt(group.reviews.length) * 2) }} aria-label={`${game.name}, week of ${dateLabel(group.date)}, ${group.reviews.length} reviews`} title={`Week of ${dateLabel(group.date)} · ${group.reviews.length} reviews`} onClick={() => setSelected(group)}/>)}{!groups.length && <small>No dated reviews</small>}</div></div>)}</div></div><p className="dw-meta">Dot size reflects the number of saved reviews that week. This is review coverage, not sales or player growth.</p>{selected && <div className="dw-timeline-reviews"><div className="dw-row"><h3>{selected.game.name} · Week of {dateLabel(selected.date)}</h3><button className="dw-icon" onClick={() => setSelected(null)} aria-label="Close dated reviews"><X size={16}/></button></div>{selected.reviews.map(r => <div className="dw-quote" key={r.id}><span className="dw-meta">{r.score ? `${r.score}/5 stars` : r.recommended === true ? 'Recommended on Steam' : r.recommended === false ? 'Not recommended on Steam' : 'No rating'}</span><p>{r.text}</p></div>)}</div>}</div>;
}
export default function DecisionWorkspace({ credentials, analysis, section, onNavigate }) {
  const client = useQueryClient();
  const [view, setView] = useState('compare');
  const [selection, setSelection] = useState(null);
  useEffect(() => setSelection(null), [section]);
  const queryKey = ['player-research', credentials.username, credentials.gameId, analysis?.analysedAt];
  const research = useQuery({ queryKey, enabled: !!analysis && section !== 'competition', staleTime: 5 * 60 * 1000, retry: false, refetchOnWindowFocus: false, queryFn: ({ signal }) => workspacePost('workspace-feedback', credentials, {}, signal) });
  /** @param {{topicId: string, status: string}} choice */
  const saveChoice = (choice) => workspacePost('workspace-focus', credentials, { fingerprint: research.data.fingerprint, ...choice });
  const focus = useMutation({ mutationFn: saveChoice, onSuccess: state => client.setQueryData(queryKey, { ...research.data, focus: state }) });
  const data = research.data;
  const priorities = data?.focus.priorities || {};
  const topics = data?.topics || [];
  const focused = topics.filter(t => priorities[t.id] === 'focus');
  const later = topics.filter(t => priorities[t.id] === 'later');
  const save = (topicId, status) => focus.mutate({ topicId, status });
  if (section === 'competition') return null;
  return <div className="decision-workspace">
    {section === 'redesign' ? <GameRedesign credentials={credentials} research={research} focused={focused} onFocus={() => onNavigate('focus')}/> : <>
      <header className="dw-heading"><span className="dw-eyebrow">{section === 'focus' ? '03 / YOUR FOCUS' : '02 / PLAYER EXPERIENCE'}</span><h2>{section === 'focus' ? 'What will you work on next?' : 'What do players love — and struggle with?'}</h2><p>{section === 'focus' ? 'Your choices become a test plan and guide your game’s redesign.' : 'Compare your closest games, read the evidence, and choose what matters to your design.'}</p></header>
      {research.isPending && <WorkspaceNotice><Loader2 size={16} className="animate-spin"/>Reading your document and comparable-game reviews. First analysis can take a minute.</WorkspaceNotice>}
      {research.isError && <WorkspaceNotice error>{research.error.message} <button onClick={() => research.refetch()}>Retry player research</button></WorkspaceNotice>}
      {focus.isError && <WorkspaceNotice error>Your focus was not saved. {focus.error.message} <button onClick={() => focus.mutate(focus.variables)}>Retry save</button></WorkspaceNotice>}
      {data && <>
        {section === 'experience' && <>
          <div className="dw-ratings">{data.competitors.map(game => <article key={game.id} className="dw-rating"><Ring count={game.rating.positive} total={game.rating.total} label={`${game.name}: ${game.rating.positive} of ${game.rating.total} ${game.rating.label.toLowerCase()}`}/><h3>{game.name}</h3><p>{game.rating.label}</p><span className="dw-meta">{sources[game.source] || game.source} · {game.reviewCount} saved reviews</span></article>)}</div>
          <div className="dw-row dw-coverage"><p>Ratings describe saved reviews, not every player. Topic findings use {data.analysedReviews} selected reviews out of {data.reviewCount} available.</p><details><summary>Sources & dates</summary>{data.competitors.map(c => <p key={c.id}><b>{c.name}</b> · {c.from ? `${dateLabel(c.from)} – ${dateLabel(c.to)}` : 'Dates unavailable'}{c.sourceUrl && <> · <a href={c.sourceUrl} target="_blank" rel="noreferrer">Store ↗</a></>}</p>)}<p>Analysed {new Date(data.analysedAt).toLocaleString()} · {data.model}</p></details></div>
          <div className="dw-row dw-toolbar"><div className="dw-tabs" aria-label="Player experience view"><button aria-pressed={view === 'compare'} onClick={() => setView('compare')}>Compare experiences</button><button aria-pressed={view === 'timeline'} onClick={() => setView('timeline')}>Review timeline</button></div><button className="dw-link" onClick={() => onNavigate('focus')}>Your focus <span>{focused.length}</span><ArrowRight size={14}/></button></div>
          {view === 'compare' ? <>
            <div className="dw-focus-guide"><b>Focus now</b><span>Adds a topic to your test plan and redesign.</span><b>Later</b><span>Keeps it for another time.</span><b>Undecided</b><span>Leaves it out of your plan.</span></div>
            {topics.length ? <div className="dw-table-scroll"><table className="dw-matrix"><caption className="sr-only">Player feedback by topic and comparable game; select a cell to see its evidence.</caption><thead><tr><th>What to investigate</th>{data.competitors.map(c => <th key={c.id}>{c.name}</th>)}<th>Your priority</th></tr></thead><tbody>{topics.map(topic => <tr key={topic.id}><th scope="row"><b title={topic.question}>{topic.label}</b></th>{data.competitors.map(game => { const cell = topic.cells.find(c => c.competitorId === game.id); return <td key={game.id}>{cell ? <button className={`dw-signal ${cell.kind}`} aria-label={`${topic.label}, ${game.name}: ${labels[cell.kind]}, read evidence`} onClick={() => setSelection({ topic, cell })}><span className="dw-signal-dot"/>{labels[cell.kind]}<small>{cell.evidence.length} {cell.evidence.length === 1 ? 'example' : 'examples'} ↗</small></button> : <span className="dw-no-evidence" title="No verified review example for this topic">—</span>}</td>; })}<td><FocusControl topic={topic} value={priorities[topic.id] || 'open'} disabled={focus.isPending} onSave={save}/></td></tr>)}</tbody></table></div> : <WorkspaceNotice>No review-backed topics are available for these comparable games yet.</WorkspaceNotice>}
            <div className="dw-legend"><span className="concern">● Concern</span><span className="praise">● Praise</span><span className="mixed">● Both kinds of feedback</span><span>— No verified example</span></div>
            <p className="dw-meta">AI groups quoted examples by topic. “Both” means praise and concern appear in the selected examples; it is not a percentage of players.</p>
            {selection && <Evidence selection={selection} competitors={data.competitors} onClose={() => setSelection(null)}/>}
          </> : <ReviewTimeline competitors={data.competitors}/>}
        </>}
        {section === 'focus' && <>
          <div className="dw-focus-summary"><div className="dw-focus-count"><strong>{focused.length.toString().padStart(2, '0')}</strong><span>FOCUS NOW</span></div><div className="dw-focus-count muted"><strong>{later.length.toString().padStart(2, '0')}</strong><span>LATER</span></div><div className="dw-focus-count muted"><strong>{(topics.length - focused.length - later.length).toString().padStart(2, '0')}</strong><span>UNDECIDED</span></div><div className="dw-focus-action"><p>Your priorities, not a score for the game.</p><button className="dw-primary" disabled={!focused.length || focus.isPending} onClick={() => onNavigate('redesign')}>Redesign from this focus <ArrowRight size={15}/></button></div></div>
          {!focused.length && <div className="dw-empty"><h3>Choose your first priority.</h3><p>Mark a topic “Focus now” below. Its suggested test will appear here.</p></div>}
          {focused.map((topic, index) => <article key={topic.id} className="dw-plan"><div className="dw-row"><div><span className="dw-eyebrow">TEST {String(index + 1).padStart(2, '0')}</span><h3>{topic.label}</h3></div><FocusControl topic={topic} value="focus" onSave={save} disabled={focus.isPending}/></div><h4>{topic.question}</h4><ol className="dw-test-steps">{topic.steps.map((step, i) => <li key={i}><span>{i + 1}</span>{step}</li>)}</ol><details><summary>Why this test fits your game</summary><p>{topic.designConnection}</p><blockquote>“{topic.documentQuote}”</blockquote><div className="dw-source-chips">{topic.cells.map(cell => <button key={cell.competitorId} className="dw-link" onClick={() => setSelection({ topic, cell })}>{data.competitors.find(c => c.id === cell.competitorId)?.name} ↗</button>)}</div></details></article>)}
          {selection && <Evidence selection={selection} competitors={data.competitors} onClose={() => setSelection(null)}/>}
          <h3 className="dw-list-title">{focused.length ? 'Other topics to consider' : 'Topics from your player research'}</h3>
          <div className="dw-backlog">{topics.filter(t => priorities[t.id] !== 'focus').map(topic => <div className="dw-row" key={topic.id}><div><h4>{topic.label}</h4><p>{topic.question}</p></div><FocusControl topic={topic} value={priorities[topic.id] || 'open'} disabled={focus.isPending} onSave={save}/></div>)}</div>
          <p className="dw-meta">Focus choices are saved for this game. Suggested tests are hypotheses to validate with players.</p>
        </>}
      </>}
    </>}
  </div>;
}
