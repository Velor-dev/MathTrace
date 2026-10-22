"""Root-owned adaptive orchestration and transactional worker-result ingestion."""

from __future__ import annotations

import json

from .campaign import Campaign
from .research import nonempty
from .context import Tasks
from .evidence import Evidence
from .store import StateError, InputContractError, digest, ZERO_HASH
from .results import worker_result, ResultProtocolError, RESULT_CONTRACT_PROFILE


class ProposalContractError(StateError):
    """A retained result violates the explicit proposal import contract."""


class Orchestration:
    def __init__(self, campaign: Campaign):
        self.c = campaign
        self.store = campaign.store
        self.tasks = Tasks(campaign)

    def strategize(self, target: str) -> str:
        return self.tasks.create('strategist', target, independence='informed',
            checks=['route-portfolio', 'falsification', 'next-obligations'],
            mandate='Use the exact current portfolio to choose complementary next routes, falsification and obligation work. Explain blocked routes and reopening conditions. Return proposals; do not equate route exhaustion or votes with proof.')

    def _native_failure_basis(self, identifier, assessment, followups):
        sources = [identifier, assessment, *followups]
        return {s: self.c._source_semantics(s) for s in dict.fromkeys(sources)}

    def _native_failure_assessment_current(self, identifier, certificate):
        return certificate.get('basis_hash') == digest(self._native_failure_basis(identifier,
            certificate['assessment_artifact'], certificate['followups']))

    def _failure_followup_scope(self, subject, followup):
        record = self.store.get(followup)
        kind, d = record['kind'], record['data']
        claim = self.tasks._claim_for(subject)
        if kind == 'task':
            return (d['packet']['claim'] == claim if claim is not None else
                    d['packet']['target'] == subject and d['packet']['context_type'] == 'infrastructure')
        if kind == 'obligation':
            return claim is not None and self.store.get(d['route'], 'route')['data']['target'] == claim
        if claim is None:
            return followup == subject or (kind in {'objection', 'review', 'adjudication'}
                and d.get('target', d.get('subject')) == subject)
        if kind == 'claim':
            return followup == claim
        return kind in {'inference', 'counterexample', 'application', 'formal_plan', 'formal_receipt',
                        'experiment', 'execution', 'candidate', 'release', 'route', 'objection',
                        'review', 'adjudication', 'native_failure'} and self.tasks._claim_for(followup) == claim

    def assess_native_failure(self, identifier: str, assessment_artifact: str, followups: list[str],
                              reopen_condition: str, *, expected: int, request_id: str) -> dict:
        """Root interpretation of actual response substance; never a retry gate."""
        failure = self.store.get(identifier, 'native_failure')
        assessment = self.store.get(assessment_artifact, 'artifact')
        nonempty(assessment['data']['text'], 'assessment of the retained response and any negative evidence')
        nonempty(reopen_condition, 'reopening condition')
        nonempty(request_id, 'request identity')
        if (not isinstance(followups, list) or any(not isinstance(f, str) or not f.strip() for f in followups)
                or len(followups) != len(set(followups))):
            raise StateError('Native failure followups must be exact distinct record IDs')
        key = 'assess-native-failure:' + request_id
        fingerprint = digest({'failure': failure['hash'], 'assessment': assessment['hash'],
                              'followups': followups, 'reopen_condition': reopen_condition})
        with self.store.transaction():
            from .native_capture import native_failure_evidence
            native_failure_evidence(self.store, identifier)
            previous = self.store.request(key, fingerprint)
            if previous is not None:
                row = self.store.db.execute('SELECT payload FROM events WHERE seq=?',
                                            (previous['assessment_revision'],)).fetchone()
                return {**previous, 'current': self._native_failure_assessment_current(identifier, json.loads(row['payload']))}
            with self.store.transaction(expected):
                if not self.c._scope_current(assessment_artifact):
                    raise StateError('Assessment artifact scope is not current')
                for followup in followups:
                    if not self._failure_followup_scope(failure['data']['target'], followup):
                        raise StateError('Failure followups need exact target scope')
                basis = self._native_failure_basis(identifier, assessment_artifact, followups)
                certificate = {'failure_hash': failure['hash'], 'assessment_artifact': assessment_artifact,
                    'assessment_hash': assessment['hash'], 'followups': followups,
                    'basis': basis, 'basis_hash': digest(basis), 'reopen_condition': reopen_condition,
                    'source_scope_at_assessment': self.c._scope_condition(identifier),
                    'authority': 'root interpretation of retained response; no mathematical finding is dismissed',
                    'mathematical_acceptance': False, 'retry_authorized': False}
                revision = self.store.event('native-failure-assessment', identifier, certificate)
                response = {'failure': identifier, 'assessment_revision': revision,
                            'mathematical_acceptance': False, 'retry_authorized': False}
                self.store.finish_request(key, fingerprint, response)
                return {**response, 'current': True}

    def assess_execution(self, identifier: str, reason: str, followups: list[str], reopen_condition: str) -> dict:
        """Preserve root assessment of observed output without accepting mathematics."""
        if not isinstance(followups, list) or any(not isinstance(f, str) or not f.strip() for f in followups):
            raise StateError('Execution followups must identify exact records')
        followups = list(dict.fromkeys(followups))
        with self.store.transaction():
            execution = self.store.get(identifier, 'execution')
            terminal = Evidence(self.c).inspect_execution(identifier).get('terminal')
            if terminal is None:
                raise StateError('Unobserved execution cannot be operationally closed')
            target = self.store.get(execution['data']['plan'])['data']['target']
            for followup in followups:
                record = self.store.get(followup)
                kind, data = record['kind'], record['data']
                relevant = data.get('target') == target or data.get('conclusion') == target
                if kind == 'claim':
                    relevant = followup == target
                elif kind == 'task':
                    relevant = data['packet']['claim'] == target
                elif kind == 'obligation':
                    relevant = self.store.get(data['route'], 'route')['data']['target'] == target
                elif kind == 'learning':
                    relevant = bool(set(data['sources']) & {identifier, terminal['receipt'], terminal['observation']})
                if not relevant:
                    raise StateError('Execution followup needs exact target scope or source-bound local learning')
            certificate = {'observation': terminal['observation'],
                'observation_hash': self.store.get(terminal['observation'])['hash'], 'receipt': terminal['receipt'],
                'outcome': self.store.status(terminal['receipt']) if terminal['receipt'] else 'backend-failure',
                'reason': nonempty(reason, 'execution assessment'), 'followups': followups,
                'reopen_condition': nonempty(reopen_condition, 'reopening condition'), 'mathematical_acceptance': False}
            prior = self.store.db.execute("SELECT payload,seq FROM events WHERE type='execution-assessment' "
                                          'AND target=? ORDER BY seq DESC LIMIT 1', (identifier,)).fetchone()
            revision = (prior['seq'] if prior and json.loads(prior['payload']) == certificate
                        else self.store.event('execution-assessment', identifier, certificate))
            return {'execution': identifier, 'assessment_revision': revision, 'mathematical_acceptance': False}

    def inspect_record(self, identifier: str, *, full: bool = False) -> dict:
        """Retrieve one identified record; never load unrelated campaign history."""
        if not isinstance(full, bool):
            raise StateError('full must be a boolean')
        with self.store.transaction():
            record = self.store.get(identifier)
            if not full:
                data = self.tasks._project_data(record['kind'], record['data'])
                if 'author' in record['data']:
                    data['author'] = record['data']['author']
                if record['kind'] == 'artifact' and isinstance(data.get('text'), str):
                    data['text'] = self.tasks._bound_stream(data['text'])
                record = {**record, 'data': data}
            response = {'record': record, 'projection': 'canonical' if full else 'bounded-root-inspection',
                'revision': self.store.revision, 'stored_status': self.store.status(identifier),
                'note': 'Stored decisions alone do not establish current mathematical eligibility. Root inspection is not a blind worker packet.'}
            if record['kind'] == 'claim':
                response['current_state'] = self.c.claim_state(identifier)
            return response

    def dispose_formal_evidence(self, identifier: str, reason: str, reopen_condition: str,
                                *, basis_sources: list[str] | None = None) -> dict:
        """Explicit advisory non-use; never assessment, acceptance or repair."""
        if basis_sources is not None and (not isinstance(basis_sources, list)
                or any(not isinstance(s, str) or not s.strip() for s in basis_sources)):
            raise StateError('Disposition basis_sources must be an exact list of record IDs')
        basis_sources = list(dict.fromkeys(basis_sources or []))
        with self.store.transaction():
            receipt = self.store.get(identifier, 'formal_receipt')
            if not self.c._formal_current(identifier):
                raise StateError('Formal evidence must be qualified before deliberate non-use; repair and review remain separate')
            references = self.c._formal_references(identifier)
            if any(r['use'] != 'unusable' for r in references):
                raise StateError('Formal evidence already has an active mathematical route; dispose of that route explicitly first')
            basis = self.c._formal_disposition_basis(identifier, references, basis_sources)
            certificate = {'receipt_hash': receipt['hash'], 'basis': basis, 'basis_hash': digest(basis),
                           'basis_sources': basis_sources,
                           'disposition': 'deferred', 'reason': nonempty(reason, 'formal evidence disposition'),
                           'reopen_condition': nonempty(reopen_condition, 'reopening condition'),
                           'mathematical_acceptance': False}
            prior = self.store.db.execute("SELECT payload,seq FROM events WHERE type='formal-evidence-disposition' "
                                          'AND target=? ORDER BY seq DESC LIMIT 1', (identifier,)).fetchone()
            revision = (prior['seq'] if prior and json.loads(prior['payload']) == certificate
                        else self.store.event('formal-evidence-disposition', identifier, certificate))
            return {'receipt': identifier, 'disposition_revision': revision, 'mathematical_acceptance': False}

    def dispose_result(self, result: str, reason: str, followups: list[str], reopen_condition: str) -> dict:
        if not isinstance(reason, str) or not reason.strip() or not isinstance(reopen_condition, str) or not reopen_condition.strip():
            raise StateError('A result disposition needs reasons and an explicit reopening condition')
        if not isinstance(followups, list) or any(not isinstance(f, str) or not f.strip() for f in followups):
            raise StateError('Followups must identify exact records')
        followups = list(dict.fromkeys(followups))
        with self.store.transaction():
            data = self.store.get(result, 'result')['data']
            if self.store.status(result) != 'imported':
                raise StateError('Only an imported result may receive an operational disposition')
            target = self.tasks.packet(data['task'])['claim']
            imported = set()
            for event in self.store.db.execute("SELECT payload FROM events WHERE type='proposal-import' AND target=?", (result,)):
                imported.update(json.loads(event['payload'])['created'])
            for identifier in followups:
                record = self.store.get(identifier)
                kind, payload = record['kind'], record['data']
                relevant = (identifier in imported and kind != 'artifact')
                if kind in {'route', 'counterexample', 'experiment', 'formal_plan'}:
                    relevant |= payload['target'] == target
                elif kind in {'inference', 'application'}:
                    relevant |= payload['conclusion'] == target
                elif kind == 'obligation':
                    relevant |= self.store.get(payload['route'], 'route')['data']['target'] == target
                elif kind == 'task':
                    relevant |= (payload['packet']['claim'] == target or payload['packet']['target'] in imported)
                elif kind == 'claim':
                    relevant |= identifier == target
                if not relevant:
                    raise StateError('Followup must be target-scoped work or a proposal imported from this result')
            self.store.decide(result, 'incorporated', {'reason': reason, 'followups': followups,
                'reopen_condition': reopen_condition, 'mathematical_acceptance': False})
            return {'result': result, 'mathematical_acceptance': False}

    def ingest(self, result: str) -> dict:
        record = self.store.get(result, 'result')
        data = record['data']
        fingerprint = digest({'result': record['hash']})
        with self.store.transaction():
            prior = self.store.request('ingest:' + result, fingerprint)
        if prior is not None:
            return prior
        # Only explicit worker syntax/proposal contract failures are quarantined.
        # Database, attribution, review and constructor integrity errors propagate.
        try:
            worker_result(self.tasks.packet(data['task']), data['task'], data['packet_hash'],
                          self.store.get(data['artifact'], 'artifact')['data']['text'])
            return self._ingest(result)
        except (ProposalContractError, ResultProtocolError, InputContractError) as error:
            with self.store.transaction():
                prior = self.store.request('ingest:' + result, fingerprint)
                if prior is not None:
                    return prior
                run = self.store.get(data['run'], 'run')
                if self.store.status(run['id']) != 'completed' or self.store.status(result) != 'proposed':
                    raise StateError('Quarantine requires the actual unimported completed result')
                failure = self.store.put('ingestion_failure', {'profile': 'exact-proposal-ingestion-failure-v1',
                    'rejecting_result_contract_profile': RESULT_CONTRACT_PROFILE,
                    'proposal_contract_profile': 'exact-proposal-import-contract-v1',
                    'result': result, 'result_hash': record['hash'], 'task': data['task'], 'run': data['run'],
                    'target': data['target'], 'packet_hash': data['packet_hash'],
                    'result_contract_profile': data.get('result_contract_profile'),
                    'artifact': data['artifact'], 'host_receipt': data['host_receipt'],
                    'validation_error': str(error), 'mathematical_acceptance': False, 'retry_authorized': False})
                self.store.decide(failure, 'observed', {'reason': 'Explicit result/proposal contract failure; partial imports rolled back'})
                self.store.decide(result, 'quarantined', {'failure': failure})
                from .native_capture import NativeCapture
                envelope = json.loads(self.store.get(data['host_receipt'], 'artifact')['data']['text'])
                capture = envelope.get('producer_evidence', run['data']['dispatch_evidence'])
                substance = NativeCapture(self.c)._substance_concern(failure, data['task'], data['run'],
                    capture, data['artifact'], self.store.get(data['artifact'], 'artifact')['data']['text'],
                    selection='complete-result-text')
                response = {'result': result, 'observation': 'ingestion-quarantined', 'failure': failure,
                    'substance_finding': substance, 'registered': [], 'outcome': data['outcome'],
                    'mathematical_acceptance': False, 'retry_authorized': False}
                self.store.event('proposal-ingestion-failure', result, response)
                self.store.finish_request('ingest:' + result, fingerprint, response)
                return response

    def assess_ingestion_failure(self, identifier: str, assessment_artifact: str, followups: list[str],
                                 reopen_condition: str, *, expected: int, request_id: str) -> dict:
        failure = self.store.get(identifier, 'ingestion_failure')
        assessment = self.store.get(assessment_artifact, 'artifact')
        nonempty(assessment['data']['text'], 'assessment of retained invalid proposals')
        nonempty(reopen_condition, 'reopening condition')
        nonempty(request_id, 'request identity')
        if (not isinstance(followups, list) or any(not isinstance(f, str) or not f.strip() for f in followups)
                or len(set(followups)) != len(followups)):
            raise StateError('Quarantine followups must be exact distinct record IDs')
        key = 'assess-ingestion-failure:' + request_id
        fingerprint = digest({'failure': failure['hash'], 'assessment': assessment['hash'],
                              'followups': followups, 'reopen_condition': reopen_condition})
        with self.store.transaction():
            previous = self.store.request(key, fingerprint)
            if previous is not None:
                event = self.store.db.execute('SELECT payload FROM events WHERE seq=?',
                                             (previous['assessment_revision'],)).fetchone()
                return {**previous, 'current': self._native_failure_assessment_current(identifier, json.loads(event['payload']))}
            with self.store.transaction(expected):
                if not self.c._scope_current(assessment_artifact):
                    raise StateError('Assessment artifact scope is not current')
                if any(not self._failure_followup_scope(failure['data']['target'], f) for f in followups):
                    raise StateError('Quarantine followups need exact target scope')
                basis = self._native_failure_basis(identifier, assessment_artifact, followups)
                certificate = {'assessment_artifact': assessment_artifact, 'followups': followups,
                    'basis': basis, 'basis_hash': digest(basis), 'reopen_condition': reopen_condition,
                    'authority': 'Operational interpretation only; no substantive concern is dismissed',
                    'mathematical_acceptance': False, 'retry_authorized': False}
                revision = self.store.event('ingestion-failure-assessment', identifier, certificate)
                response = {'failure': identifier, 'assessment_revision': revision,
                            'mathematical_acceptance': False, 'retry_authorized': False}
                self.store.finish_request(key, fingerprint, response)
                return {**response, 'current': True}

    def _ingest(self, result: str) -> dict:
        record = self.store.get(result, 'result')
        data = record['data']
        run = self.store.get(data['run'], 'run')['data']
        packet = self.tasks.packet(data['task'])
        if self.store.status(data['run']) != 'completed' or self.store.status(result) == 'withdrawn':
            raise StateError('Only a current completed result may be imported')
        output = json.loads(self.store.get(data['artifact'], 'artifact')['data']['text'])
        key = 'ingest:' + result
        fingerprint = digest({'result': record['hash']})
        with self.store.transaction():
            prior = self.store.request(key, fingerprint)
            if prior is not None:
                return prior
            created = []
            if data['outcome'] == 'review':
                provenance = self.tasks.review_provenance(data['run'], data['target'], data['verdict'], data['artifact'], data['checks'])
                existing = [r for r in self.store.records('review') if r['data']['run_id'] == data['run']]
                if existing:
                    expected_review = {'target': data['target'], 'target_hash': data['target_hash'],
                        'run_id': data['run'], 'reviewer': run['conversation_id'], 'verdict': data['verdict'],
                        'artifact': data['artifact'], 'checks': data['checks']}
                    if len(existing) != 1 or any(existing[0]['data'].get(k) != v for k, v in expected_review.items()):
                        raise StateError('Captured review conflicts with this exact result')
                    created.append(existing[0]['id'])
                else:
                    created.append(self.c.review(data['target'], run['conversation_id'], data['run'],
                        data['verdict'], data['artifact'], data['checks'], exposure=provenance['exposure']))
            elif data['outcome'] == 'context-request':
                requests = output.get('requested_context')
                if not isinstance(requests, list) or not requests or any(not isinstance(x, str) or not x.strip() for x in requests):
                    raise ProposalContractError('Context request needs specific missing information')
                self.store.decide(result, 'context-needed', {'requested_context': requests})
            else:
                proposals = output.get('proposals', [])
                if not isinstance(proposals, list):
                    raise ProposalContractError('Proposals must be an array')
                if data['outcome'] == 'counterexample' and not any(
                        isinstance(p, dict) and p.get('kind') == 'counterexample' for p in proposals):
                    if not proposals and self.store.get(packet['target'])['kind'] == 'claim':
                        # The exact assigned claim is explicit. This remains an
                        # unvalidated self-contained proposal, never a disproof.
                        proposals = [{'local_id': 'reported-counterexample', 'kind': 'counterexample',
                                      'data': {'target': packet['target'], 'dependencies': []}}]
                    else:
                        raise ProposalContractError('Counterexample outcome needs an explicit exact-claim counterexample proposal; a method defect is not a theorem refutation')
                if (packet['claim'] is None or packet['records'].get(packet['target'], {}).get('kind') == 'adjudication') and proposals:
                    raise ProposalContractError('Subject adjudication/infrastructure review cannot register mathematical proposals')
                aliases = {}
                allowed = set(packet['records']) | {packet['target']}
                if packet['claim'] is not None:
                    allowed.add(packet['claim'])
                contract = self.store.get(packet['claim'], 'claim')['data']['contract'] if packet['claim'] else None
                reasoning = self.store.put('artifact', {'text': output['reasoning'], 'media_type': 'text/markdown',
                    'content_hash': digest(output['reasoning']), 'source_result': result})
                created.append(reasoning)

                def reference(value, kind=None):
                    if not isinstance(value, str) or not value.strip():
                        raise ProposalContractError('Proposal reference must be a nonempty identifier string')
                    if value in aliases:
                        identifier = aliases[value]
                    elif value in allowed:
                        identifier = value
                    else:
                        raise ProposalContractError('Proposal references information outside its packet; request context or register a new scoped discovery')
                    record = self.store.get(identifier)
                    if kind is not None and record['kind'] != kind:
                        raise ProposalContractError(f'Proposal reference requires {kind}, received {record["kind"]}')
                    return identifier

                for proposal in proposals:
                    if not isinstance(proposal, dict) or set(proposal) != {'local_id', 'kind', 'data'}:
                        raise ProposalContractError('Each proposal requires exactly local_id, kind and data')
                    local, kind, payload = proposal['local_id'], proposal['kind'], proposal['data']
                    if not isinstance(local, str) or not local.strip() or local in aliases or local in allowed or not isinstance(payload, dict):
                        raise ProposalContractError('Invalid or duplicate proposal alias')
                    fields = {
                        'claim': {'statement', 'definitions'},
                        'inference': {'conclusion', 'premises', 'assumptions', 'discharge', 'rule', 'applications'},
                        'counterexample': {'target', 'dependencies'},
                        'route': {'target', 'strategy', 'family'},
                        'obligation': {'route', 'statement', 'claim', 'relation', 'relation_artifact'},
                        'experiment': {'target', 'source_code', 'scope', 'inputs'},
                        'formal_plan': {'target', 'source_code', 'symbol', 'expected_type', 'assumptions', 'allowed_axioms', 'outcome'},
                    }
                    if not isinstance(kind, str) or kind not in fields or not set(payload).issubset(fields[kind]):
                        raise ProposalContractError('Worker proposal cannot assign status, author, assurance or unsupported operations')
                    required = {'claim': {'statement'}, 'inference': {'conclusion'}, 'counterexample': set(),
                                'route': {'strategy', 'family'}, 'obligation': {'route', 'statement'},
                                'experiment': {'source_code', 'scope'},
                                'formal_plan': {'source_code', 'symbol', 'expected_type'}}[kind]
                    if not required.issubset(payload):
                        raise ProposalContractError('Worker proposal is missing required fields')
                    for name in ('statement', 'strategy', 'family', 'source_code', 'scope', 'symbol', 'expected_type', 'rule', 'outcome', 'relation'):
                        if name in payload and (not isinstance(payload[name], str) or not payload[name].strip()):
                            raise ProposalContractError(f"Proposal field '{name}' must be nonempty text")
                    for field_name in ('definitions', 'premises', 'assumptions', 'discharge', 'applications', 'allowed_axioms', 'dependencies'):
                        if field_name in payload and not isinstance(payload[field_name], list):
                            raise ProposalContractError(f"Proposal field '{field_name}' must be an array")
                    if 'inputs' in payload and payload['inputs'] is not None and not isinstance(payload['inputs'], dict):
                        raise ProposalContractError("Proposal field 'inputs' must be an object or None")
                    if kind == 'claim':
                        identifier = self.c.claim(payload['statement'], contract,
                            definitions=[reference(x, 'definition') for x in payload.get('definitions', [])])
                    elif kind == 'inference':
                        identifier = self.c.inference(reference(payload['conclusion'], 'claim'),
                            [reference(x, 'claim') for x in payload.get('premises', [])], reasoning, run['conversation_id'],
                            assumptions=[reference(x, 'assumption') for x in payload.get('assumptions', [])],
                            discharge=[reference(x, 'assumption') for x in payload.get('discharge', [])],
                            rule=payload.get('rule', 'argument'),
                            applications=[reference(x, 'application') for x in payload.get('applications', [])])
                    elif kind == 'counterexample':
                        identifier = self.c.counterexample(reference(payload.get('target', packet['claim']), 'claim'), reasoning,
                            run['conversation_id'], dependencies=[reference(x, 'claim') for x in payload.get('dependencies', [])])
                    elif kind == 'route':
                        identifier = self.c.route(reference(payload.get('target', packet['claim']), 'claim'), payload['strategy'], family=payload['family'])
                    elif kind == 'obligation':
                        identifier = self.c.obligation(reference(payload['route'], 'route'), payload['statement'],
                            claim=reference(payload['claim'], 'claim') if payload.get('claim') else None,
                            relation=payload.get('relation', 'required-for-selected-route'),
                            relation_artifact=reference(payload['relation_artifact'], 'artifact')
                                if payload.get('relation_artifact') else reasoning)
                    else:
                        source_code = nonempty(payload['source_code'], 'source code')
                        code = self.store.put('artifact', {'text': source_code,
                            'media_type': 'text/x-python' if kind == 'experiment' else 'text/x-lean',
                            'content_hash': digest(source_code), 'source_result': result})
                        created.append(code)
                        evidence = Evidence(self.c)
                        target = reference(payload.get('target', packet['claim']), 'claim')
                        if kind == 'experiment':
                            identifier = evidence.experiment(target, code, payload['scope'],
                                author=run['conversation_id'], inputs=payload.get('inputs'))
                        else:
                            identifier = evidence.formal_plan(target, code, payload['symbol'], payload['expected_type'],
                                author=run['conversation_id'], assumptions=[reference(x, 'assumption') for x in payload.get('assumptions', [])],
                                allowed_axioms=payload.get('allowed_axioms'), outcome=payload.get('outcome', 'proof'))
                    aliases[local] = identifier
                    created.append(identifier)
                self.store.event('proposal-import', result, {'created': created, 'aliases': aliases})
            if data['outcome'] != 'context-request':
                self.store.decide(result, 'imported', {'records': created, 'outcome': data['outcome']})
            response = {'result': result, 'registered': created, 'outcome': data['outcome'],
                        'mathematical_acceptance': False}
            self.store.finish_request(key, fingerprint, response)
            return response

    def resolve_context(self, result: str, added: list[str], reason: str, *, becomes_informed: bool = False) -> str:
        if not isinstance(added, list) or not added or any(not isinstance(a, str) or not a.strip() for a in added):
            raise StateError("added must be a nonempty list of record IDs")
        if type(becomes_informed) is not bool:
            raise StateError("becomes_informed must be an exact boolean")
        data = self.store.get(result, 'result')['data']
        with self.store.transaction():
            if self.store.status(result) != 'context-needed':
                raise StateError('Result has no unresolved context request')
            new_task = self.tasks.extend(data['task'], added, reason, becomes_informed=becomes_informed)
            self.store.decide(result, 'context-resolved', {'new_task': new_task, 'reason': reason})
            return new_task

    def checkpoint(self, reason: str) -> str:
        if not isinstance(reason, str) or not reason.strip():
            raise StateError('Checkpoint requires an epistemic/operational reason')
        with self.store.transaction():
            base_revision = self.store.revision
            previous = self.store.db.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            event_head = previous["hash"] if previous else ZERO_HASH
            snapshot = self.store.export()
            identifier = self.store.put('checkpoint', {
                'reason': reason,
                'base_revision': base_revision,
                'event_head': event_head,
                'snapshot_hash': digest(snapshot),
                'pending': self.next_actions(),
            })
            return identifier

    def resolve_semantic_context(self, result: str, capsule: str, selectors: list[str], reason: str,
                                 *, max_chars: int = 128000, include_theorem_proofs: bool = False) -> str:
        data = self.store.get(result, 'result')['data']
        with self.store.transaction():
            if self.store.status(result) != 'context-needed':
                raise StateError('Result has no unresolved context request')
            new_task = self.tasks.expand_semantics(data['task'], capsule, selectors, reason, max_chars=max_chars,
                                                   include_theorem_proofs=include_theorem_proofs)
            self.store.decide(result, 'context-resolved', {'new_task': new_task,
                'capsule': capsule, 'reason': reason, 'exposure_change': False})
            return new_task

    def checkpoint_snapshot(self, identifier: str) -> dict:
        record = self.store.get(identifier, 'checkpoint')
        data = record['data']
        if 'snapshot' in data:
            if 'snapshot_hash' not in data:
                raise StateError(f"Legacy checkpoint lacks snapshot hash: {identifier}")
            snapshot = data['snapshot']
            if digest(snapshot) != data['snapshot_hash']:
                raise StateError(f"Checkpoint snapshot hash mismatch for {identifier}")
            return snapshot
        if all(key in data for key in ('base_revision', 'snapshot_hash', 'event_head')):
            snapshot = self.store.export_at(data['base_revision'])
            if digest(snapshot) != data['snapshot_hash']:
                raise StateError(f"Checkpoint snapshot hash mismatch for {identifier}")
            reconstructed_head = snapshot['events'][-1]['hash'] if snapshot['events'] else ZERO_HASH
            if reconstructed_head != data['event_head']:
                raise StateError(f"Checkpoint event head mismatch for {identifier}")
            return snapshot
        raise StateError(f"Unsupported checkpoint format in {identifier}")

    def next_actions(self) -> dict:
        with self.store.transaction():
            return self._next_actions()

    def _next_actions(self) -> dict:
        progress = self.c.progress()
        actions = []
        from .curation import Curation
        for candidate in self.store.records('learning_candidate'):
            if self.store.status(candidate['id']) == 'proposed':
                actions.append({'action': 'curate-or-decline-local-learning' if Curation(self.c).candidate_current(candidate['id'])
                    else 'reextract-or-decline-stale-learning', 'target': candidate['id'], 'automatic_acceptance': False})
        for learning in self.store.records('learning'):
            if (learning['data'].get('target') and self.c.learning_current(learning['id'])
                    and not any(a['data']['learning'] == learning['id'] and Curation(self.c).admission_current(a['id'])
                                for a in self.store.records('learning_admission'))):
                actions.append({'action': 'admit-target-local-learning', 'target': learning['data']['target'],
                    'learning': learning['id'], 'automatic_acceptance': False})
        from .advisory import Advisory
        for route in self.store.records('route'):
            condition = Advisory(self.c).condition(route['id'])
            if not condition['current']:
                actions.append({'action': 'reclassify-route-decision' if condition['needs_reclassification']
                    else 'reassess-route-decision', 'target': route['id'], 'condition': condition,
                    'automatic_acceptance': False})
        for request in self.store.records('completion_request'):
            if self.store.status(request['id']) in {'draft', 'active'}:
                from .completion import Completion
                condition = Completion(self.c)._fidelity(request['id'], {'completion-mapping', 'criteria-coverage'})
                if not condition['current']:
                    actions.append({'action': 'review-completion-mapping', 'target': request['id'],
                        'role': 'fidelity-auditor', 'checks': ['completion-mapping', 'criteria-coverage']})
                elif self.store.status(request['id']) == 'draft':
                    actions.append({'action': 'activate-exact-completion-request', 'target': request['id'],
                                    'automatic_acceptance': False})
        for claim in progress['claims']:
            if claim['state'] == 'refuted':
                continue  # Same-orientation reports do not obstruct a disproof.
            for report in claim.get('pending_counterexample_reports', []):
                if not any(a.get('report') == report for a in actions):
                    actions.append({'action': 'adjudicate-counterexample-report', 'report': report,
                        'target': claim['id'], 'role': 'adjudicator', 'independence': 'informed',
                        'automatic_acceptance': False})
        for failure in self.store.records('ingestion_failure'):
            prior = self.store.db.execute("SELECT payload FROM events WHERE type='ingestion-failure-assessment' "
                                         'AND target=? ORDER BY seq DESC LIMIT 1', (failure['id'],)).fetchone()
            if prior is None or not self._native_failure_assessment_current(failure['id'], json.loads(prior['payload'])):
                actions.append({'action': 'assess-ingestion-failure', 'failure': failure['id'],
                    'result': failure['data']['result'], 'task': failure['data']['task'],
                    'automatic_acceptance': False, 'retry_authorized': False})
        for conflict in self.store.records('native_conflict'):
            if self.c.finding_blocking(conflict['data']['finding']):
                actions.append({'action': 'investigate-native-terminal-conflict', 'conflict': conflict['id'],
                    'finding': conflict['data']['finding'], 'run': conflict['data']['previous_run'],
                    'task': conflict['data']['task'], 'retry_authorized': False,
                    'automatic_acceptance': False})
        for failure in self.store.records('native_failure'):
            prior = self.store.db.execute("SELECT payload FROM events WHERE type='native-failure-assessment' "
                                         'AND target=? ORDER BY seq DESC LIMIT 1', (failure['id'],)).fetchone()
            if prior is None or not self._native_failure_assessment_current(failure['id'], json.loads(prior['payload'])):
                actions.append({'action': 'assess-native-protocol-failure', 'failure': failure['id'],
                    'task': failure['data']['task'], 'run': failure['data']['run'],
                    'response_artifact': failure['data']['response_artifact'],
                    'negative_evidence_disposition': 'unassessed or changed; inspect retained substance',
                    'automatic_acceptance': False, 'retry_authorized': False})
        # A live process/host status is needed before deciding a running task has
        # stopped. The ledger alone authorizes inspection, never an automatic retry.
        for run in self.store.records('run'):
            terminated = any(r['data']['run'] == run['id'] for kind in ('result', 'native_failure')
                             for r in self.store.records(kind))
            if not terminated:
                actions.append({'action': 'inspect-live-run', 'run': run['id'],
                                'conversation_id': run['data']['conversation_id'], 'retry_without_observation': False})
        executed_plans = {e['data']['plan'] for e in self.store.records('execution')}
        executed_plans |= {r['data']['plan'] for kind in ('experiment', 'formal_receipt')
                           for r in self.store.records(kind) if r['data'].get('plan')}
        for execution in self.store.records('execution'):
            status = self.store.status(execution['id'])
            from .execution import Executions
            terminal = Executions(self.c)._terminal_response(execution['id'])
            if terminal is None:
                actions.append({'action': 'inspect-execution', 'execution': execution['id'],
                                'plan': execution['data']['plan'], 'retry_without_observation': False})
            assessed = self.store.db.execute("SELECT 1 FROM events WHERE type='execution-assessment' AND target=?",
                                            (execution['id'],)).fetchone()
            if terminal is not None and status != 'withdrawn':
                receipt = terminal['receipt']
                item = {'execution': execution['id'], 'receipt': receipt,
                        'plan': execution['data']['plan'], 'automatic_rerun': False,
                        'automatic_acceptance': False}
                failed_boundary = receipt is None or self.store.get(receipt)['data'].get('evidence_class') == 'execution-failure'
                formal = execution['data']['operation'] != 'compute'
                receipt_status = self.store.status(receipt) if receipt else None
                # An operational disposition closes assessment only. It cannot
                # dispose of missing qualification or damaged formal provenance.
                if formal and not failed_boundary and receipt_status == 'checked':
                    condition = self.c._formal_condition(receipt)
                    if not condition['current']:
                        if any(i['category'] != 'qualification' for i in condition['issues']):
                            actions.append({'action': 'repair-formal-evidence', 'condition': condition, **item})
                        else:
                            for issue in condition['issues']:
                                action = 'review-formal-receipt' if issue['target'] == receipt else 'review-formal-plan'
                                actions.append({'action': action, 'target': issue['target'],
                                                'missing': issue['missing'], **item})
                    else:
                        references = self.c._formal_references(receipt)
                        if not any(r['use'] != 'unusable' for r in references):
                            prior = self.store.db.execute("SELECT payload FROM events WHERE type='formal-evidence-disposition' "
                                'AND target=? ORDER BY seq DESC LIMIT 1', (receipt,)).fetchone()
                            disposition = json.loads(prior['payload']) if prior else None
                            deferred = disposition is not None and self.c._formal_disposition_current(receipt, disposition)
                            if not deferred:
                                actions.append({'action': 'consider-formal-evidence', 'references': references,
                                                'choices': ['register-exact-mathematical-route', 'explicitly-defer'], **item})
                if not assessed:
                    action = ('assess-execution-failure' if failed_boundary else
                              'assess-computation' if not formal else
                              'assess-formal-failure' if receipt_status == 'failed' else 'assess-formal-evidence')
                    actions.append({'action': action, **item})
        for result in self.store.records('result'):
            status = self.store.status(result['id'])
            if status == 'proposed':
                actions.append({'action': 'ingest-result', 'result': result['id']})
            elif status == 'context-needed':
                actions.append({'action': 'supply-context', 'result': result['id']})
            elif status == 'imported' and result['data']['outcome'] != 'review':
                actions.append({'action': 'assess-research-result', 'result': result['id'],
                                'outcome': result['data']['outcome'], 'automatic_acceptance': False})
        for kind, action in [('inference', 'evaluate-inference-for-promotion'),
                             ('counterexample', 'evaluate-counterexample'),
                             ('application', 'evaluate-theorem-application'),
                             ('formal_plan', 'inspect-formal-plan'), ('experiment', 'inspect-experiment-plan')]:
            for record in self.store.records(kind):
                if self.store.status(record['id']) == 'proposed':
                    if kind in {'formal_plan', 'experiment'} and record['id'] in executed_plans:
                        continue
                    actions.append({'action': action, 'target': record['id'], 'automatic_acceptance': False})
        if progress['next']['action'] in {'adjudicate', 'investigate-conflict', 'investigate-refutation-cycle',
                                       'repair-validated-findings', 'investigate-disputed-claims'}:
            actions.insert(0, progress['next'])
        if progress['open_obligations']:
            actions.append({'action': 'research-obligations', 'targets': progress['open_obligations']})
        for task in self.store.records('task'):
            if self.store.status(task['id']) == 'ready':
                actions.append({'action': 'dispatch', 'task': task['id'], 'role': task['data']['packet']['role']})
            elif any(task['id'] in d['data']['tasks'] for d in self.store.records('dispatch')) and not any(
                    r['data']['task'] == task['id'] for r in self.store.records('run')):
                requests = [r for r in self.store.records('dispatch') if task['id'] in r['data']['tasks']]
                actions.append({'action': 'inspect-native-allocation', 'task': task['id'],
                                'dispatch': requests[0]['id'] if len(requests) == 1 else None,
                                'parent': requests[0]['data']['parent'] if len(requests) == 1 else None,
                                'retry_without_observation': False})
        for release in progress['releases']:
            if not release['current'] and release['status'] == 'released':
                actions.append({'action': 'repair-or-withdraw-release', 'release': release['id']})
        for candidate in progress['release_ready']:
            actions.append({'action': 'release-candidate', 'candidate': candidate, 'automatic_release': False})
        for candidate in self.store.records('candidate'):
            if (self.store.status(candidate['id']) not in {'withdrawn', 'rejected'}
                    and not self.c.candidate_current(candidate['id'])):
                actions.append({'action': 'revise-candidate', 'candidate': candidate['id'], 'reuse_old_audit': False})
            elif self.store.status(candidate['id']) == 'audited' and not self.c.candidate_audit_current(candidate['id']):
                actions.append({'action': 'reaudit-candidate', 'candidate': candidate['id'],
                                'reuse_retracted_witnesses': False})
            elif self.store.status(candidate['id']) == 'frozen':
                actions.append({'action': 'audit', 'targets': [candidate['id']]})
        for review in self.store.records('review'):
            if (review['data']['verdict'] == 'fail' and self.c.finding_blocking(review['id'])
                    and not self.c.finding_effects(review['id'])['substantive_current']):
                actions.insert(0, {'action': 'adjudicate-review', 'review': review['id']})
        for case in self.store.records('adjudication'):
            if self.store.status(case['id']) == 'proposed':
                checks = self.c._adjudication_checks(case['data'])
                current = self.c._adjudication_current(case['id'])
                ready = False
                if current:
                    try:
                        self.c._reviews(case['id'], checks)
                        ready = True
                    except StateError:
                        pass
                actions.append({'action': ('adjudicate-case' if ready else 'review-adjudication-case'
                                          if current else 'revise-adjudication-case'),
                                'case': case['id'], 'checks': sorted(checks),
                                'role': 'adjudicator', 'independence': 'informed', 'automatic_acceptance': False})
        if not actions:
            actions.append(progress['next'])
        if progress['mathematics_sufficient']:
            required_delivery = {r['selected']['candidate'] for request in progress['completion_requests']
                for r in request['requirements'] if r['selected'] and not r['delivery_fulfilled']}
            for action in actions:
                action['optional_research'] = action['action'] not in {
                    'inspect-live-run', 'inspect-execution', 'inspect-native-allocation',
                    'investigate-native-terminal-conflict', 'repair-or-withdraw-release',
                    'assess-native-failure', 'assess-ingestion-failure'}
                if action['action'] == 'release-candidate' and action.get('candidate') in required_delivery:
                    action['optional_research'] = False
            if progress['next'] not in actions:
                actions.insert(0, progress['next'])
        return {'revision': self.store.revision, 'actions': actions,
                'solved': progress['contract_fulfilled'], 'contract_fulfilled': progress['contract_fulfilled'],
                'mathematics_sufficient': progress['mathematics_sufficient'],
                'completion_bound': progress['completion_bound'], 'research_exhaustion': 'not-claimed',
                'note': 'Requested fulfillment is scoped to exact qualified requests; task completion and research exhaustion are separate.'}
