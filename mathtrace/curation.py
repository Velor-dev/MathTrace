"""Root extraction, curation and explicit target admission of advisory learning."""
from __future__ import annotations

import json
from .advisory import Advisory
from .context import Tasks
from .research import nonempty
from .store import StateError, digest

CURATION_PROFILE = 'source-bound-local-curation-v1'
CATEGORIES = {'failed-mechanism', 'counterexample', 'structural-insight', 'theorem-trap', 'reopen'}


class Curation:
    def __init__(self, campaign):
        self.c, self.store = campaign, campaign.store
        self.a = Advisory(campaign)

    def _sources(self, event, sources):
        result = [event['target'], *sources]
        def visit(value):
            if not isinstance(value, dict):
                return
            for k, v in value.items():
                if k in {'certificate', 'observation', 'receipt', 'result', 'resolution', 'case', 'assessment_artifact'} and v:
                    self.store.get(v)
                    result.append(v)
                elif k in {'reviews', 'followups'} and isinstance(v, list):
                    for r in v:
                        self.store.get(r)
                        result.append(r)
                elif k == 'reason' and isinstance(v, dict):
                    visit(v)
        visit(event['payload'])
        for identifier in list(result):
            record = self.store.get(identifier)
            d = record['data']
            if record['kind'] == 'result':
                result += [d['artifact'], d['host_receipt'], d['task'], d['run'],
                    self.store.get(d['run'], 'run')['data']['dispatch_evidence']]
            elif record['kind'] == 'native_failure':
                result += [d['capture_artifact'], d['response_artifact'], d['task'], d['run']]
            elif record['kind'] == 'ingestion_failure':
                result += [d['result'], d['artifact'], d['host_receipt'], d['task'], d['run']]
        return list(dict.fromkeys(result))

    def _scope(self, target, subject):
        self.store.get(target, 'claim')
        record = self.store.get(subject)
        if record['kind'] == 'checkpoint':
            from .orchestration import Orchestration
            snapshot = Orchestration(self.c).checkpoint_snapshot(subject)
            if any(r['id'] == target for r in snapshot['records']):
                return
        if Tasks(self.c)._claim_for(subject) == target:
            return
        if record['kind'] == 'obligation' and self.store.get(record['data']['route'], 'route')['data']['target'] == target:
            return
        claim = Tasks(self.c)._claim_for(subject)
        if claim is not None and any(o['data'].get('claim') == claim and self.store.get(o['data']['route'], 'route')['data']['target'] == target
               for o in self.store.records('obligation')):
            return
        raise StateError('Learning extraction needs the exact target or an explicitly linked research boundary')

    def extract(self, target, boundary, summary, sources, *, category, applicability, reopen_condition,
                author, expected, request_id):
        target_record = self.store.get(target, 'claim')
        event = self.a.boundary_data(boundary)['event']
        self._scope(target, event['target'])
        if category not in CATEGORIES:
            raise StateError('Unknown learning category')
        if not isinstance(sources, list) or any(not isinstance(s, str) or not s.strip() for s in sources):
            raise StateError('Learning extraction sources must be an exact list')
        for s in sources:
            self.store.get(s)
        for text, name in ((summary, 'proposed learning'), (applicability, 'exact applicability scope'),
            (reopen_condition, 'reopening condition'), (author, 'extractor'), (request_id, 'extraction request identity')):
            nonempty(text, name)
        sources = list(dict.fromkeys([boundary, *self._sources(event, sources)]))
        description = {'profile': CURATION_PROFILE, 'target': target, 'target_hash': target_record['hash'],
            'boundary': boundary, 'boundary_hash': self.store.get(boundary)['hash'], 'sources': sources,
            'summary': summary, 'category': category, 'applicability': applicability,
            'reopen_condition': reopen_condition, 'author': author}
        fingerprint = digest(description)
        with self.store.transaction():
            old = self.store.request('extract-learning:' + request_id, fingerprint)
            if old is not None:
                return {**old, 'current': self.candidate_current(old['candidate'])}
            basis = {s: self.c._source_semantics(s) for s in sources}
            data = {**description, 'basis': basis, 'basis_hash': digest(basis), 'authority': 'Proposed advice only; root curation required',
                'mathematical_acceptance': False}
            for record in self.store.records('learning_candidate'):
                if record['data'] == data:
                    reply = {'candidate': record['id'], 'mathematical_acceptance': False}
                    self.store.finish_request('extract-learning:' + request_id, fingerprint, reply)
                    return {**reply, 'current': self.candidate_current(record['id'])}
            with self.store.transaction(expected):
                identifier = self.store.put('learning_candidate', data)
                reply = {'candidate': identifier, 'mathematical_acceptance': False}
                self.store.finish_request('extract-learning:' + request_id, fingerprint, reply)
                return {**reply, 'current': True}

    def candidate_current(self, identifier):
        try:
            d = self.store.get(identifier, 'learning_candidate')['data']
            self.a.boundary_data(d['boundary'])
            event = self.store.get(d['boundary'])['data']['event']
            self._scope(d['target'], event['target'])
            return (d.get('profile') == CURATION_PROFILE and d['category'] in CATEGORIES
                and self.store.status(identifier) in {'proposed', 'curated'}
                and d.get('authority') == 'Proposed advice only; root curation required'
                and d.get('mathematical_acceptance') is False
                and all(isinstance(d.get(k), str) and d[k].strip()
                        for k in ('summary', 'applicability', 'reopen_condition', 'author'))
                and isinstance(d['sources'], list) and all(isinstance(s, str) for s in d['sources'])
                and len(set(d['sources'])) == len(d['sources'])
                and d['target_hash'] == self.store.get(d['target'])['hash']
                and d['boundary_hash'] == self.store.get(d['boundary'])['hash']
                and d['basis_hash'] == digest(d['basis']) and bool(d['sources'])
                and d['boundary'] in d['sources'] and self.c._scope_current(identifier)
                and set(self._sources(event, [])).issubset(d['sources'])
                and d['basis'] == {s: self.c._source_semantics(s) for s in d['sources']})
        except (StateError, KeyError, TypeError, ValueError, RecursionError):
            return False

    def curate(self, candidate, *, reason, author, expected, request_id,
               disposition='curate', summary=None, applicability=None, reopen_condition=None):
        record = self.store.get(candidate, 'learning_candidate')
        if disposition not in {'curate', 'decline'}:
            raise StateError('Curation must explicitly curate or decline')
        nonempty(reason, 'root curation reason')
        nonempty(author, 'root curator')
        nonempty(request_id, 'curation request identity')
        for v, name in ((summary, 'revised summary'), (applicability, 'revised applicability'), (reopen_condition, 'revised reopening condition')):
            if v is not None:
                nonempty(v, name)
        fingerprint = digest({'candidate': record['hash'], 'disposition': disposition, 'reason': reason,
            'author': author, 'summary': summary, 'applicability': applicability, 'reopen_condition': reopen_condition})
        with self.store.transaction():
            old = self.store.request('curate-learning:' + request_id, fingerprint)
            if old is not None:
                return {**old, 'current': self.c.learning_current(old['learning']) if old['learning'] else False}
            with self.store.transaction(expected):
                if self.store.status(candidate) != 'proposed':
                    raise StateError('Already curated/declined candidates remain historical; use exact replay or a new extraction')
                if disposition == 'curate' and not self.candidate_current(candidate):
                    raise StateError('Changed extraction evidence needs fresh review/extraction before curation')
                self.store.decide(candidate, 'curated' if disposition == 'curate' else 'declined',
                    {'reason': reason, 'author': author, 'mathematical_acceptance': False})
                d = record['data']
                learning = self.c.learning(summary or d['summary'], d['sources'], category=d['category'],
                    reopen_condition=reopen_condition or d['reopen_condition'], target=d['target'],
                    applicability=applicability or d['applicability'], origin={'candidate': candidate,
                        'candidate_hash': record['hash'], 'boundary': d['boundary'], 'reason': reason, 'author': author,
                        'profile': CURATION_PROFILE}) if disposition == 'curate' else None
                reply = {'candidate': candidate, 'learning': learning, 'mathematical_acceptance': False}
                self.store.finish_request('curate-learning:' + request_id, fingerprint, reply)
                return {**reply, 'current': bool(learning and self.c.learning_current(learning))}

    def admit(self, learning, target, *, applicability, reason, author, expected, request_id):
        lesson = self.store.get(learning, 'learning')
        target_record = self.store.get(target, 'claim')
        if lesson['data'].get('target') not in {None, target}:
            raise StateError('Curated target advice needs an explicit new scoped lesson for another target')
        for v, name in ((applicability, 'target applicability'), (reason, 'admission reason'),
            (author, 'root admitting author'), (request_id, 'learning admission request identity')):
            nonempty(v, name)
        data = {'profile': CURATION_PROFILE, 'learning': learning, 'learning_hash': lesson['hash'],
            'target': target, 'target_hash': target_record['hash'], 'applicability': applicability,
            'reason': reason, 'author': author}
        fingerprint = digest(data)
        with self.store.transaction():
            old = self.store.request('admit-learning:' + request_id, fingerprint)
            if old is not None:
                return {**old, 'current': self.admission_current(old['admission'])}
            with self.store.transaction(expected):
                if not self.c.learning_current(learning) or not self.c._scope_current(target):
                    raise StateError('Only current advice may enter an exact current target scope')
                basis = self.c._source_semantics(learning)
                admission = self.store.put('learning_admission', {**data, 'basis': basis, 'basis_hash': digest(basis)})
                self.store.decide(admission, 'active', {'reason': reason, 'mathematical_acceptance': False})
                reply = {'admission': admission, 'learning': learning, 'mathematical_acceptance': False}
                self.store.finish_request('admit-learning:' + request_id, fingerprint, reply)
                return {**reply, 'current': True}

    def admission_current(self, identifier):
        try:
            d = self.store.get(identifier, 'learning_admission')['data']
            decision = self.store.db.execute('SELECT e.type,e.payload FROM events e JOIN decisions d '
                'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
            activation = {'status': 'active', 'reason': {'reason': d['reason'], 'mathematical_acceptance': False}}
            return (d.get('profile') == CURATION_PROFILE and self.store.status(identifier) == 'active'
                and decision['type'] == 'decision' and json.loads(decision['payload']) == activation
                and all(isinstance(d.get(k), str) and d[k].strip() for k in ('applicability', 'reason', 'author'))
                and self.c._scope_current(identifier) and self.c._scope_current(d['target'])
                and self.store.get(d['target'])['hash'] == d['target_hash']
                and self.store.get(d['learning'], 'learning')['hash'] == d['learning_hash']
                and self.store.get(d['learning'])['data'].get('target') in {None, d['target']}
                and self.c.learning_current(d['learning']) and d['basis_hash'] == digest(d['basis'])
                and d['basis'] == self.c._source_semantics(d['learning']))
        except (StateError, KeyError, TypeError, ValueError, RecursionError):
            return False

    def selection(self, target, *, max_items=8):
        self.store.get(target, 'claim')
        if type(max_items) is not int or not 0 <= max_items <= 32:
            raise StateError('Learning selection needs a bounded item count from 0 to 32')
        with self.store.transaction():
            current, excluded, seen = [], 0, set()
            for admission in reversed(self.store.records('learning_admission')):
                d = admission['data']
                if d.get('target') != target:
                    if 'target' not in d:
                        excluded += 1
                    continue
                if not self.admission_current(admission['id']):
                    excluded += 1
                    continue
                if d['learning'] in seen:
                    continue
                seen.add(d['learning'])
                current.append({'learning': d['learning'], 'learning_hash': d['learning_hash'],
                    'admission': admission['id'], 'admission_hash': admission['hash'], 'applicability': d['applicability']})
            return {'profile': CURATION_PROFILE, 'target': target, 'selected': current[:max_items],
                'omitted_current': max(0, len(current) - max_items), 'excluded_stale_admissions': excluded,
                'authority': 'Explicitly admitted advisory history; never a premise or permission to accept'}
