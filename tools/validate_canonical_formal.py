"""Ordinary module proof through the real recorder and canonical evidence path.

Review captures are explicitly synthetic bookkeeping fixtures. This validates
integration and invalidation, not real reviewer independence or fidelity judgment.
"""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
import test_research
from mathtrace.campaign import Campaign
from mathtrace.evidence import Evidence
from mathtrace.formal import receipt_evidence
from mathtrace.store import Store
from mathtrace.toolchain import verify_toolchain


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provisioned-db', type=Path, default=ROOT / 'work/validation/formal/state.sqlite')
    parser.add_argument('--execution-mode', choices=['direct','bubblewrap'], default='direct')
    args = parser.parse_args()
    output = ROOT / 'work/validation/formal' / ('canonical-receipt-' + uuid.uuid4().hex)
    output.mkdir(parents=True)
    with Store(args.provisioned_db) as provisioned:
        toolchains = provisioned.records('toolchain')
        if len(toolchains) != 1:
            raise RuntimeError('Requires the single previously provisioned pinned distribution')
        distribution = toolchains[0]
        verify_toolchain(distribution)
    with Store(output / 'state.sqlite', create=True) as store:
        research = Campaign(store)
        contract = research.contract('True', [], completion='An exact proof of True')
        target = research.claim('True', contract)
        source = research.artifact('module\npublic theorem t : True := True.intro\n', 'text/x-lean')
        bookkeeping = SimpleNamespace(r=research, store=store,
            proof=research.artifact('Synthetic review bookkeeping; no actual independent mathematical assessment'))
        def review(identifier, checks):
            return test_research.ResearchTests.review(bookkeeping, identifier, checks)
        evidence = Evidence(research)
        plan = evidence.formal_plan(target, source, 't', 'True', author='validation-fixture')
        review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        with store.transaction():
            toolchain = store.put('toolchain', distribution['data'])
            store.decide(toolchain, 'installed', {'reason': 'Copied previously verified provisioned validation distribution',
                'provisioned_record_hash': distribution['hash']})
        receipt = evidence.run_lean(plan, toolchain=toolchain, timeout=300, execution_mode=args.execution_mode)
        if store.status(receipt) != 'checked':
            raise RuntimeError('Actual checking did not produce complete modern evidence: ' + str(store.get(receipt)['data']['failures']))
        bound = receipt_evidence(store, receipt)
        review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        if not research._formal_current(receipt):
            raise RuntimeError('Canonical modern qualification failed: ' + str(research._formal_condition(receipt)))
        inference = research.inference(target, [], source, 'validation-fixture', assurance='formal', formal_receipt=receipt)
        review(inference, ['validity', 'scope', 'dependencies'])
        research.promote(inference, expected=store.revision, request_id='validation-formal-binding')
        candidate = research.freeze(target, source, author='validation-fixture', assurance='machine-checked')
        before = research.candidate_current(candidate)
        capsule = store.get(receipt)['data']['semantic_artifact']
        research.withdraw(capsule, 'Validation-only check of exact evidence dependency withdrawal')
        after = research.candidate_current(candidate)
        unsupported = research.claim_state(target, policy='formal-only')['state'] == 'unsupported'
        passed = before and not after and unsupported and store.status(receipt) == 'checked'
        result = {'passed': passed, 'purpose': __doc__, 'review_channel': 'synthetic bookkeeping fixtures',
            'checking_channel': 'actual pinned ' + args.execution_mode + ' compiler and primitive-target verifier',
            'database': str(store.path), 'receipt': receipt, 'candidate': candidate,
            'source_to_object_correspondence': 'unverified', 'independent_host_assessment': 'not exercised',
            'bound_records': len(bound['records']), 'profile_declarations': len(bound['report']['reference_profile']['declarations']),
            'checked_declarations': len(bound['report']['semantics']['declarations']),
            'candidate_current_before_withdrawal': before, 'candidate_current_after_withdrawal': after,
            'claim_unsupported_after_withdrawal': unsupported, 'historical_receipt_status': store.status(receipt),
            'helper_sha256': store.get(receipt)['data']['helper_sha256']}
        (output / 'evidence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'passed': passed, 'evidence': str(output / 'evidence.json')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
