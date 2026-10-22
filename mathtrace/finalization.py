"""Retained counterexample reports at finalization, separate from refutation."""
import json

from .store import StateError, digest
from .witness import nodes

REPORT_PROFILE = 'retained-counterexample-report-v1'
REPORT_DISPOSITIONS = {'invalid', 'irrelevant', 'unsubstantiated'}


def report_source(record):
    return record['kind'] == 'counterexample' or (record['kind'] == 'result' and record['data']['outcome'] == 'counterexample')


def report_subject(research, identifier):
    record = research.store.get(identifier)
    if not report_source(record):
        raise StateError('Not an exact counterexample report source')
    if record['kind'] == 'counterexample':
        return record['data']['target']
    from .context import Tasks
    target = Tasks(research)._claim_for(identifier)
    if target is None:
        raise StateError('Retained negative result lacks an exact claim boundary')
    return target


def statement_key(research, target):
    store = research.store
    claim = store.get(target, 'claim')['data']
    contract = store.get(claim['contract'], 'contract')['data']
    return digest({'statement': claim['statement'], 'original': contract['statement'],
        'foundations': sorted(contract['allowed_axioms']),
        'definitions': {r: store.get(r)['hash'] for r in sorted(set(claim['definitions'] + contract['definitions']))}})


def report_basis(research, identifier):
    """Source facts, excluding the report's own dismissal/current support."""
    store = research.store
    report = store.get(identifier)
    if not report_source(report):
        raise StateError('Not an exact counterexample report source')
    d = report['data']
    target = report_subject(research, identifier)
    refs = [d['artifact'], *research._statement_manifest(target)]
    if report['kind'] == 'result':
        run = store.get(d['run'], 'run')
        refs += [d['host_receipt'], d['task'], d['run'], run['data']['dispatch_evidence']]
    if d.get('formal_receipt'):
        refs.append(d['formal_receipt'])
    dependencies = d.get('dependencies', [])
    research._counterexample_dependencies(dependencies)
    # A later proof of a reported dependency can substantiate a previously
    # unsubstantiated report. Record reachable source rosters, not an evaluation
    # whose outcome changes when this report itself is dismissed.
    sources, pending, seen = {}, list(dependencies), set()
    while pending:
        claim = pending.pop()
        if claim in seen:
            continue
        seen.add(claim)
        refs.extend(research._statement_manifest(claim))
        for inference in store.records('inference'):
            if inference['data']['conclusion'] != claim:
                continue
            data = inference['data']
            sources[inference['id']] = {'hash': inference['hash'], 'status': store.status(inference['id']),
                'artifact_scope': research._scope_condition(data['artifact']),
                'formal': research._formal_condition(data['formal_receipt']) if data.get('formal_receipt') else None,
                'applications': {r: {'hash': store.get(r)['hash'], 'status': store.status(r),
                                    'current': research._application_current(r)} for r in data.get('applications', [])},
                'qualification': research._review_condition(inference['id'],
                    {'validity', 'scope', 'dependencies'} | ({'discharge'} if data['discharge'] else set()))}
            pending.extend(data['premises'])
    markers = []
    for event in store.db.execute("SELECT seq,hash,payload FROM events WHERE type='decision' AND target=? ORDER BY seq", (identifier,)):
        value = json.loads(event['payload'])
        if value.get('status') in {'validated', 'withdrawn', 'provenance-retracted', 'rejected'}:
            markers.append({'revision': event['seq'], 'hash': event['hash'], 'status': value['status']})
    return {'profile': REPORT_PROFILE, 'report_hash': report['hash'], 'statement_key': statement_key(research, target),
        'source_records': {r: {'hash': store.get(r)['hash'], 'status': store.status(r),
                              'scope': research._scope_condition(r)} for r in dict.fromkeys(refs)},
        'qualification': research._review_condition(identifier,
            {'domain', 'negation', 'scope'} | ({'dependencies'} if dependencies else set()))
            if report['kind'] == 'counterexample' else {'scope': 'retained result; not itself a qualified counterexample'},
        'report_boundaries': markers, 'dependency_sources': sources}


def reports_for(research, positive_claims):
    keys = {statement_key(research, c) for c in positive_claims}
    result = []
    for report in research.store.records('counterexample'):
        if statement_key(research, report['data']['target']) not in keys:
            continue
        if research.finding_blocking(report['id']):
            result.append(report['id'])
    store = research.store
    imported = {event['target'] for event in store.db.execute("SELECT target,payload FROM events WHERE type='proposal-import'")
                if any(store.get(r)['kind'] == 'counterexample' for r in json.loads(event['payload'])['created'])}
    for report in store.records('result'):
        if (report['data']['outcome'] == 'counterexample' and report['id'] not in imported
                and statement_key(research, report_subject(research, report['id'])) in keys
                and research.finding_blocking(report['id'])):
            result.append(report['id'])
    return result


def candidate_report_condition(research, identifier):
    data = research.store.get(identifier, 'candidate')['data']
    positive = set()
    try:
        for node in nodes(data['derivation']['witness']).values():
            inference = research.store.get(node['inference'], 'inference')['data']
            if not inference['assumptions']:
                positive.add(inference['conclusion'])
    except (StateError, KeyError, TypeError, ValueError):
        return {'current': False, 'positive_judgments': [], 'pending_reports': [],
                'reason': 'Selected finalization judgments are malformed'}
    reports = reports_for(research, positive)
    return {'current': not reports, 'positive_judgments': sorted(positive), 'pending_reports': reports,
        'reason': 'Exact retained counterexample reports need substantive disposition' if reports else None,
        'authority': 'Finalization limit; not a negation premise or statement-scope certificate'}
