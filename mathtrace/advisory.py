"""Exact root coordination certificates; never mathematical acceptance."""
from __future__ import annotations

import json

from .research import nonempty
from .store import StateError, digest, ZERO_HASH

ROUTE_PROFILE = 'source-bound-route-decision-v1'
BOUNDARY_PROFILE = 'exact-advisory-event-boundary-v1'
BOUNDARY_TYPES = {'decision', 'execution-terminal', 'completion-qualification', 'execution-assessment',
    'native-failure-assessment', 'ingestion-failure-assessment', 'formal-evidence-disposition',
    'counterexample-report-disposed', 'finding-impact-certified', 'registered'}
ROUTE_STATUSES = {'active', 'blocked', 'dormant', 'refuted', 'closed'}


class Advisory:
    def __init__(self, campaign):
        self.c, self.store = campaign, campaign.store

    def event(self, revision, event_hash):
        if type(revision) is not int or revision < 1 or not isinstance(event_hash, str):
            raise StateError('Boundary needs an exact event revision and hash')
        row = self.store.db.execute('SELECT * FROM events WHERE seq=?', (revision,)).fetchone()
        if row is None or row['hash'] != event_hash or row['type'] not in BOUNDARY_TYPES:
            raise StateError('Boundary is not a supported authentic canonical event')
        source = self.store.get(row['target'])
        payload = json.loads(row['payload'])
        previous = self.store.db.execute('SELECT hash FROM events WHERE seq=?', (revision - 1,)).fetchone()
        body = {'seq': row['seq'], 'type': row['type'], 'target': row['target'], 'data': payload,
                'created': row['created'], 'previous_hash': row['previous_hash']}
        if (digest(body) != row['hash'] or row['previous_hash'] != (previous['hash'] if previous else ZERO_HASH)
                or (revision > 1 and previous is None)):
            raise StateError('Boundary event hash/address is not intact')
        if not isinstance(payload, dict):
            raise StateError('Boundary payload must have its typed event shape')
        expected = {'registered': {'checkpoint'}, 'completion-qualification': {'run'},
            'execution-terminal': {'execution'}, 'execution-assessment': {'execution'},
            'native-failure-assessment': {'native_failure'}, 'ingestion-failure-assessment': {'ingestion_failure'},
            'formal-evidence-disposition': {'formal_receipt'}, 'counterexample-report-disposed': {'result'},
            'finding-impact-certified': {'objection', 'review'}}
        if row['type'] in expected and source['kind'] not in expected[row['type']]:
            raise StateError('Boundary event type does not match its exact subject kind')
        if row['type'] == 'registered' and source['kind'] != 'checkpoint':
            raise StateError('Only a checkpoint registration is an extractable registered boundary')
        if row['type'] == 'decision' and not (
                source['kind'] in {'route', 'inference', 'counterexample', 'candidate', 'release', 'adjudication', 'obligation'}
                or (source['kind'] == 'result' and payload.get('status') == 'incorporated')):
            raise StateError('This decision is not a substantive research boundary')
        try:
            self._event_payload(row['type'], source, payload, revision)
        except (KeyError, TypeError, ValueError) as error:
            raise StateError('Boundary lacks its exact typed payload binding: ' + str(error)) from error
        return {'revision': row['seq'], 'hash': row['hash'], 'type': row['type'], 'target': row['target'],
                'target_hash': source['hash'], 'payload': payload}

    def _event_payload(self, kind, source, payload, revision):
        if kind == 'registered':
            if payload != {'kind': 'checkpoint', 'record_hash': source['hash']}:
                raise StateError('Checkpoint registration does not bind its exact record')
        elif kind == 'decision':
            latest = self.store.db.execute("SELECT seq FROM events WHERE target=? AND type IN ('registered','decision') "
                'ORDER BY seq DESC LIMIT 1', (source['id'],)).fetchone()
            projected = self.store.db.execute('SELECT event_seq FROM decisions WHERE target=?', (source['id'],)).fetchone()
            if not projected or not latest or projected['event_seq'] != latest['seq']:
                raise StateError('Boundary subject has an inconsistent derived decision projection')
            statuses = {'route': ROUTE_STATUSES | {'withdrawn', 'rejected'}, 'inference': {'accepted', 'withdrawn', 'rejected'},
                'counterexample': {'validated', 'dismissed', 'withdrawn', 'rejected', 'provenance-retracted'},
                'candidate': {'audited', 'withdrawn', 'rejected'}, 'release': {'released', 'superseded', 'withdrawn', 'rejected'},
                'adjudication': {'resolved', 'withdrawn', 'rejected'}, 'obligation': {'satisfied', 'withdrawn', 'rejected'},
                'result': {'incorporated'}}
            if (set(payload) != {'status', 'reason'} or payload['status'] not in statuses[source['kind']]
                    or not isinstance(payload['reason'], dict) or not payload['reason']):
                raise StateError('Unsupported research decision shape/status')
        elif kind == 'completion-qualification':
            if set(payload) != {'captured', 'result'} or type(payload['captured']) is not bool:
                raise StateError('Completion boundary lacks exact qualification/result fields')
            result = self.store.get(payload['result'], 'result')['data']
            if result['run'] != source['id'] or result['task'] != source['data']['task']:
                raise StateError('Completion boundary does not bind this run/result')
            for subject in (source['id'], source['data']['task']):
                row = self.store.db.execute("SELECT payload FROM events WHERE type='decision' AND target=? AND seq<? "
                    'ORDER BY seq DESC LIMIT 1', (subject, revision)).fetchone()
                phase = json.loads(row['payload']) if row else {}
                if phase.get('status') != 'completed' or phase.get('reason', {}).get('result') != payload['result']:
                    raise StateError('Completion boundary lacks the actual completed run/task decisions')
            from .context import Tasks
            from .results import worker_result, RESULT_CONTRACT_V1
            from .native_capture import strict_json
            packet = Tasks(self.c).packet(result['task'])
            text = self.store.get(result['artifact'], 'artifact')['data']['text']
            receipt = strict_json(self.store.get(result['host_receipt'], 'artifact')['data']['text'])
            output = worker_result(self.store.get(result['task'])['data']['packet'], result['task'],
                result['packet_hash'], text, profile=result.get('result_contract_profile', RESULT_CONTRACT_V1))
            if (result['packet_hash'] != packet['packet_hash'] or source['data']['packet_hash'] != packet['packet_hash']
                    or result['target'] != packet['target'] or result['target_hash'] != packet['target_hash']
                    or receipt.get('status') != 'SUCCESS' or receipt.get('conversation_id') != source['data']['conversation_id']
                    or receipt.get('response') != text or output['outcome'] != result['outcome']
                    or output.get('verdict') != result['verdict'] or sorted(set(output.get('checks', []))) != result['checks']):
                raise StateError('Completion boundary lacks its exact packet/response/receipt binding')
            captured = self.store.db.execute("SELECT payload FROM events WHERE type='capture-qualification' AND target=? AND seq<?",
                                            (source['id'], revision)).fetchone()
            if payload['captured'] and (not captured or json.loads(captured['payload']).get('captured') is not True):
                raise StateError('Reported dispatch cannot become an observed completion')
        elif kind in {'execution-terminal', 'execution-assessment'}:
            from .execution import Executions
            terminal = Executions(self.c)._terminal_response(source['id'])
            if terminal is None or any(payload.get(k) != terminal[k] for k in ('observation', 'receipt')):
                raise StateError('Execution boundary lacks its actual retained observation/receipt')
            observation = self.store.get(terminal['observation'], 'artifact')
            expected_hash = observation['data']['content_hash'] if kind == 'execution-terminal' else observation['hash']
            if payload.get('observation_hash') != expected_hash:
                raise StateError('Execution boundary observation identity differs')
            nonempty(payload.get('reason'), 'execution boundary reason')
            if kind == 'execution-assessment':
                if payload.get('mathematical_acceptance') is not False or not isinstance(payload.get('followups'), list):
                    raise StateError('Execution assessment cannot assert mathematical acceptance')
                nonempty(payload.get('reopen_condition'), 'execution reopening condition')
                for r in payload['followups']:
                    self.store.get(r)
        elif kind in {'native-failure-assessment', 'ingestion-failure-assessment'}:
            artifact = self.store.get(payload['assessment_artifact'], 'artifact')
            nonempty(payload.get('reopen_condition'), 'failure reopening condition')
            if (payload.get('mathematical_acceptance') is not False or payload.get('retry_authorized') is not False
                    or not isinstance(payload.get('followups'), list)
                    or payload['basis_hash'] != digest(payload['basis'])):
                raise StateError('Failure assessment lacks its source-bound operational shape')
            if kind == 'native-failure-assessment' and (payload['failure_hash'] != source['hash']
                    or payload['assessment_hash'] != artifact['hash']):
                raise StateError('Failure assessment hash binding differs')
            for r in payload['followups']:
                self.store.get(r)
        elif kind == 'formal-evidence-disposition':
            if (payload['receipt_hash'] != source['hash'] or payload['basis_hash'] != digest(payload['basis'])
                    or payload.get('disposition') != 'deferred' or payload.get('mathematical_acceptance') is not False):
                raise StateError('Formal disposition lacks its exact advisory binding')
            nonempty(payload.get('reason'), 'formal disposition reason')
            nonempty(payload.get('reopen_condition'), 'formal reopening condition')
            for r in payload['basis_sources']:
                self.store.get(r)
        elif kind in {'counterexample-report-disposed', 'finding-impact-certified'}:
            resolution = self.store.get(payload['resolution'], 'resolution')['data']
            if resolution.get('finding', resolution.get('objection')) != source['id']:
                raise StateError('Disposition boundary addresses another finding')
            if kind == 'counterexample-report-disposed':
                if source['data']['outcome'] != 'counterexample' or resolution['disposition'] != 'dismissed':
                    raise StateError('Not an exact counterexample report disposition')
                case = self.store.get(resolution['case'], 'adjudication')['data']
                if case['finding'] != source['id'] or case.get('report_disposition') not in {'invalid', 'irrelevant', 'unsubstantiated'}:
                    raise StateError('Report boundary lacks its exact substantive case')
            elif (resolution['disposition'] != 'scope-classified' or payload.get('impact') != 'unconditional-truth'
                    or payload.get('substantive_acceptance') is not False):
                raise StateError('Finding scope boundary cannot assert substantive acceptance')
            elif source['kind'] == 'review' and source['data']['verdict'] != 'fail':
                raise StateError('A passing review is not a scope-held finding')

    def boundary(self, revision, event_hash, *, target):
        with self.store.transaction():
            event = self.event(revision, event_hash)
            if event['target'] != target:
                raise StateError('Boundary target does not match the addressed event')
            data = {'profile': BOUNDARY_PROFILE, 'event': event,
                    'authority': 'Immutable historical boundary; no current mathematical acceptance'}
            for old in self.store.records('boundary_certificate'):
                if old['data'] == data:
                    return old['id']
            return self.store.put('boundary_certificate', data)

    def boundary_data(self, identifier):
        data = self.store.get(identifier, 'boundary_certificate')['data']
        event = data['event']
        if (data.get('profile') != BOUNDARY_PROFILE
                or self.event(event['revision'], event['hash']) != event):
            raise StateError('Boundary lacks its exact authentic event binding')
        return data

    def _latest(self, route):
        row = self.store.db.execute('SELECT e.seq,e.hash,e.payload FROM events e JOIN decisions d '
            'ON d.event_seq=e.seq WHERE d.target=?', (route,)).fetchone()
        if row is None:
            raise StateError('Route lacks a canonical decision')
        return {'revision': row['seq'], 'hash': row['hash'], **json.loads(row['payload'])}

    def _basis(self, route, sources):
        basis = {}
        for source in sources:
            value = self.c._source_semantics(source)
            # The flat source reader follows actual dependencies transitively.
            # A historical boundary may address this route without reading its
            # mutable disposition; a raw route or indirect source may not.
            if route in value['conditions']:
                raise StateError('Route decision basis may not depend on its own mutable disposition')
            basis[source] = value
        return basis

    def transition(self, route, status, certificate, *, sources, rationale, reopen_condition,
                   author, expected, previous_decision, request_id):
        record = self.store.get(route, 'route')
        self.store.get(certificate, 'artifact')
        if status not in ROUTE_STATUSES:
            raise StateError('Unknown route status')
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or not s.strip() for s in sources)
                or len(set(sources)) != len(sources)):
            raise StateError('Route decisions require exact distinct external sources')
        for source in sources:
            self.store.get(source)
        nonempty(rationale, 'route decision rationale')
        nonempty(reopen_condition, 'route reopening condition')
        nonempty(author, 'route decision author')
        nonempty(previous_decision, 'exact previous route decision hash')
        nonempty(request_id, 'route decision request identity')
        arguments = {'route': record['hash'], 'status': status, 'certificate': certificate, 'sources': sources,
            'rationale': rationale, 'reopen_condition': reopen_condition, 'author': author,
            'previous_decision': previous_decision}
        fingerprint = digest(arguments)
        with self.store.transaction():
            old = self.store.request('route-transition:' + request_id, fingerprint)
            if old is not None:
                return {**old, 'current': self.condition(route)['certificate'] == old['certificate']
                        and self.condition(route)['current']}
            with self.store.transaction(expected):
                latest = self._latest(route)
                if latest['hash'] != previous_decision:
                    raise StateError('Route decision changed; inspect its exact current boundary')
                if self.store.status(route) in {'withdrawn', 'rejected'} or not self.c._scope_current(certificate):
                    raise StateError('Withdrawn route or unavailable decision certificate needs explicit repair')
                basis_sources = list(dict.fromkeys([certificate, *sources]))
                basis = self._basis(route, basis_sources)
                decision = self.store.put('route_decision', {'profile': ROUTE_PROFILE,
                    'route': route, 'route_hash': record['hash'], 'target': record['data']['target'],
                    'target_hash': self.store.get(record['data']['target'])['hash'], 'status': status,
                    'previous_decision': latest, 'artifact': certificate, 'sources': basis_sources,
                    'basis': basis, 'basis_hash': digest(basis), 'rationale': rationale, 'author': author,
                    'reopen_condition': reopen_condition, 'mathematical_acceptance': False})
                self.store.decide(route, status, {'certificate': decision, 'profile': ROUTE_PROFILE,
                    'reopen_condition': reopen_condition, 'mathematical_acceptance': False})
                reply = {'route': route, 'certificate': decision, 'status': status, 'mathematical_acceptance': False}
                self.store.finish_request('route-transition:' + request_id, fingerprint, reply)
                return {**reply, 'current': self.condition(route)['current']}

    def condition(self, route):
        with self.store.transaction():
            record = self.store.get(route, 'route')
            latest = self._latest(route)
            reason = latest['reason']
            certificate = reason.get('certificate')
            base = {'route': route, 'status': self.store.status(route), 'decision_hash': latest['hash'],
                'certificate': certificate, 'current': False, 'needs_reclassification': False,
                'mathematical_acceptance': False}
            if not certificate and latest['status'] == 'active' and reason.get('reason') == 'Independent route registered':
                return {**base, 'current': self.c._scope_current(route) and self.c._scope_current(record['data']['target']),
                        'reason': 'Initial scheduling declaration; no mathematical disposition'}
            if not certificate or self.store.get(certificate)['kind'] != 'route_decision':
                return {**base, 'needs_reclassification': True,
                        'reason': 'Legacy unbound disposition retained as history; current applicability unavailable'}
            try:
                d = self.store.get(certificate, 'route_decision')['data']
                self.store.get(d['artifact'], 'artifact')
                if (d['status'] not in ROUTE_STATUSES or not isinstance(d['sources'], list) or not d['sources']
                        or any(not isinstance(s, str) or not s.strip() for s in d['sources'])
                        or len(set(d['sources'])) != len(d['sources']) or d['artifact'] not in d['sources']
                        or not all(isinstance(d.get(k), str) and d[k].strip()
                                   for k in ('rationale', 'author', 'reopen_condition'))
                        or d.get('mathematical_acceptance') is not False):
                    return {**base, 'reason': 'Malformed exact route decision fields'}
                prior = d['previous_decision']
                prior_event = self.event(prior['revision'], prior['hash'])
                if (reason.get('profile') != ROUTE_PROFILE or d.get('profile') != ROUTE_PROFILE
                        or d['route'] != route or d['route_hash'] != record['hash']
                        or d['target'] != record['data']['target'] or d['status'] != latest['status']
                        or d['target_hash'] != self.store.get(d['target'])['hash']
                        or prior_event['target'] != route or prior_event['type'] != 'decision'
                        or prior['revision'] >= latest['revision']
                        or prior_event['payload'] != {'status': prior['status'], 'reason': prior['reason']}
                        or d['basis_hash'] != digest(d['basis']) or not d['sources']
                        or d['basis'] != self._basis(route, d['sources'])):
                    return {**base, 'reason': 'Exact route source conditions changed or certificate is malformed'}
                current = all(self.c._scope_current(r) for r in [route, certificate, d['artifact'], d['target']])
                return {**base, 'current': current, 'reason': None if current else 'Route/certificate/target hold remains',
                        'rationale': d['rationale'], 'reopen_condition': d['reopen_condition']}
            except (StateError, KeyError, TypeError, ValueError, RecursionError) as error:
                return {**base, 'reason': str(error)}
