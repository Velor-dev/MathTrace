"""Exact requested fulfillment; neither universal truth nor research exhaustion."""
from __future__ import annotations

from .context import Tasks
from .formal import PROFILE
from .research import nonempty
from .store import StateError, digest

COMPLETION_PROFILE = 'exact-requested-fulfillment-v1'
ASSURANCE = {'audited-informal': 0, 'machine-checked': 1}
EVIDENCE_KINDS = {'artifact', 'claim', 'definition', 'external_theorem', 'application',
                  'experiment', 'formal_receipt', 'execution'}


class Completion:
    def __init__(self, campaign):
        self.c, self.store = campaign, campaign.store

    def _request_data(self, identifier):
        record = self.store.get(identifier, 'completion_request')
        d = record['data']
        contract = self.store.get(d['contract'], 'contract')
        if (d.get('profile') != COMPLETION_PROFILE or d.get('contract_hash') != contract['hash']
                or d.get('criterion') != contract['data']['completion']
                or d.get('supported_machine_profile') != PROFILE
                or not isinstance(d.get('outputs'), list) or not d['outputs']):
            raise StateError('Completion request lacks its exact supported contract/output binding')
        seen = set()
        for o in d['outputs']:
            if (not isinstance(o, dict) or set(o) != {'target', 'outcomes', 'assurance', 'delivery', 'duties'}
                    or not isinstance(o['target'], str) or o['target'] in seen
                    or self.store.get(o['target'], 'claim')['data']['contract'] != d['contract']
                    or not isinstance(o['outcomes'], list) or not o['outcomes']
                    or any(not isinstance(v, str) or v not in {'proof', 'disproof'} for v in o['outcomes'])
                    or len(set(o['outcomes'])) != len(o['outcomes'])
                    or ('disproof' in o['outcomes'] and not contract['data']['allow_disproof'])
                    or not isinstance(o['assurance'], str) or o['assurance'] not in ASSURANCE
                    or not isinstance(o['delivery'], str) or o['delivery'] not in {'audited-result', 'released-result'}
                    or not isinstance(o['duties'], list) or any(not isinstance(v, str) or not v.strip() for v in o['duties'])
                    or len(set(o['duties'])) != len(o['duties'])):
                raise StateError('Completion request contains an invalid exact output')
            seen.add(o['target'])
        self.store.get(d['mapping_artifact'], 'artifact')
        if d.get('previous') is not None and self.store.get(d['previous'], 'completion_request')['data']['contract'] != d['contract']:
            raise StateError('Completion revision must preserve the exact original contract')
        return d

    def request(self, contract, outputs, mapping_artifact, *, author, previous=None):
        original = self.store.get(contract, 'contract')
        self.store.get(mapping_artifact, 'artifact')
        nonempty(author, 'request author')
        if not isinstance(outputs, list) or not outputs:
            raise StateError('Completion needs a nonempty AND list of exact required outputs')
        required = {'target', 'outcomes', 'assurance', 'delivery', 'duties'}
        copied, targets = [], set()
        for output in outputs:
            if not isinstance(output, dict) or set(output) != required:
                raise StateError('Each output must declare exactly target/outcomes/assurance/delivery/duties')
            target = self.store.get(output['target'], 'claim')
            if target['data']['contract'] != contract or target['id'] in targets:
                raise StateError('Required outputs must be distinct exact claims of the original contract')
            outcomes, duties = output['outcomes'], output['duties']
            if (not isinstance(outcomes, list) or not outcomes
                    or any(not isinstance(o, str) or o not in {'proof', 'disproof'} for o in outcomes)
                    or len(set(outcomes)) != len(outcomes)):
                raise StateError('Each output needs explicit acceptable proof/disproof outcomes')
            if 'disproof' in outcomes and not original['data']['allow_disproof']:
                raise StateError('Completion cannot enlarge the contract permitted outcomes')
            if (not isinstance(output['assurance'], str) or output['assurance'] not in ASSURANCE
                    or not isinstance(output['delivery'], str) or output['delivery'] not in {'audited-result', 'released-result'}):
                raise StateError('Unknown requested assurance or delivery boundary')
            if (not isinstance(duties, list) or any(not isinstance(d, str) or not d.strip() for d in duties)
                    or len(set(duties)) != len(duties)):
                raise StateError('Additional criterion duties must be exact distinct nonempty strings')
            copied.append({**output, 'outcomes': list(outcomes), 'duties': list(duties)})
            targets.add(target['id'])
        if previous is not None:
            if self.store.get(previous, 'completion_request')['data']['contract'] != contract:
                raise StateError('Completion revision must preserve the exact original contract')
        with self.store.transaction():
            identifier = self.store.put('completion_request', {'profile': COMPLETION_PROFILE,
                'contract': contract, 'contract_hash': original['hash'], 'outputs': copied,
                'mapping_artifact': mapping_artifact, 'author': author, 'previous': previous,
                'criterion': original['data']['completion'],
                'supported_machine_profile': PROFILE,
                'machine_limits': 'Same-kernel compiled-target checking; source correspondence and independent-kernel assurance are not supplied by this label',
                'mapping_duty': 'Check the entire original completion criterion against all outputs/policies/duties without assuming any result exists. Reject omitted or unsupported criteria; do not infer fulfillment from the existence of a weaker result.'})
            self.store.decide(identifier, 'draft', {'reason': 'Exact request retained; criterion mapping still needs independent qualification'})
            return identifier

    def _fidelity(self, target, checks, witnesses=None):
        condition = self.c._review_condition(target, checks, witnesses=witnesses)
        covered, reviews = set(), []
        for review in condition['reviews']:
            data = self.store.get(review, 'review')['data']
            packet = self.store.get(data['provenance']['task'], 'task')['data']['packet']
            if packet['role'] == 'fidelity-auditor':
                reviews.append(review)
                covered.update(data['checks'])
        current = condition['current'] and checks.issubset(covered)
        if witnesses is not None:
            current = current and set(reviews) == set(witnesses)
        return {'current': current, 'reviews': reviews, 'missing': sorted(checks - covered),
                'reason': condition['reason'] if not condition['current'] else
                    None if current else 'Exact completion fidelity responsibility is incomplete'}

    def activate(self, identifier, *, expected, reason, supersedes=None):
        request = self.store.get(identifier, 'completion_request')
        self._request_data(identifier)
        nonempty(reason, 'explicit requested-scope activation/revision reason')
        with self.store.transaction(expected):
            if self.store.status(identifier) != 'draft' or not self.c._scope_current(identifier):
                raise StateError('Completion activation needs a current draft request')
            if not self._fidelity(identifier, {'completion-mapping', 'criteria-coverage'})['current']:
                raise StateError('Completion mapping must independently cover the full original criterion')
            previous = request['data']['previous']
            if previous != supersedes:
                raise StateError('A request revision must explicitly name its declared predecessor')
            if any(r['data']['contract'] == request['data']['contract'] and self.store.status(r['id']) == 'active'
                   and r['id'] != previous for r in self.store.records('completion_request')):
                raise StateError('Another request for this contract is active; an alias cannot silently replace it')
            if previous:
                if self.store.status(previous) != 'active':
                    raise StateError('Request revision must name the currently active predecessor')
                self.store.decide(previous, 'superseded', {'request': identifier, 'reason': reason})
            self.store.decide(identifier, 'active', {'reason': reason, 'supersedes': supersedes})
            return {'request': identifier, 'mathematical_acceptance': False}

    def evidence(self, request, output_index, candidate, artifact, *, author, additional_evidence=None):
        d = self._request_data(request)
        if type(output_index) is not int or not 0 <= output_index < len(d['outputs']):
            raise StateError('Completion evidence must name an exact output index')
        frozen = self.store.get(candidate, 'candidate')
        output = d['outputs'][output_index]
        if frozen['data']['target'] != output['target'] or not output['duties']:
            raise StateError('Candidate-specific completion evidence needs this exact target and additional duties')
        self.store.get(artifact, 'artifact')
        additional = [] if additional_evidence is None else additional_evidence
        if not isinstance(additional, list) or any(not isinstance(r, str) or not r.strip() for r in additional):
            raise StateError('Additional completion evidence must be exact mathematical evidence IDs')
        for r in additional:
            if self.store.get(r)['kind'] not in EVIDENCE_KINDS:
                raise StateError('Verdicts/history cannot silently become completion-duty evidence')
        with self.store.transaction():
            return self.store.put('completion_evidence', {'profile': COMPLETION_PROFILE,
                'request': request, 'request_hash': self.store.get(request)['hash'],
                'target': output['target'], 'output_index': output_index,
                'candidate': candidate, 'candidate_hash': frozen['hash'],
                'manifest_hash': frozen['data']['manifest_hash'], 'duties': output['duties'],
                'artifact': artifact, 'additional_evidence': list(dict.fromkeys(additional)),
                'author': nonempty(author, 'completion evidence author'),
                'checks': sorted({'completion-duties'} | ({'formal-environment'}
                    if frozen['data']['assurance'] == 'machine-checked' else set())),
                'authority': 'Exact candidate-specific criterion evidence, not a replacement proof/audit'})

    def _duty_options(self, request, index, candidate):
        output = self._request_data(request)['outputs'][index]
        if not output['duties']:
            return [{'evidence': None, 'evidence_hash': None, 'reviews': []}]
        result = []
        for record in self.store.records('completion_evidence'):
            d = record['data']
            if d.get('request') != request or d.get('output_index') != index or d.get('candidate') != candidate:
                continue
            try:
                self._evidence_data(record['id'])
            except (StateError, KeyError, TypeError, ValueError):
                continue
            if not self.c._scope_current(record['id']):
                continue
            condition = self._fidelity(record['id'], set(d['checks']))
            if condition['current']:
                result.append({'evidence': record['id'], 'evidence_hash': record['hash'], 'reviews': condition['reviews']})
        return result

    def _evidence_data(self, identifier):
        d = self.store.get(identifier, 'completion_evidence')['data']
        request = self.store.get(d['request'], 'completion_request')
        outputs = self._request_data(request['id'])['outputs']
        index = d['output_index']
        if type(index) is not int or not 0 <= index < len(outputs):
            raise StateError('Completion duty evidence lacks an exact output index')
        output = outputs[index]
        frozen = self.store.get(d['candidate'], 'candidate')
        checks = sorted({'completion-duties'} | ({'formal-environment'}
            if frozen['data']['assurance'] == 'machine-checked' else set()))
        if (d.get('profile') != COMPLETION_PROFILE or d['request_hash'] != request['hash']
                or d['candidate_hash'] != frozen['hash'] or d['manifest_hash'] != frozen['data']['manifest_hash']
                or d['target'] != output['target'] or frozen['data']['target'] != output['target']
                or not output['duties'] or d['duties'] != output['duties'] or d['checks'] != checks
                or not isinstance(d['additional_evidence'], list)
                or any(not isinstance(r, str) or not r.strip() for r in d['additional_evidence'])
                or len(set(d['additional_evidence'])) != len(d['additional_evidence'])):
            raise StateError('Completion duty evidence lacks its exact candidate/criterion/check binding')
        self.store.get(d['artifact'], 'artifact')
        for r in d['additional_evidence']:
            if self.store.get(r)['kind'] not in EVIDENCE_KINDS:
                raise StateError('Completion duty evidence contains unsupported record kinds')
        return d

    def _options(self, request, index):
        output = self._request_data(request)['outputs'][index]
        result = []
        for frozen in self.store.records('candidate'):
            d = frozen['data']
            if (d['target'] != output['target'] or d['outcome'] not in output['outcomes']
                    or ASSURANCE.get(d['assurance'], -1) < ASSURANCE[output['assurance']]
                    or not self.c.candidate_audit_current(frozen['id'])):
                continue
            publications = [r['id'] for r in self.store.records('release') if r['data']['candidate'] == frozen['id']
                            and self.c.release_current(r['id'])]
            for duties in self._duty_options(request, index, frozen['id']):
                result.append({'candidate': frozen['id'], 'candidate_hash': frozen['hash'],
                    'manifest_hash': d['manifest_hash'], 'audit_reviews': self.c._audit_reviews(frozen['id']),
                    'assurance': d['assurance'], 'outcome': d['outcome'], **duties,
                    'publication': publications[-1] if publications and output['delivery'] == 'released-result' else None,
                    'delivery_current': output['delivery'] == 'audited-result' or bool(publications)})
        return result

    def fulfillment(self, identifier):
        with self.store.transaction():
            request = self.store.get(identifier, 'completion_request')
            self._request_data(identifier)
            active = self.store.status(identifier) == 'active'
            mapping = self._fidelity(identifier, {'completion-mapping', 'criteria-coverage'})
            mapping['current'] = mapping['current'] and self.c._scope_current(identifier)
            requirements = []
            for i, output in enumerate(request['data']['outputs']):
                options = self._options(identifier, i) if active and mapping['current'] else []
                selected = next((o for o in options if o['delivery_current']), options[0] if options else None)
                requirements.append({'index': i, **output, 'mathematics_sufficient': bool(options),
                    'delivery_fulfilled': bool(selected and selected['delivery_current']), 'selected': selected,
                    'alternative_current_candidates': list(dict.fromkeys(o['candidate'] for o in options))})
            math = active and mapping['current'] and all(r['mathematics_sufficient'] for r in requirements)
            fulfilled = math and all(r['delivery_fulfilled'] for r in requirements)
            targets = {o['target'] for o in request['data']['outputs']}
            owned_tasks = {r['data']['task'] for r in self.store.records('work_intent') if r['data']['target'] in targets}
            maintenance = []
            tasks = Tasks(self.c)
            for run in self.store.records('run'):
                if run['data']['task'] not in owned_tasks and tasks._claim_for(run['id']) not in targets:
                    continue
                terminal = any(r['data']['run'] == run['id'] for r in self.store.records('native_failure'))
                if not terminal:
                    import json
                    row = self.store.db.execute("SELECT payload FROM events WHERE type='completion-qualification' AND target=?",
                                                (run['id'],)).fetchone()
                    completed = json.loads(row['payload']) if row else None
                    terminal = bool(completed and completed.get('captured') is True and any(
                        r['id'] == completed.get('result') and r['data']['run'] == run['id'] for r in self.store.records('result')))
                if not terminal:
                    maintenance.append({'action': 'inspect-existing-run', 'run': run['id'], 'retry_authorized': False})
            for dispatch in self.store.records('dispatch'):
                unresolved = [t for t in dispatch['data']['tasks'] if (t in owned_tasks or tasks._claim_for(t) in targets)
                    and not any(r['data']['task'] == t for r in self.store.records('run'))]
                if unresolved:
                    maintenance.append({'action': 'inspect-native-allocation', 'dispatch': dispatch['id'],
                                        'tasks': unresolved, 'retry_authorized': False})
            return {'profile': COMPLETION_PROFILE, 'request': identifier, 'request_hash': request['hash'],
                'revision': self.store.revision, 'status': self.store.status(identifier),
                'mapping': mapping, 'requirements': requirements,
                'mathematics_sufficient': math, 'contract_fulfilled': fulfilled,
                'autonomous_exploration_required': not math, 'research_exhaustion': 'not-claimed',
                'maintenance': maintenance,
                'next': 'stop required exploration; deliver/collect existing work' if math else
                    'qualify completion mapping' if not mapping['current'] else 'complete required outputs',
                'authority': 'Current requested assurance/delivery under recorded evidence; not universal truth or absence of future challenges'}

    def record_fulfillment(self, identifier, *, expected, request_id):
        nonempty(request_id, 'fulfillment request identity')
        request = self.store.get(identifier, 'completion_request')
        fingerprint = digest({'request': request['hash']})
        with self.store.transaction():
            old = self.store.request('fulfillment:' + request_id, fingerprint)
            if old is not None:
                return {**old, 'current': self.certificate_current(old['certificate'])}
            with self.store.transaction(expected):
                state = self.fulfillment(identifier)
                if not state['contract_fulfilled']:
                    raise StateError('The exact requested contract is not currently fulfilled')
                certificate = self.store.put('fulfillment_certificate', {'profile': COMPLETION_PROFILE,
                    'request': identifier, 'request_hash': request['hash'], 'mapping_reviews': state['mapping']['reviews'],
                    'selected': [r['selected'] for r in state['requirements']],
                    'research_exhaustion': 'not-claimed'})
                self.store.decide(certificate, 'observed', {'reason': 'Exact current fulfillment witness; no silent candidate substitution'})
                reply = {'request': identifier, 'certificate': certificate}
                self.store.finish_request('fulfillment:' + request_id, fingerprint, reply)
                return {**reply, 'current': True}

    def certificate_current(self, identifier):
        try:
            return self._certificate_current(identifier)
        except (StateError, KeyError, TypeError, ValueError):
            return False

    def _certificate_current(self, identifier):
        with self.store.transaction():
            record = self.store.get(identifier, 'fulfillment_certificate')
            d = record['data']
            request = self.store.get(d['request'], 'completion_request')
            self._request_data(request['id'])
            if (d.get('profile') != COMPLETION_PROFILE or self.store.status(identifier) in {'withdrawn', 'rejected'} or self.c._blocked(identifier)
                    or self.store.status(request['id']) != 'active' or d['request_hash'] != request['hash']
                    or not self.c._scope_current(request['id']) or not self._fidelity(request['id'],
                        {'completion-mapping', 'criteria-coverage'}, d['mapping_reviews'])['current']
                    or len(d['selected']) != len(request['data']['outputs'])):
                return False
            for index, selected in enumerate(d['selected']):
                if selected.get('delivery_current') is not True:
                    return False
                output = request['data']['outputs'][index]
                frozen = self.store.get(selected['candidate'], 'candidate')
                value = frozen['data']
                if (frozen['hash'] != selected['candidate_hash'] or value['manifest_hash'] != selected['manifest_hash']
                        or value['target'] != output['target'] or value['outcome'] not in output['outcomes']
                        or value['outcome'] != selected['outcome'] or value['assurance'] != selected['assurance']
                        or ASSURANCE[value['assurance']] < ASSURANCE[output['assurance']]
                        or self.store.status(frozen['id']) != 'audited' or not self.c.candidate_current(frozen['id'])):
                    return False
                self.c._candidate_reviews(frozen['id'], witnesses=selected['audit_reviews'])
                if output['duties']:
                    evidence = self.store.get(selected['evidence'], 'completion_evidence')
                    e = self._evidence_data(evidence['id'])
                    if (evidence['hash'] != selected['evidence_hash'] or e['request'] != request['id']
                            or e['request_hash'] != request['hash'] or e['output_index'] != index
                            or e['candidate'] != frozen['id'] or e['candidate_hash'] != frozen['hash']
                            or e['manifest_hash'] != value['manifest_hash'] or e['duties'] != output['duties']
                            or not self.c._scope_current(evidence['id'])
                            or not self._fidelity(evidence['id'], set(e['checks']), selected['reviews'])['current']):
                        return False
                elif any(selected[k] for k in ('evidence', 'evidence_hash', 'reviews')):
                    return False
                if output['delivery'] == 'released-result':
                    publication = self.store.get(selected['publication'], 'release')
                    if publication['data']['candidate'] != frozen['id'] or not self.c.release_current(publication['id']):
                        return False
                elif selected['publication'] is not None:
                    return False
            return True
