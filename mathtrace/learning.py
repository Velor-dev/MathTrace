"""Advisory source-condition snapshots, never mathematical acceptance state."""

import json
from .store import StateError
from .evaluation import Evaluation
from .context import Tasks

BASIS_VERSION = 'typed-advisory-basis-v2'


def source_basis(campaign, identifier):
    """Capture the relevant conditions, not merely one eligibility Boolean.

    A failed source can describe a useful failure. Its *unchanged* condition is
    the criterion. Selected candidate dependencies stay exact; unrelated event
    revisions and interchangeable ordinary qualification witnesses are omitted.
    The flat map shares dependencies and is only a historical observation.
    """
    store, conditions = campaign.store, {}

    def qualification(target, checks, witnesses=None):
        result = campaign._review_condition(target, checks, witnesses=witnesses)
        # Ordinary review replacement is allowed by the mathematical policy.
        # Exact candidate/publication witness loss is included in lost_witnesses.
        return {k: v for k, v in result.items() if k != 'reviews'}

    def candidate_qualification(target, witnesses=None):
        return {k: v for k, v in campaign._candidate_review_condition(target, witnesses=witnesses).items()
                if k != 'reviews'}

    def claim_state(target, assumptions=None, policy='audited-informal', inference=None):
        state = campaign.claim_state(target, assumptions, policy=policy)
        # A claim-state lesson does not select every alternative proof. Exact
        # argument lessons cite an inference/candidate; unrelated positive OR
        # alternatives must not invalidate those selected-witness observations.
        result = {k: v for k, v in state.items()
                  if k not in {'revision', 'supports', 'grounded_supports', 'usable_supports'}}
        result['grounded'] = bool(state['grounded_supports'])
        if inference is not None:
            result['source_inference_usable'] = inference in state['usable_supports']
        return result

    def visit(target):
        if target in conditions:
            return
        record = store.get(target)
        kind, data = record['kind'], record['data']
        item = {'kind': kind, 'hash': record['hash'], 'status': store.status(target),
                'scope': campaign._scope_condition(target)}
        conditions[target] = item
        links = []
        if kind == 'claim':
            item['grounding'] = claim_state(target)
        elif kind == 'inference':
            checks = {'validity', 'scope', 'dependencies'} | ({'discharge'} if data['discharge'] else set())
            item['qualification'] = qualification(target, checks)
            policy = 'formal-only' if data['assurance'] == 'formal' else 'audited-informal'
            item['grounding'] = claim_state(data['conclusion'], set(data['assumptions']), policy, target)
            links = [data['artifact'], data['conclusion'], *data['premises'], *data['assumptions'],
                     *data['discharge'], *data.get('applications', [])]
            if data.get('formal_receipt'):
                links.append(data['formal_receipt'])
        elif kind == 'formal_receipt':
            item['formal'] = campaign._formal_condition(target)
        elif kind == 'formal_plan':
            item['qualification'] = qualification(target, {'formal-source-integrity', 'formal-target-fidelity', 'foundations'})
        elif kind == 'application':
            item['structure'] = campaign._application_structure(target)
            item['qualification'] = qualification(target, {'source', 'hypotheses', 'substitution', 'conclusion'})
            item['current'] = campaign._application_current(target)
            links = list(data['mapping'].values())
        elif kind == 'counterexample':
            checks = {'domain', 'negation', 'scope'} | ({'dependencies'} if data.get('dependencies') else set())
            item['qualification'] = qualification(target, checks)
            evaluation = Evaluation(campaign)
            bounds = evaluation.bounds()
            item['refutation'] = ('certain' if target in bounds['certain'] else
                                  'unresolved' if target in bounds['unresolved'] else 'ineligible')
            links = data.get('dependencies', []) + ([data['formal_receipt']] if data.get('formal_receipt') else [])
        elif kind == 'candidate':
            item['current'] = campaign.candidate_current(target)
            item['audit_current'] = campaign.candidate_audit_current(target)
            item['qualification'] = candidate_qualification(target)
            if store.status(target) == 'audited':
                event = store.db.execute('SELECT e.payload FROM events e JOIN decisions d ON d.event_seq=e.seq '
                                         'WHERE d.target=?', (target,)).fetchone()
                witnesses = json.loads(event['payload']).get('reason', {}).get('reviews') if event else None
                if isinstance(witnesses, list) and witnesses:
                    item['audit_witnesses'] = candidate_qualification(target, witnesses)
                else:
                    item['audit_witnesses'] = {'current': False, 'reason': 'Audit has no exact review witnesses'}
            links = list(data['manifest'])
        elif kind == 'release':
            item['current'] = campaign.release_current(target)
            item['publication_witnesses'] = candidate_qualification(data['candidate'], data['reviews'])
            links = [data['candidate']]
        elif kind == 'obligation':
            item['open'] = campaign.obligation_open(record)
            item['qualification'] = qualification(target, {'obligation-mapping'})
            links = [data['claim']] if data.get('claim') else []
        elif kind == 'route':
            store.get(data.get('target'), 'claim')
            if any(not isinstance(data.get(k), str) or not data[k].strip() for k in ('strategy', 'family')):
                raise StateError('Advisory route source lacks its exact target/strategy/family')
            event = store.db.execute('SELECT e.payload FROM events e JOIN decisions d ON d.event_seq=e.seq '
                                     'WHERE d.target=?', (target,)).fetchone()
            reason = json.loads(event['payload']).get('reason', {}) if event else {}
            item['disposition'] = reason
            links = [reason['certificate']] if reason.get('certificate') else []
        elif kind == 'route_decision':
            links = list(data['sources'])
        elif kind == 'boundary_certificate':
            from .advisory import Advisory
            item['event'] = Advisory(campaign).boundary_data(target)['event']
        elif kind == 'learning_candidate':
            from .curation import Curation
            item['current'] = Curation(campaign).candidate_current(target)
            links = list(data['sources'])
        elif kind == 'learning_admission':
            from .curation import Curation
            item['current'] = Curation(campaign).admission_current(target)
            links = [data['learning'], data['target']]
        elif kind == 'review':
            try:
                item['provenance'] = Tasks(campaign).review_provenance(data['run_id'], data['target'],
                    data['verdict'], data['artifact'], data['checks'])
            except StateError as error:
                item['provenance'] = {'current': False, 'reason': str(error)}
            if data['verdict'] == 'pass':
                item['qualification'] = qualification(data['target'], set(data['checks']), [target])
            links = campaign._review_evidence_ids(target)
        elif kind == 'adjudication':
            item['current'] = campaign._adjudication_current(target)
            item['qualification'] = qualification(target, campaign._adjudication_checks(data))
            related = campaign._related_case_context(data['finding'], exclude=target,
                                                    scope_only=data['disposition'] == 'scope-classified')
            item['related_challenges'] = related
            links = [data['finding'], data['response'], *data.get('prior_findings', []), *related]
        elif kind == 'resolution':
            finding = data.get('finding', data.get('objection'))
            item['dismissal_current'] = campaign._resolution_current(target, finding, frozenset())
            if data['disposition'] == 'scope-classified':
                item['scope_certificate_current'] = campaign._qualified_resolution_current(target, finding, 'scope-classified')
            case = data.get('case')
            checks = campaign._adjudication_checks(store.get(case, 'adjudication')['data']) if case else {'objection-scope', 'dismissed'}
            item['qualification'] = qualification(case or finding, checks, data['reviews'])
            links = [finding, *data['reviews']] + ([case] if case else [])
        elif kind == 'run':
            item['exposures'] = {e['id']: e['data']['category'] for e in store.records('exposure') if e['data']['run'] == target}
            links = [data['task'], data['dispatch_evidence']]
        elif kind == 'task':
            item['packet_hash'] = Tasks(campaign).packet(target)['packet_hash']
        elif kind == 'result':
            links = [data['run'], data['task'], data['artifact'], data['host_receipt']]
        elif kind == 'native_failure':
            item['terminal_public_response'] = data['terminal_public_response']
            item['protocol_error'] = data['protocol_error']
            item['mathematical_acceptance'] = False
            links = [data['run'], data['task'], data['capture_artifact'], data['response_artifact'], data['target']]
        elif kind == 'ingestion_failure':
            item['validation_error'] = data['validation_error']
            links = [data['result'], data['artifact'], data['host_receipt'], data['run'], data['task']]
        elif kind == 'artifact' and data.get('source_result'):
            links = [data['source_result']]
        elif kind == 'learning':
            item['basis_unchanged'] = campaign.learning_current(target)
            links = list(data['sources'])
        if kind == 'objection' or (kind == 'review' and data['verdict'] == 'fail'):
            item['finding_blocking'] = campaign.finding_blocking(target)
            item['effects'] = campaign.finding_effects(target)
            event = store.db.execute('SELECT e.payload FROM events e JOIN decisions d ON d.event_seq=e.seq '
                                     'WHERE d.target=?', (target,)).fetchone()
            resolution = json.loads(event['payload']).get('reason', {}).get('resolution') if event else None
            if resolution:
                links.append(resolution)
        for link in links:
            visit(link)

    visit(identifier)
    return {'profile': BASIS_VERSION, 'conditions': conditions}
