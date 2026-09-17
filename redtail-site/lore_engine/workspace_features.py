"""Authenticated, per-game research, persistent focus, and redesign routes.

Ported from a local-preview build whose Features.start_job() ran work on a
background ThreadPoolExecutor and let the client poll for completion.
Vercel's Python functions have no thread that survives past the response
(same constraint server.py already documents for scraping), so start_job()
here just runs the work synchronously and returns the finished job record
directly — the frontend's job-polling mutation already treats an immediate
`status: 'done'` (or 'error') response as a terminal result, so no frontend
change was needed to make this correct under serverless.
"""
import json
import re
import threading

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

import player_research as research
import game_redesign as redesign
import storage


class GameRequest(BaseModel):
    username: str
    password: str
    gameId: str
    year: int = 2026
    cachedOnly: bool = False
    analysisId: str | None = None


class FocusRequest(GameRequest):
    fingerprint: str
    topicId: str
    status: Literal['open', 'focus', 'later']


class BriefRequest(GameRequest):
    fingerprint: str


class ImageRequest(GameRequest):
    briefId: str
    modificationId: str
    referenceIds: list[str] = Field(default_factory=list, max_length=4)


class JobRequest(GameRequest):
    jobId: str


def safe_error(exc):
    if isinstance(exc, ValueError):
        return str(exc)[:500]
    name = type(exc).__name__
    if name in ('AuthenticationError', 'PermissionDeniedError'):
        return 'The AI provider could not authorize this request. Check the server API account and model access.'
    if name == 'RateLimitError':
        return 'The AI provider is temporarily rate-limited or has reached its usage limit. Retry later.'
    if name in ('APITimeoutError', 'TimeoutError'):
        return 'The AI provider took too long. Your saved research is safe; retry this step.'
    return f'This step could not finish ({name}). Check the backend connection and retry.'


class Features:
    def __init__(self, workspace):
        self.w = workspace
        self.locks = {}
        self.guard = threading.Lock()

    def lock(self, key):
        with self.guard:
            return self.locks.setdefault(key, threading.Lock())

    def context(self, req, original=False):
        if req.year not in self.w.config.SUPPORTED_YEARS:
            raise ValueError('Unsupported data year.')
        text, filename = self.w.document_for(self.w.WorkspaceRequest(**req.model_dump(include=set(GameRequest.model_fields))))
        is_original = not filename.startswith('Saved analysis report (')
        if original and not is_original:
            raise ValueError('This older game has only a saved report. Add its original design document before redesigning it.')
        user = self.w.get_user_data(req.username, req.password)
        game = next(g for g in user['portfolio'] if g['id'] == req.gameId)
        return text, filename, game, is_original

    def scope(self, req, text):
        return self.w.digest(req.username.lower() + '\0' + req.gameId + '\0' + text)

    def focus(self, req, text):
        return storage.workspace_get_json('focus', self.scope(req, text)) or {'priorities': {}, 'updatedAt': None, 'documentHash': self.w.digest(text)}

    def feedback(self, req):
        text, filename, game, original = self.context(req)
        if req.analysisId:
            if not re.fullmatch('[a-f0-9]{64}', req.analysisId):
                raise ValueError('Open the current competition analysis first.')
            analysis = storage.workspace_get_json('analysis', req.analysisId)
            expected = self.w.digest('grounded-v2' + text + str(req.year) + json.dumps(analysis.get('sources', []), sort_keys=True)) if analysis else None
            if expected != req.analysisId:
                raise ValueError('This competition analysis belongs to another document. Refresh the workspace.')
        else:
            analysis = self.w.analyse(text, filename, req.year, cached_only=req.cachedOnly)
        records, sources = self.w.market(req.year)
        competitors = research.collect_competitors(analysis, records)
        inputs = research.selected_reviews(competitors)
        fingerprint = self.w.digest(research.VERSION + self.scope(req, text) + json.dumps(competitors, sort_keys=True))
        with self.lock(fingerprint):
            result = storage.workspace_get_json('feedback', fingerprint)
            if result is None:
                topics = []
                if inputs:
                    import os
                    if os.getenv('LORE_ALLOW_DOCUMENT_AI') != '1':
                        raise ValueError('The server needs document-analysis access enabled to analyse player feedback.')
                    raw = self.w.llm.generate(research.build_prompt(text, filename, inputs), max_tokens=6500)
                    try:
                        topics = research.validate_topics(raw, text, inputs, competitors)
                    except ValueError:
                        # One repair pass must still pass the same source validation.
                        storage.workspace_put_json('research-rejected', fingerprint, {'raw': raw})
                        raw = self.w.llm.generate(research.build_prompt(text, filename, inputs) + '\nThe prior response below failed validation. Correct it: documentQuote and review quotes must be EXACT continuous substrings, including punctuation and any spaces around hyphens. Do not paraphrase, join excerpts, or add ellipses. Each topic must have exactly three test steps.\nPRIOR_RESPONSE:\n' + raw, max_tokens=6500)
                        topics = research.validate_topics(raw, text, inputs, competitors)
                result = {'fingerprint': fingerprint, 'gameId': req.gameId, 'username': req.username.lower(),
                          'gameName': game['name'], 'year': req.year, 'documentHash': self.w.digest(text),
                          'document': filename, 'isOriginal': original, 'competitors': competitors, 'topics': topics,
                          'analysedReviews': len(inputs), 'reviewCount': sum(c['reviewCount'] for c in competitors),
                          'analysedAt': self.w.now(), 'model': self.w.llm.active_model(),
                          'sources': sources}
                storage.workspace_put_json('feedback', fingerprint, result)
        return {**result, 'focus': self.focus(req, text)}

    def cached_feedback(self, req, fingerprint, text):
        if not re.fullmatch('[a-f0-9]{64}', fingerprint):
            raise ValueError('Open the current player research before continuing.')
        data = storage.workspace_get_json('feedback', fingerprint)
        if not data or data['gameId'] != req.gameId or data['username'] != req.username.lower() or data['documentHash'] != self.w.digest(text):
            raise ValueError('This research belongs to another game or document. Refresh this workspace.')
        return data

    def save_focus(self, req):
        text, _, _, _ = self.context(req)
        data = self.cached_feedback(req, req.fingerprint, text)
        if req.topicId not in {t['id'] for t in data['topics']}:
            raise ValueError('This topic is not in the selected game’s research.')
        scope = self.scope(req, text)
        with self.lock(scope):
            state = self.focus(req, text)
            state['priorities'][req.topicId] = req.status
            state['updatedAt'] = self.w.now()
            storage.workspace_put_json('focus', scope, state)
        return state

    def assets(self, req):
        text, filename, game, original = self.context(req)
        docid = self.w.digest(req.username + '\0' + text)
        references = storage.workspace_get_json('asset-meta', docid)
        # Migrate only the verified original for this exact existing portfolio
        # entry, and require its full extracted text to match the retained doc.
        if references is None and original and req.username == 'lore' and req.gameId == 'p1' and game['name'] == 'Lucha Dog':
            from pathlib import Path
            source = Path('/Users/amrithap/Desktop/amritha_project/video_game/ai_engine/games/LuchaDog - unity game design document (1).pdf')
            if source.exists():
                raw = source.read_bytes()
                if self.w.extract(raw, source.name) == text:
                    references = redesign.extract_references(raw, filename, docid)
                    storage.workspace_put_json('asset-meta', docid, references)
        references = references or []
        import os
        return {'filename': filename, 'documentHash': self.w.digest(text), 'isOriginal': original,
                'references': references, 'imageAvailable': bool(os.getenv('OPENAI_API_KEY')),
                'referenceError': (storage.workspace_get_json('asset-error', docid) or {}).get('error'),
                'imageModel': os.getenv('OPENAI_REDESIGN_MODEL', self.w.config.OPENAI_IMAGE_MODEL)}, docid

    def evidence_for(self, feedback, topics):
        reviews = {r['id']: (c, r) for c in feedback['competitors'] for r in c['reviews']}
        selected = {}
        for topic in topics:
            for cell in topic['cells']:
                for evidence in cell['evidence']:
                    cid, review = reviews[evidence['reviewId']]
                    item = selected.setdefault(review['id'], {'reviewId': review['id'], 'game': cid['name'],
                                                             'source': cid['source'], 'text': review['text'],
                                                             'date': review['date'], 'topicIds': []})
                    if topic['id'] not in item['topicIds']:
                        item['topicIds'].append(topic['id'])
        return list(selected.values())

    def job(self, req, job_id):
        text, _, _, _ = self.context(req)
        if not re.fullmatch('[a-f0-9]{64}', job_id):
            raise ValueError('Unknown job.')
        job = storage.workspace_get_json('job', job_id)
        if not job or job['scope'] != self.scope(req, text):
            raise ValueError('This result is not available for the selected game.')
        return job

    def start_job(self, req, text, kind, key, work):
        # No background thread survives past a serverless response — run the
        # work inline and return the finished record. The frontend's mutation
        # already treats an immediate 'done'/'error' status as terminal.
        scope = self.scope(req, text)
        job_id = self.w.digest(scope + kind + key)
        with self.lock(job_id):
            existing = storage.workspace_get_json('job', job_id)
            if existing and existing['status'] == 'done':
                return existing
            job = {'jobId': job_id, 'scope': scope, 'kind': kind, 'status': 'running', 'startedAt': self.w.now()}
            storage.workspace_put_json('job', job_id, job)
            try:
                result = work()
                finished = {**job, 'status': 'done', 'result': result, 'finishedAt': self.w.now()}
            except Exception as exc:
                finished = {**job, 'status': 'error', 'error': safe_error(exc), 'finishedAt': self.w.now()}
            storage.workspace_put_json('job', job_id, finished)
        return finished

    def prepare_brief(self, req):
        text, filename, game, _ = self.context(req, original=True)
        feedback = self.cached_feedback(req, req.fingerprint, text)
        priorities = self.focus(req, text)['priorities']
        topics = [t for t in feedback['topics'] if priorities.get(t['id']) == 'focus']
        if not topics:
            raise ValueError('Choose Focus now for at least one topic before preparing a redesign.')
        import os
        if os.getenv('LORE_ALLOW_DOCUMENT_AI') != '1':
            raise ValueError('Document analysis must be enabled on the server to prepare a redesign.')
        evidence = self.evidence_for(feedback, topics)
        key = redesign.VERSION + req.fingerprint + json.dumps(topics, sort_keys=True)

        def work():
            bid = self.w.digest(self.scope(req, text) + key)
            prompt = redesign.brief_prompt(text, filename, game['name'], topics, evidence)
            stored = storage.workspace_get_json('brief-provider', bid)
            raw = stored['raw'] if stored else self.w.llm.generate(prompt, max_tokens=6500)
            storage.workspace_put_json('brief-provider', bid, {'raw': raw})
            try:
                brief = redesign.validate_brief(raw, text, topics, evidence)
            except ValueError as exc:
                raw = self.w.llm.generate(prompt + '\nCorrect this prior response. Validation error: ' + str(exc) + '\nEvery documentExcerptId must name a supplied doc-N excerpt supporting that claim. Respect all text length limits. Return one change per supplied topic and only that topic’s review IDs. Return complete JSON.\nPRIOR_RESPONSE:\n' + raw, max_tokens=6500)
                storage.workspace_put_json('brief-provider', bid, {'raw': raw})
                brief = redesign.validate_brief(raw, text, topics, evidence)
            brief.update({'id': bid, 'scope': self.scope(req, text), 'gameId': req.gameId, 'gameName': game['name'],
                          'version': redesign.VERSION,
                          'document': filename, 'documentHash': self.w.digest(text), 'fingerprint': req.fingerprint,
                          'focusTopicIds': [t['id'] for t in topics], 'createdAt': self.w.now(),
                          'model': self.w.llm.active_model(), 'evidence': evidence})
            storage.workspace_put_json('brief', bid, brief)
            return brief
        return self.start_job(req, text, 'brief', key, work)

    def read_brief(self, req, text):
        if not re.fullmatch('[a-f0-9]{64}', req.briefId):
            raise ValueError('Prepare a redesign brief first.')
        brief = storage.workspace_get_json('brief', req.briefId)
        if not brief or brief.get('scope') != self.scope(req, text):
            raise ValueError('This redesign belongs to another game or document. Prepare a new brief.')
        if brief.get('version') != redesign.VERSION:
            raise ValueError('Prepare an updated redesign proposal before generating images.')
        priorities = self.focus(req, text)['priorities']
        feedback = self.cached_feedback(req, brief['fingerprint'], text)
        current_ids = {t['id'] for t in feedback['topics']}
        if sorted(k for k, v in priorities.items() if v == 'focus' and k in current_ids) != sorted(brief['focusTopicIds']):
            raise ValueError('Your focus has changed. Prepare an updated brief before making images.')
        return brief

    def generate_image(self, req):
        text, _, game, _ = self.context(req, original=True)
        brief = self.read_brief(req, text)
        mod = next((m for m in brief['modifications'] if m['id'] == req.modificationId), None)
        if not mod:
            raise ValueError('Choose a change from this game’s redesign brief.')
        assets, docid = self.assets(req)
        if not assets['imageAvailable']:
            raise ValueError('An OpenAI API key is not configured on the server.')
        ids = list(dict.fromkeys(req.referenceIds))
        known = {r['id'] for r in assets['references']}
        if any(r not in known for r in ids):
            raise ValueError('Only visual references from this game’s document can be used.')
        images = [redesign.reference_image_bytes(docid, rid) for rid in ids]
        key = req.briefId + mod['id'] + json.dumps(ids) + assets['imageModel']

        def work():
            import base64
            image, details = redesign.render_concept(game['name'], brief, mod, images, assets['imageModel'])
            return {'modificationId': mod['id'], 'gameId': req.gameId, 'briefId': req.briefId,
                    'imageB64': base64.b64encode(image).decode(), 'referenceIds': ids,
                    'createdAt': self.w.now(), **details}
        return self.start_job(req, text, 'image', key, work)

    def history(self, req):
        text, _, _, _ = self.context(req)
        scope = self.scope(req, text)
        # Per-game scope is verified on every read; no paths or tokens come from
        # the client.
        briefs = [item for item in storage.workspace_list_json('brief') if item.get('scope') == scope]
        focus_ids = {k for k, v in self.focus(req, text)['priorities'].items() if v == 'focus'}
        briefs.sort(key=lambda b: (set(b['focusTopicIds']) == focus_ids, b['createdAt']), reverse=True)
        latest = briefs[0]['id'] if briefs else None
        images, pending = [], []
        for item in storage.workspace_list_json('job'):
            if item.get('scope') != scope:
                continue
            if item.get('status') == 'running':
                pending.append(self.job(req, item['jobId']))
            if item.get('kind') == 'image' and item.get('status') == 'done' and item['result'].get('briefId') == latest:
                images.append(item['result'])
        return {'brief': briefs[0] if briefs else None, 'images': images, 'pending': pending, 'redesignVersion': redesign.VERSION}


def install(app, workspace):
    service = Features(workspace)

    def respond(fn, req):
        try:
            return fn(req)
        except PermissionError:
            return JSONResponse({'error': 'Unauthorized'}, status_code=401)
        except Exception as exc:
            return JSONResponse({'error': safe_error(exc)}, status_code=422 if isinstance(exc, ValueError) else 502)

    @app.post('/api/lore/workspace-feedback')
    def feedback(req: GameRequest):
        return respond(service.feedback, req)

    @app.post('/api/lore/workspace-focus')
    def focus(req: FocusRequest):
        return respond(service.save_focus, req)

    @app.post('/api/lore/workspace-document-assets')
    def assets(req: GameRequest):
        return respond(lambda r: service.assets(r)[0], req)

    @app.post('/api/lore/workspace-redesign-brief')
    def brief(req: BriefRequest):
        return respond(service.prepare_brief, req)

    @app.post('/api/lore/workspace-redesign-image')
    def image(req: ImageRequest):
        return respond(service.generate_image, req)

    @app.post('/api/lore/workspace-job')
    def job(req: JobRequest):
        return respond(lambda r: service.job(r, r.jobId), req)

    @app.post('/api/lore/workspace-redesign-history')
    def history(req: GameRequest):
        return respond(service.history, req)

    return service
