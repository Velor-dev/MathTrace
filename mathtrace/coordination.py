"""Root advisory work identities; existing mathematical gates remain authoritative."""
from __future__ import annotations

import json

from .context import Tasks
from .execution import Executions
from .research import nonempty
from .store import StateError, digest

COORDINATION_PROFILE = 'source-bound-research-work-v1'
ROSTER_KINDS = {'route', 'obligation', 'inference', 'counterexample', 'application',
                'formal_plan', 'formal_receipt', 'experiment', 'candidate', 'release', 'learning', 'learning_admission', 'disposition-boundaries'}


class Coordination:
    def __init__(self, campaign):
        self.c, self.store = campaign, campaign.store
        self.tasks = Tasks(campaign)

    def _scope(self, target, work_target, anchors):
        self.store.get(target, 'claim')
        self.store.get(work_target)
        if not isinstance(anchors, dict) or set(anchors) - {'route', 'obligation'}:
            raise StateError('Work anchors must name an exact route and/or obligation')
        route = self.store.get(anchors['route'], 'route') if anchors.get('route') else None
        obligation = self.store.get(anchors['obligation'], 'obligation') if anchors.get('obligation') else None
        if obligation:
            linked = self.store.get(obligation['data']['route'], 'route')
            if route and route['id'] != linked['id']:
                raise StateError('Obligation and route work anchors disagree')
            route = linked
            if work_target not in {obligation['id'], obligation['data'].get('claim')}:
                raise StateError('Obligation work must assess its mapping or its exact linked subclaim')
        if route and route['data']['target'] != target:
            raise StateError('Route work anchor belongs to another campaign target')
        if self.tasks._claim_for(work_target) != target and not obligation:
            raise StateError('Subclaim work requires an exact linked campaign obligation')

    def _selectors(self, selectors):
        if not isinstance(selectors, list):
            raise StateError('Work basis selectors must be an exact list')
        result = []
        for selector in selectors:
            if not isinstance(selector, dict):
                raise StateError('Each work source selector must be a typed object')
            if set(selector) == {'kind', 'id'} and selector['kind'] == 'source':
                self.store.get(selector['id'])
            elif set(selector) == {'kind', 'target', 'categories'} and selector['kind'] == 'target-roster':
                self.store.get(selector['target'], 'claim')
                kinds = selector['categories']
                if (not isinstance(kinds, list) or not kinds or any(not isinstance(k, str) or k not in ROSTER_KINDS for k in kinds)
                        or len(set(kinds)) != len(kinds)):
                    raise StateError('Roster selectors need exact supported mathematical/advisory categories')
                selector = {**selector, 'categories': sorted(kinds)}
            else:
                raise StateError('Unknown work source selector')
            result.append(selector)
        return sorted({digest(s): s for s in result}.values(), key=digest)

    def _basis(self, selectors):
        result = {}
        for selector in selectors:
            if selector['kind'] == 'source':
                value = self.c._source_semantics(selector['id'])
            else:
                target = selector['target']
                ids = []
                boundaries = []
                for kind in selector['categories']:
                    if kind == 'disposition-boundaries':
                        for event in self.store.db.execute("SELECT seq,type,target,hash,payload FROM events WHERE type IN "
                            "('decision','execution-assessment','native-failure-assessment','ingestion-failure-assessment','formal-evidence-disposition') ORDER BY seq"):
                            payload = json.loads(event['payload'])
                            source = self.store.get(event['target'])
                            if event['type'] == 'decision' and not (source['kind'] == 'result' and payload.get('status') == 'incorporated'):
                                continue
                            if self.tasks._claim_for(source['id']) != target:
                                continue
                            boundaries.append({'revision': event['seq'], 'hash': event['hash'], 'type': event['type'],
                                'target': source['id'], 'condition': self.c._source_semantics(source['id']),
                                'followups': {r: self.c._source_semantics(r) for r in
                                    payload.get('reason', payload).get('followups', [])}})
                        continue
                    for record in self.store.records(kind):
                        relevant = self.tasks._claim_for(record['id']) == target
                        if kind == 'obligation':
                            relevant = self.store.get(record['data']['route'], 'route')['data']['target'] == target
                        if kind == 'learning':
                            relevant = record['data'].get('target') == target
                        if relevant:
                            ids.append(record['id'])
                value = {'records': {r: self.c._source_semantics(r) for r in sorted(ids)}, 'boundaries': boundaries}
            result[digest(selector)] = {'selector': selector, 'condition': value}
        return {'profile': COORDINATION_PROFILE, 'sources': result}

    def _permission(self, work_target, role):
        record = self.store.get(work_target)
        if record['kind'] == 'adjudication' and role == 'adjudicator':
            current = self.c._adjudication_current(work_target)
            return {'packet_allowed': current, 'subject': work_target,
                    'reason': 'Fresh informed review of both retained sides; no proof qualification'}
        scope = self.c._scope_condition(work_target)
        return {'packet_allowed': scope['current'], 'subject': work_target, 'scope': scope,
                'reason': 'Statement and source permission only; mathematical use has separate gates'}

    def inspect_work(self, identifier):
        with self.store.transaction():
            record = self.store.get(identifier, 'work_intent')
            d = record['data']
            task = self.store.get(d['task'], 'task')
            if (d.get('profile') != COORDINATION_PROFILE or task['data']['packet_hash'] != d['packet_hash']
                    or digest(task['data']['packet']) != d['packet_hash']
                    or task['data']['packet']['target'] != d['work_target']):
                raise StateError('Work intent does not bind its exact task/packet')
            basis = self._basis(d['selectors'])
            dispatches = [r for r in self.store.records('dispatch') if task['id'] in r['data']['tasks']]
            runs = [r for r in self.store.records('run') if r['data']['task'] == task['id']]
            outcomes = [r for kind in ('result', 'native_failure') for r in self.store.records(kind)
                        if r['data']['task'] == task['id']]
            terminal = []
            observations = []
            for outcome in outcomes:
                observed, producer_current, reason = False, False, None
                try:
                    self._terminal_source(record, outcome['id'])
                    observed = True
                    try:
                        self._terminal_source(record, outcome['id'], require_current=True)
                        producer_current = True
                    except StateError as error:
                        reason = str(error)
                except StateError as error:
                    reason = str(error)
                if observed:
                    terminal.append(outcome)
                observations.append({'id': outcome['id'], 'hash': outcome['hash'], 'kind': outcome['kind'],
                    'retained': True, 'producer_observed_terminal': observed,
                    'producer_attribution_current': producer_current, 'producer_limitation': reason,
                    'source_scope_current': self.c._scope_current(outcome['id'])})
            unknown = bool(dispatches or runs) and not terminal
            unchanged = digest(basis) == d['basis_hash']
            return {'intent': identifier, 'task': task['id'], 'packet_hash': d['packet_hash'],
                'target': d['target'], 'work_target': d['work_target'],
                'stored_status': self.store.status(identifier), 'task_status': self.store.status(task['id']),
                'basis_unchanged': unchanged,
                'permission': self._permission(d['work_target'], d['specification']['role']),
                'dispatches': [r['id'] for r in dispatches], 'runs': [r['id'] for r in runs],
                'terminal_outcomes': observations,
                'unknown_attempt': unknown, 'retry_authorized': False, 'mathematical_acceptance': False,
                'next_operation': 'capture/inspect existing native attempt' if unknown else
                    'reassess selected sources' if not unchanged else
                    'assess retained outcome' if outcomes else 'reserve exact task' if self.store.status(task['id']) == 'ready'
                        and self.store.status(identifier) == 'prepared'
                    else 'inspect historical task; retirement does not establish termination'}

    def _reply(self, retained, observation):
        current = self.inspect_work(retained['intent'])
        if retained.get('specification_matches') is False:
            current['next_operation'] = 'reassess changed task specification; historical task does not satisfy this request'
        return {**retained, 'observation': retained.get('observation', observation), 'delivery': observation, 'current': current,
                'retry_authorized': False, 'mathematical_acceptance': False}

    def prepare_work(self, target, key, instance, work_target, role, checks, mandate, rationale, *,
                     expected, request_id, independence='blind', literature='background-only',
                     background=None, anchors=None, selectors=None, relationship='fresh',
                     parent_intent=None, source=None, purpose=None):
        anchors, background = {} if anchors is None else anchors, [] if background is None else background
        for value, name in ((key, 'frontier key'), (instance, 'intent instance'), (rationale, 'root rationale'),
                            (request_id, 'request identity')):
            nonempty(value, name)
        if not isinstance(checks, list) or not checks or any(not isinstance(c, str) or not c.strip() for c in checks):
            raise StateError('Work checks must be exact nonempty obligations')
        if not isinstance(background, list) or any(not isinstance(b, str) or not b.strip() for b in background):
            raise StateError('Work background must be exact admitted source IDs')
        self._scope(target, work_target, anchors)
        if type(expected) is not int or expected < 0:
            raise StateError('Work preparation needs an exact nonnegative expected revision')
        if relationship not in {'fresh', 'parallel', 'successor', 'protocol-successor'}:
            raise StateError('Unknown work relationship; context expansion uses continue_work')
        lineage = None
        if relationship != 'fresh':
            parent = self.store.get(parent_intent, 'work_intent')
            if parent['data']['target'] != target:
                raise StateError('Work parent belongs to another campaign target')
            nonempty(purpose, 'explicit parallel/continuation purpose')
            if relationship == 'parallel':
                if source is not None:
                    raise StateError('Parallel work is separate from terminal successor work')
            else:
                self._terminal_source(parent, source, relationship)
            lineage = {'intent': parent_intent, 'intent_hash': parent['hash'],
                'task': parent['data']['task'], 'packet_hash': parent['data']['packet_hash'], 'source': source}
            if key == parent['data']['key'] and instance == parent['data']['instance']:
                raise StateError('Parallel/successor work needs a distinct instance')
        elif any(v is not None for v in (parent_intent, source, purpose)):
            raise StateError('Fresh work cannot conceal a continuation relationship')
        if selectors is None:
            selectors = [{'kind': 'source', 'id': work_target}]
        if not isinstance(selectors, list):
            raise StateError('Work selectors must be an exact list')
        if role == 'strategist' and independence == 'informed':
            selectors = [*selectors, {'kind': 'target-roster', 'target': target,
                'categories': ['route', 'obligation', 'inference', 'counterexample', 'formal_receipt',
                               'learning', 'learning_admission', 'disposition-boundaries']}]
        selectors = self._selectors([*selectors, {'kind': 'source', 'id': work_target},
            *[{'kind': 'source', 'id': b} for b in [*background, *anchors.values()]]])
        spec = {'role': role, 'checks': sorted(set(checks)), 'mandate': nonempty(mandate, 'worker mandate'),
            'independence': independence, 'literature': literature, 'background': list(dict.fromkeys(background))}
        identity = {'target': target, 'work_target': work_target, 'key': key, 'instance': instance,
            'specification': spec, 'anchors': anchors, 'selectors': selectors, 'relationship': relationship,
            'lineage': lineage, 'purpose': purpose, 'rationale': rationale}
        fingerprint = digest(identity)
        with self.store.transaction():
            prior = self.store.request('prepare-work:' + request_id, fingerprint)
            if prior is not None:
                return self._reply(prior, 'historical-request-replay')
            retained_lane = any(r['data']['target'] == target and r['data']['key'] == key
                                and r['data']['instance'] == instance for r in self.store.records('work_intent'))
            with self.store.transaction(None if retained_lane else expected):
                matches = [r for r in self.store.records('work_intent') if r['data']['target'] == target
                           and r['data']['key'] == key and r['data']['instance'] == instance]
                if len(matches) > 1:
                    raise StateError('Ambiguous durable work lane/instance')
                basis = self._basis(selectors)
                if matches:
                    spec_matches = matches[0]['data']['specification_hash'] == fingerprint
                    unchanged = (spec_matches
                                 and matches[0]['data']['basis_hash'] == digest(basis))
                    retained = {'intent': matches[0]['id'], 'task': matches[0]['data']['task'],
                        'observation': 'unchanged-work-recovery' if unchanged else 'reassessment-required',
                        'specification_matches': spec_matches}
                    self.store.finish_request('prepare-work:' + request_id, fingerprint, retained)
                    return self._reply(retained, 'unchanged-work-recovery' if unchanged else 'reassessment-required')
                if relationship == 'fresh' and any(r['data']['target'] == target and r['data']['key'] == key
                                                   for r in self.store.records('work_intent')):
                    raise StateError('Additional work in an existing lane needs explicit parallel/successor lineage and purpose')
                if not self._permission(work_target, role)['packet_allowed']:
                    raise StateError('Work packet lacks current statement/source permission; adjudicate or repair the exact hold')
                if relationship in {'successor', 'protocol-successor'}:
                    self._terminal_source(parent, source, relationship, require_current=True)
                task = self.tasks.create(role, work_target, checks=spec['checks'], mandate=mandate,
                    independence=independence, literature=literature, background=spec['background'])
                record = self._record_intent(identity, fingerprint, basis, task)
                retained = {'intent': record, 'task': task, 'observation': 'prepared', 'specification_matches': True}
                self.store.finish_request('prepare-work:' + request_id, fingerprint, retained)
                return self._reply(retained, 'prepared')

    def _record_intent(self, identity, fingerprint, basis, task):
        identifier = self.store.put('work_intent', {**identity, 'profile': COORDINATION_PROFILE,
            'target_hash': self.store.get(identity['target'])['hash'],
            'work_target_hash': self.store.get(identity['work_target'])['hash'],
            'specification_hash': fingerprint, 'basis': basis, 'basis_hash': digest(basis),
            'task': task, 'packet_hash': self.store.get(task, 'task')['data']['packet_hash'],
            'mathematical_acceptance': False, 'retry_authorized': False})
        self.store.decide(identifier, 'prepared', {'reason': 'Root selected exact work; task committed before native reservation'})
        return identifier

    def _terminal_source(self, parent, source, relationship=None, *, require_current=False):
        record = self.store.get(source)
        if record['kind'] not in {'result', 'native_failure'} or record['data']['task'] != parent['data']['task']:
            raise StateError('Continuation needs an actual terminal source of the exact parent task')
        if record['data']['packet_hash'] != parent['data']['packet_hash']:
            raise StateError('Continuation source addresses another parent packet')
        if record['kind'] == 'native_failure':
            from .native_capture import native_failure_evidence
            native_failure_evidence(self.store, source)
            if relationship == 'successor':
                raise StateError('A protocol failure needs an explicit protocol-successor relationship')
        else:
            row = self.store.db.execute("SELECT payload FROM events WHERE type='completion-qualification' AND target=?",
                                        (record['data']['run'],)).fetchone()
            if not row or json.loads(row['payload']) != {'captured': True, 'result': source}:
                raise StateError('Continuation requires retained producer-observed completion, not inferred termination')
            if relationship == 'protocol-successor':
                raise StateError('A valid result is not a protocol failure')
        if require_current:
            d = record['data']
            refs = [d['task'], d['run']]
            refs += [d['capture_artifact'], d['response_artifact']] if record['kind'] == 'native_failure' else [d['artifact'], d['host_receipt']]
            if (self.store.status(source) in {'withdrawn', 'rejected'} or self.c._blocked(source)
                    or any(not self.c._scope_current(r) for r in refs)):
                raise StateError('New continuation requires current producer evidence; retained historical bytes alone do not suffice')
        return record

    def continue_work(self, identifier, source, instance, rationale, *, expected, request_id,
                      added=None, becomes_informed=False):
        parent = self.store.get(identifier, 'work_intent')
        outcome = self._terminal_source(parent, source)
        if outcome['kind'] != 'result' or outcome['data']['outcome'] != 'context-request':
            raise StateError('This continuation operation extends an actual context request; use prepare_work for successors')
        if instance == parent['data']['instance']:
            raise StateError('Context continuation needs a distinct instance')
        nonempty(instance, 'continuation instance')
        nonempty(rationale, 'root continuation rationale')
        arguments = {'parent': parent['hash'], 'source': outcome['hash'], 'instance': instance,
                     'added': added, 'becomes_informed': becomes_informed, 'rationale': rationale}
        fingerprint = digest(arguments)
        with self.store.transaction():
            prior = self.store.request('continue-work:' + nonempty(request_id, 'request identity'), fingerprint)
            if prior is not None:
                return self._reply(prior, 'historical-request-replay')
            with self.store.transaction(expected):
                self._terminal_source(parent, source, require_current=True)
                if not self._permission(parent['data']['work_target'], parent['data']['specification']['role'])['packet_allowed']:
                    raise StateError('Context continuation needs current statement/source permission')
                if self.store.status(source) != 'context-needed':
                    raise StateError('Context continuation requires its exact unresolved request')
                if any(r['data']['target'] == parent['data']['target'] and r['data']['key'] == parent['data']['key']
                       and r['data']['instance'] == instance for r in self.store.records('work_intent')):
                    raise StateError('Continuation instance is already materialized')
                # Keep root lineage/rationale out of the worker's extension reason.
                task = self.tasks.extend(parent['data']['task'], added, 'Exact requested context expansion',
                                         becomes_informed=becomes_informed)
                self.store.decide(source, 'context-resolved', {'new_task': task, 'reason': rationale})
                packet = self.store.get(task, 'task')['data']['packet']
                selectors = self._selectors([*parent['data']['selectors'], {'kind': 'source', 'id': source},
                                            *[{'kind': 'source', 'id': r} for r in added]])
                spec = {**parent['data']['specification'], 'independence': packet['independence'],
                        'background': packet['admitted_sources']}
                identity = {'target': parent['data']['target'], 'work_target': parent['data']['work_target'],
                    'key': parent['data']['key'], 'instance': instance, 'specification': spec,
                    'anchors': parent['data']['anchors'], 'selectors': selectors, 'relationship': 'context-extension',
                    'lineage': {'intent': identifier, 'intent_hash': parent['hash'], 'task': parent['data']['task'],
                                'packet_hash': parent['data']['packet_hash'], 'source': source},
                    'purpose': 'Provide exact requested context in a new immutable packet', 'rationale': rationale}
                new = self._record_intent(identity, digest(identity), self._basis(selectors), task)
                retained = {'intent': new, 'task': task, 'observation': 'prepared-context-continuation',
                            'specification_matches': True}
                self.store.finish_request('continue-work:' + request_id, fingerprint, retained)
                return self._reply(retained, 'prepared-context-continuation')

    def frontier(self, target):
        with self.store.transaction():
            self.store.get(target, 'claim')
            from .orchestration import Orchestration
            items = []
            owned = [r for r in self.store.records('work_intent') if r['data']['target'] == target]
            linked_claims = {self.tasks._claim_for(r['data']['work_target']) for r in owned}
            linked_claims.update(o['data']['claim'] for o in self.store.records('obligation')
                if o['data'].get('claim') and self.store.get(o['data']['route'], 'route')['data']['target'] == target)
            linked_claims.discard(None)
            def add(key, action, work_target, role=None, anchors=None, selectors=None, detail=None):
                selectors = self._selectors(selectors or [{'kind': 'source', 'id': work_target}])
                intents = [r['id'] for r in self.store.records('work_intent')
                           if r['data']['target'] == target and r['data']['key'] == key]
                items.append({'key': key, 'action': action, 'target': target, 'work_target': work_target,
                    'role': role, 'anchors': anchors or {}, 'selectors': selectors,
                    'basis_hash': digest(self._basis(selectors)), 'permission': self._permission(work_target, role),
                    'existing_work': [self.inspect_work(r) for r in intents], 'detail': detail,
                    'mathematical_acceptance': False, 'retry_authorized': False})
            for action in Orchestration(self.c)._next_actions()['actions']:
                anchors = [action[k] for k in ('target', 'task', 'result', 'run', 'failure', 'conflict',
                                              'execution', 'candidate', 'release', 'case', 'review') if action.get(k)]
                anchors += action.get('targets', [])
                relevant = [r for r in anchors if self.tasks._claim_for(r) in linked_claims | {target}
                    or (self.store.get(r)['kind'] == 'obligation'
                        and self.store.get(self.store.get(r)['data']['route'], 'route')['data']['target'] == target)]
                if relevant:
                    anchor = relevant[0]
                    detail = {**action}
                    if 'targets' in detail:
                        detail['targets'] = [r for r in detail['targets'] if r in relevant]
                    add(action['action'] + ':' + anchor, action['action'], anchor, detail=detail)
            for intent in owned:
                add('retained-work:' + intent['id'], 'inspect-owned-work', intent['data']['work_target'],
                    anchors=intent['data']['anchors'], selectors=intent['data']['selectors'],
                    detail=self.inspect_work(intent['id']))
            for obligation in self.store.records('obligation'):
                route = self.store.get(obligation['data']['route'], 'route')
                if route['data']['target'] == target and self.c.obligation_open(obligation):
                    work = obligation['data'].get('claim') or obligation['id']
                    add('obligation:' + obligation['id'], 'research-obligation', work, 'scout' if work != obligation['id'] else None,
                        anchors={'route': route['id'], 'obligation': obligation['id']},
                        selectors=[{'kind': 'source', 'id': work}, {'kind': 'source', 'id': obligation['id']}])
            state = self.c.claim_state(target)
            from .completion import Completion
            scoped_requests = [r for r in self.store.records('completion_request')
                if self.store.status(r['id']) == 'active'
                and any(o['target'] == target for o in r['data']['outputs'])]
            scoped_drafts = [r['id'] for r in self.store.records('completion_request')
                if self.store.status(r['id']) == 'draft'
                and any(o['target'] == target for o in r['data']['outputs'])]
            scoped_fulfillment = [Completion(self.c).fulfillment(r['id']) for r in scoped_requests]
            sufficient = bool(scoped_fulfillment) and all(r['mathematics_sufficient'] for r in scoped_fulfillment)
            fulfilled = sufficient and all(r['contract_fulfilled'] for r in scoped_fulfillment)
            if sufficient:
                add('completion:' + target, 'contract-fulfilled' if fulfilled else 'finish-requested-delivery',
                    target, detail={'requests': [r['id'] for r in scoped_requests],
                                    'research_exhaustion': 'not-claimed'})
            if state['state'] != 'refuted':
                add('discover:' + target, 'independent-discovery', target, 'scout')
                add('falsify:' + target, 'independent-falsification', target, 'falsifier')
                add('strategy:' + target, 'informed-strategy', target, 'strategist',
                    selectors=[{'kind': 'source', 'id': target}, {'kind': 'target-roster', 'target': target,
                'categories': ['route', 'obligation', 'inference', 'counterexample', 'formal_receipt', 'learning', 'learning_admission', 'disposition-boundaries']}])
            for item in items:
                item['optional_research'] = sufficient and item['action'] in {
                    'independent-discovery', 'independent-falsification', 'informed-strategy', 'research-obligation',
                    'reclassify-route-decision', 'reassess-route-decision', 'curate-or-decline-local-learning',
                    'reextract-or-decline-stale-learning', 'admit-target-local-learning'}
            return {'profile': COORDINATION_PROFILE, 'target': target, 'revision': self.store.revision,
                'items': items, 'target_state': state, 'solved': fulfilled,
                'contract_fulfilled': fulfilled, 'mathematics_sufficient': sufficient,
                'completion_bound': bool(scoped_requests), 'completion_requests': scoped_fulfillment,
                'draft_completion_requests': scoped_drafts,
                'research_exhaustion': 'not-claimed', 'autonomous_exploration_required': not sufficient,
                'authority': 'Root work selection only; complementary lanes do not confer acceptance or retries'}
