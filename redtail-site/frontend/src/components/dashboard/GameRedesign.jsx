import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Download, ImagePlus, Loader2 } from 'lucide-react';
import { workspacePost } from '@/lib/workspaceApi';
import WorkspaceNotice from './WorkspaceNotice';

export default function GameRedesign({ credentials, research, focused, onFocus }) {
  const client = useQueryClient();
  const [jobId, setJobId] = useState(null);
  const [jobError, setJobError] = useState('');
  const [referenceIds, setReferenceIds] = useState(null);
  const key = ['redesign-history', credentials.username, credentials.gameId];
  const history = useQuery({ queryKey: key, retry: false, refetchOnWindowFocus: false, queryFn: ({ signal }) => workspacePost('workspace-redesign-history', credentials, {}, signal) });
  const assets = useQuery({ queryKey: ['document-art', credentials.username, credentials.gameId], retry: false, staleTime: Infinity, queryFn: ({ signal }) => workspacePost('workspace-document-assets', credentials, {}, signal) });
  const references = assets.data?.references || [];
  const previousReferences = [...(history.data?.images || [])].sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0]?.referenceIds;
  const selectedRefs = referenceIds ?? previousReferences ?? references.slice(0, 3).map(r => r.id);
  const job = useQuery({ queryKey: ['workspace-job', credentials.username, credentials.gameId, jobId], enabled: !!jobId, retry: false, refetchInterval: q => q.state.data?.status === 'running' ? 2500 : false, queryFn: () => workspacePost('workspace-job', credentials, { jobId }) });
  useEffect(() => {
    if (job.data?.status === 'done') { client.invalidateQueries({ queryKey: key }); setJobId(null); }
    if (job.data?.status === 'error') { setJobError(job.data.error); setJobId(null); }
  }, [job.data]); // The component is scoped to a single game by its parent.
  useEffect(() => {
    const pending = history.data?.pending?.find(item => item.status === 'running');
    if (pending) setJobId(pending.jobId);
    const failed = history.data?.pending?.find(item => item.status === 'error');
    if (failed) setJobError(failed.error);
  }, [history.data]);
  /** @param {{endpoint: string, payload: object}} request */
  const submit = ({ endpoint, payload }) => workspacePost(endpoint, credentials, payload);
  const start = useMutation({ mutationFn: submit, onMutate: () => setJobError(''), onSuccess: result => {
    if (result.status === 'done') client.invalidateQueries({ queryKey: key });
    else { client.removeQueries({ queryKey: ['workspace-job', credentials.username, credentials.gameId, result.jobId] }); setJobId(result.jobId); }
  } });
  const brief = history.data?.brief;
  const current = brief && research.data && brief.version === history.data.redesignVersion && brief.fingerprint === research.data.fingerprint && [...brief.focusTopicIds].sort().join() === focused.map(t => t.id).sort().join();
  const busy = start.isPending || !!jobId;
  const prepare = () => start.mutate({ endpoint: 'workspace-redesign-brief', payload: { fingerprint: research.data.fingerprint } });
  const toggleReference = id => setReferenceIds(selectedRefs.includes(id) ? selectedRefs.filter(r => r !== id) : [...selectedRefs, id].slice(0, 4));
  const error = start.error?.message || jobError || job.error?.message;
  const latestImage = mod => [...(history.data?.images || [])].filter(i => i.modificationId === mod.id).sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0];
  return <section className="dw-redesign">
    <header className="dw-heading"><span className="dw-eyebrow">04 / REDESIGN YOUR GAME</span><h2>Keep your game. Improve the experience.</h2><p>Your uploaded design + your chosen focus + player evidence.</p></header>
    <div className="dw-redesign-path"><span>01 · Your document</span><ArrowRight size={16}/><span>02 · Your focus</span><ArrowRight size={16}/><span>03 · Proposed change</span><ArrowRight size={16}/><span>04 · Concept image</span></div>
    {(history.isPending || assets.isPending) && <WorkspaceNotice><Loader2 className="animate-spin" size={16}/>Opening your game’s saved designs…</WorkspaceNotice>}
    {(history.isError || assets.isError) && <WorkspaceNotice error>{history.error?.message || assets.error?.message} <button onClick={() => { history.refetch(); assets.refetch(); }}>Retry</button></WorkspaceNotice>}
    {research.isError && <WorkspaceNotice error>Player research is needed before preparing a redesign. {research.error.message}<button onClick={() => research.refetch()}>Retry research</button></WorkspaceNotice>}
    {assets.data && <div className="dw-original"><span className="dw-eyebrow">YOUR SOURCE DOCUMENT</span><h3>{assets.data.filename}</h3><span className="dw-meta">{assets.data.isOriginal ? `${references.length} visual references available` : 'Original document unavailable for this older game'}</span></div>}
    {assets.data && !assets.data.isOriginal && <WorkspaceNotice error>This older game only has a saved report. Upload its original game design through “Add a game” to create a document-based redesign.</WorkspaceNotice>}
    <div className="dw-row dw-focus-bar"><div><span className="dw-eyebrow">CHOSEN FOCUS</span><div className="dw-source-chips">{focused.map(t => <span key={t.id}>{t.label}</span>)}{!focused.length && <span>No priorities selected</span>}</div></div><button className="dw-link" onClick={onFocus}><ArrowLeft size={14}/>Choose focus</button></div>
    {error && <WorkspaceNotice error>{error}{job.isError && <button onClick={() => job.refetch()}>Check progress again</button>}</WorkspaceNotice>}
    {busy && <WorkspaceNotice><Loader2 size={16} className="animate-spin"/>{job.data?.kind === 'image' ? 'Rendering your game’s concept with OpenAI. High-quality images can take several minutes.' : 'Building a proposal from your full design document and chosen priorities…'} You can return to this game while it finishes.</WorkspaceNotice>}
    {brief && !current && <WorkspaceNotice>This proposal needs an update for your current workspace. Prepare an updated proposal before generating images.</WorkspaceNotice>}
    {(!brief || !current) && <button className="dw-primary" onClick={prepare} disabled={busy || !focused.length || !research.data || !assets.data?.isOriginal}>Prepare redesign proposal <ArrowRight size={15}/></button>}
    {brief && <>
      <div className="dw-row dw-subheading"><div><span className="dw-eyebrow">{current ? 'YOUR REDESIGN PROPOSAL' : 'PREVIOUS PROPOSAL'}</span><h3>{brief.headline}</h3></div><span className="dw-meta">{new Date(brief.createdAt).toLocaleDateString()}</span></div>
      <details className="dw-identity"><summary>Game identity preserved · {brief.identity.length} document-backed details</summary><div className="dw-identity-grid">{brief.identity.map((fact, i) => <div key={i}><span className="dw-eyebrow">{fact.label}</span><h4>{fact.value}</h4><blockquote>“{fact.documentQuote}”</blockquote></div>)}</div></details>
      {references.length > 0 && <div className="dw-reference-picker"><div className="dw-row"><div><h3>Use your game’s original look.</h3><p>Select up to four references from your uploaded document.</p></div><span className="dw-meta">{selectedRefs.length} / 4 selected</span></div><div className="dw-reference-strip">{references.map((reference, i) => <button key={reference.id} aria-pressed={selectedRefs.includes(reference.id)} disabled={busy || (!selectedRefs.includes(reference.id) && selectedRefs.length >= 4)} onClick={() => toggleReference(reference.id)} aria-label={`Use reference ${i + 1}, ${reference.label}`}><img src={`data:image/jpeg;base64,${reference.thumbnail}`} alt={`Visual reference ${i + 1} from ${reference.label.toLowerCase()}`}/><span>{reference.label}{selectedRefs.includes(reference.id) ? ' ✓' : ''}</span></button>)}</div></div>}
      {!references.length && assets.data?.isOriginal && <p className="dw-meta">{assets.data.referenceError || 'No original artwork was found in this document.'} Concepts will follow its written art direction.</p>}
      {!assets.data?.imageAvailable && <WorkspaceNotice error>Image generation needs the server’s OpenAI API key.</WorkspaceNotice>}
      {brief.modifications.map((mod, index) => { const image = latestImage(mod); return <article className="dw-proposal" key={mod.id}>
        <div className="dw-row"><div><span className="dw-eyebrow">CHANGE {String(index + 1).padStart(2, '0')} · {focused.find(t => t.id === mod.topicId)?.label || 'SAVED FOCUS'}</span><h3>{mod.title}</h3></div><span className="dw-tag">PROPOSED</span></div>
        <div className="dw-before-after"><div><span className="dw-eyebrow">IN YOUR DOCUMENT</span><p>{mod.currentDesign}</p><details><summary>See original wording</summary><blockquote>“{mod.documentQuote}”</blockquote></details></div><div><span className="dw-eyebrow">TRY THIS CHANGE</span><p>{mod.change}</p><details><summary>{mod.preserve.length} game rules kept</summary><div className="dw-source-chips">{mod.preserve.map((item, i) => <span key={i}>{item}</span>)}</div></details></div></div>
        <details className="dw-reason"><summary>Player evidence & suggested test</summary><p>{mod.why}</p>{mod.reviewIds.map(id => { const review = brief.evidence.find(r => r.reviewId === id); return review && <blockquote key={id}><b>{review.game}</b><p>“{review.text}”</p></blockquote>; })}<h4>Validate with players</h4><p>{mod.test}</p>{mod.assumptions.length > 0 && <><h4>Design assumptions to check</h4><ul>{mod.assumptions.map((item, i) => <li key={i}>{item}</li>)}</ul></>}</details>
        {image && <figure className="dw-concept"><img src={`data:image/png;base64,${image.imageB64}`} alt={`Proposed ${mod.title} concept for ${brief.gameName}`}/><figcaption><span>Concept image · {image.referenceCount} document references used · {image.quality} quality</span><a download={`${brief.gameName}-${mod.id}.png`} href={`data:image/png;base64,${image.imageB64}`}><Download size={14}/>Download image</a></figcaption></figure>}
        <div className="dw-row dw-render-footer"><p>A visual proposal to test. It does not change your game’s code.</p><button className="dw-primary" disabled={busy || !current || !assets.data?.imageAvailable || (image && JSON.stringify([...image.referenceIds].sort()) === JSON.stringify([...selectedRefs].sort()))} onClick={() => start.mutate({ endpoint: 'workspace-redesign-image', payload: { briefId: brief.id, modificationId: mod.id, referenceIds: selectedRefs } })}><ImagePlus size={16}/>{image ? 'Generate with changed references' : 'Generate concept with OpenAI'}</button></div>
      </article>; })}
    </>}
  </section>;
}
