"""Synthetic review bookkeeping; these fixtures establish no mathematical truth."""
import unittest
import json
import sys
from copy import deepcopy
from unittest.mock import patch

import test_research
import formal_fixture
from mathtrace.campaign import Campaign
from mathtrace.completion import Completion
from mathtrace.context import Tasks
from mathtrace.coordination import Coordination
from mathtrace.evidence import Evidence
from mathtrace.native_capture import NativeCapture
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class CompletionTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.co = Completion(self.r)
        self.target = self.claim()

    def request(self, targets=None, *, assurance='audited-informal', delivery='audited-result', duties=None, previous=None):
        outputs = [{'target': t, 'outcomes': ['proof'], 'assurance': assurance,
                    'delivery': delivery, 'duties': [] if duties is None else duties}
                   for t in targets or [self.target]]
        request = self.co.request(self.contract, outputs, self.proof, author='root', previous=previous)
        self.review(request, ['completion-mapping', 'criteria-coverage'], role='fidelity-auditor')
        self.co.activate(request, expected=self.store.revision, reason='Exact user-request scope bound', supersedes=previous)
        return request

    def candidate(self, target=None, *, outcome='proof'):
        target = target or self.target
        if outcome == 'proof':
            support = self.accept(target)
        else:
            support = self.r.counterexample(target, self.proof, 'hunter')
            self.review(support, ['domain', 'negation', 'scope'])
            self.r.validate_counterexample(support, expected=self.store.revision)
        frozen = self.r.freeze(target, self.proof, author='author', outcome=outcome)
        self.audit(frozen)
        return frozen, support

    def audit(self, candidate):
        outcome = self.store.get(candidate)['data']['outcome']
        self.review(candidate, ['full-proof' if outcome == 'proof' else 'full-refutation', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)

    def dismiss_report(self, report, *, disposition='invalid'):
        response = self.r.artifact('Self-contained assessment of exact retained report: the asserted witness is outside the declared domain; no provenance/format argument is used as mathematical clearance.')
        case = self.r.adjudication(report, response, disposition='dismissed', report_disposition=disposition, author='root')
        self.review(case, sorted(self.r._adjudication_checks(self.store.get(case)['data'])), role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        return case, response

    def test_unproved_request_mapping_is_independent_of_support_and_legacy_has_no_implicit_fulfillment(self):
        request = self.request()
        self.assertFalse(self.co.fulfillment(request)['mathematics_sufficient'])
        packet = Tasks(self.r).packet(self.store.records('task')[0]['id'])
        self.assertNotIn('candidate', {r['kind'] for r in packet['records'].values()})
        self.assertFalse(self.r.progress()['contract_fulfilled'])
        self.candidate()
        state = self.co.fulfillment(request)
        self.assertTrue(state['contract_fulfilled'])
        self.assertFalse(state['autonomous_exploration_required'])
        self.assertEqual(self.r.progress()['next']['action'], 'contract-fulfilled')
        frontier = Coordination(self.r).frontier(self.target)
        self.assertTrue(frontier['solved'])
        self.assertTrue(next(i for i in frontier['items'] if i['action'] == 'independent-discovery')['optional_research'])
        self.assertEqual(state['research_exhaustion'], 'not-claimed')
        other = self.claim('Other unbound problem')
        self.candidate(other)
        self.assertFalse(Coordination(self.r).frontier(other)['completion_bound'])

    def test_insufficient_assurance_and_all_required_targets_are_enforced(self):
        candidate, _ = self.candidate()
        machine = self.request(assurance='machine-checked')
        self.assertTrue(self.r.candidate_audit_current(candidate))
        self.assertFalse(self.co.fulfillment(machine)['mathematics_sufficient'])
        self.r.withdraw(machine, 'Replaced test request, not a truth change')
        other = self.claim('Second required output')
        both = self.request([self.target, other])
        self.assertFalse(self.co.fulfillment(both)['contract_fulfilled'])
        self.candidate(other)
        self.assertTrue(self.co.fulfillment(both)['contract_fulfilled'])

    def test_publication_only_withdrawal_reopens_delivery_but_preserves_mathematics(self):
        request = self.request(delivery='released-result')
        candidate, _ = self.candidate()
        self.assertTrue(self.co.fulfillment(request)['mathematics_sufficient'])
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        release_action = next(a for a in Orchestration(self.r).next_actions()['actions']
                              if a['action'] == 'release-candidate' and a.get('candidate') == candidate)
        self.assertFalse(release_action['optional_research'])
        self.assertIn('finish-requested-delivery', [i['action'] for i in Coordination(self.r).frontier(self.target)['items']])
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        certificate = self.co.record_fulfillment(request, expected=self.store.revision, request_id='delivery')['certificate']
        self.r.withdraw(release, 'Publication logistics withdrawn; proof unchanged')
        state = self.co.fulfillment(request)
        self.assertTrue(state['mathematics_sufficient'])
        self.assertFalse(state['contract_fulfilled'])
        self.assertFalse(self.co.certificate_current(certificate))

    def test_additional_duty_requires_exact_candidate_evidence_without_reproof_and_pins_witnesses(self):
        request = self.request(duties=['Provide an elementary proof'])
        candidate, _ = self.candidate()
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        evidence = self.co.evidence(request, 0, candidate, self.proof, author='root')
        self.review(evidence, ['completion-duties'], role='fidelity-auditor')
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])
        certificate = self.co.record_fulfillment(request, expected=self.store.revision, request_id='duty')['certificate']
        self.review(evidence, ['completion-duties'], role='fidelity-auditor')
        self.assertTrue(self.co.certificate_current(certificate))
        pinned = self.store.get(certificate)['data']['selected'][0]['reviews'][0]
        self.r.withdraw(pinned, 'Exact duty witness retracted')
        self.assertFalse(self.co.certificate_current(certificate))
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])

    def test_new_alternative_restores_live_sufficiency_without_substituting_historical_certificate(self):
        request = self.request()
        first, support = self.candidate()
        certificate = self.co.record_fulfillment(request, expected=self.store.revision, request_id='first')['certificate']
        self.r.withdraw(support, 'First selected argument withdrawn')
        self.assertFalse(self.co.certificate_current(certificate))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        second, _ = self.candidate()
        self.assertNotEqual(first, second)
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])
        self.assertFalse(self.co.record_fulfillment(request, expected=0, request_id='first')['current'])

    def test_pending_lost_and_aliased_counterexample_reports_block_finalization_until_substantive_disposition(self):
        request = self.request()
        candidate, _ = self.candidate()
        publication = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        alias = self.claim()
        report = self.r.counterexample(alias, self.proof, 'critic')
        self.r.withdraw(report, 'Withdraw producer attribution, not mathematical report')
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.r.candidate_audit_current(candidate))
        self.assertFalse(self.r.release_current(publication))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        self.assertTrue(any(a.get('report') == report for a in Orchestration(self.r).next_actions()['actions']))
        with self.assertRaises(StateError):
            self.r.adjudication(report, self.proof, disposition='dismissed', author='root')
        case, response = self.dismiss_report(report)
        self.assertTrue(self.r._adjudication_current(case))
        self.assertFalse(self.r.finding_blocking(report))
        self.assertTrue(self.r.release_current(publication))
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])
        self.r.withdraw(response, 'Disposition evidence withdrawn')
        self.assertFalse(self.r.release_current(publication))

    def test_optional_unknown_attempt_survives_fulfillment_and_alias_request_cannot_replace_original(self):
        request = self.request()
        self.candidate()
        task = Tasks(self.r).create('scout', self.target, checks=['exploration'], mandate='Optional additional search')
        NativeCapture(self.r).reserve([task], '11111111-1111-4111-8111-111111111111')
        self.r.withdraw(task, 'Retired without claiming child stopped')
        state = self.co.fulfillment(request)
        self.assertTrue(state['contract_fulfilled'])
        self.assertTrue(state['maintenance'])
        self.assertFalse(state['maintenance'][0]['retry_authorized'])
        alias = self.claim()
        new = self.co.request(self.contract, [{'target': alias, 'outcomes': ['proof'], 'assurance': 'audited-informal',
            'delivery': 'audited-result', 'duties': []}], self.proof, author='root')
        self.review(new, ['completion-mapping', 'criteria-coverage'], role='fidelity-auditor')
        with self.assertRaises(StateError):
            self.co.activate(new, expected=self.store.revision, reason='Cannot silently replace original')
        self.assertEqual(self.store.status(request), 'active')

    def test_lost_validated_counterevidence_does_not_silently_restore_publication(self):
        request = self.request()
        candidate, _ = self.candidate()
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        artifact = self.r.artifact('Reported exact witness, with a purported domain/violation argument')
        report = self.r.counterexample(self.target, artifact, 'critic')
        self.review(report, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(report, expected=self.store.revision)
        self.r.withdraw(artifact, 'Source withdrawn, allegation has not been ruled out')
        self.assertEqual(self.r.claim_state(self.target)['state'], 'supported')
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.r.release_current(release))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        self.dismiss_report(report)
        self.assertTrue(self.r.release_current(release))

    def test_conditional_children_and_disproof_orientation_have_scoped_report_relevance(self):
        conditional = self.claim('Conditional P')
        assumption = self.r.assumption('A')
        child = self.r.inference(conditional, [], self.proof, 'author', assumptions=[assumption])
        self.review(child)
        self.r.promote(child, expected=self.store.revision, request_id='conditional-child')
        root = self.r.inference(self.target, [conditional], self.proof, 'author',
            discharge=[assumption], rule='contradiction')
        self.review(root, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(root, expected=self.store.revision, request_id='discharged-root')
        self.r.counterexample(conditional, self.r.artifact('Alleged unconditional negative of P'), 'critic')
        frozen = self.r.freeze(self.target, self.proof, author='author')
        self.audit(frozen)
        self.assertTrue(self.r.candidate_audit_current(frozen))
        negative = self.claim('Disproof target')
        self.r.counterexample(negative, self.r.artifact('Additional alleged negative'), 'critic')
        disproof, _ = self.candidate(negative, outcome='disproof')
        self.assertTrue(self.r.candidate_audit_current(disproof))
        self.assertFalse(any(a['action'] == 'adjudicate-counterexample-report' and a.get('target') == negative
                             for a in Orchestration(self.r).next_actions()['actions']))

    def test_unsubstantiated_report_reopens_when_dependency_acquires_support(self):
        candidate, _ = self.candidate()
        dependency = self.claim('Reported supporting lemma')
        report = self.r.counterexample(self.target, self.r.artifact('Allegation depends on this separate lemma'),
                                     'critic', dependencies=[dependency])
        case, _ = self.dismiss_report(report, disposition='unsubstantiated')
        self.assertFalse(self.r.finding_blocking(report))
        self.assertTrue(self.r.candidate_audit_current(candidate))
        self.accept(dependency)
        self.assertFalse(self.r._adjudication_current(case))
        self.assertTrue(self.r.finding_blocking(report))
        self.assertFalse(self.r.candidate_audit_current(candidate))

    def test_empty_or_imported_unbound_request_cannot_report_vacuous_fulfillment(self):
        with self.assertRaises(StateError):
            self.co.request(self.contract, [], self.proof, author='root')
        request = self.request()
        malformed = deepcopy(self.store.get(request)['data'])
        malformed['outputs'] = []
        with self.store.transaction():
            identifier = self.store.put('completion_request', malformed)
            self.store.decide(identifier, 'active', {'reason': 'Malformed imported fixture'})
        with self.assertRaises(StateError):
            self.co.fulfillment(identifier)

    def test_draft_revision_does_not_replace_current_requested_scope(self):
        request = self.request()
        self.candidate()
        draft = self.co.request(self.contract, [{'target': self.target, 'outcomes': ['proof'],
            'assurance': 'machine-checked', 'delivery': 'released-result', 'duties': []}],
            self.proof, author='root', previous=request)
        frontier = Coordination(self.r).frontier(self.target)
        self.assertTrue(frontier['contract_fulfilled'])
        self.assertTrue(self.r.progress()['contract_fulfilled'])
        self.assertEqual(frontier['draft_completion_requests'], [draft])
        self.assertIn('contract-fulfilled', [i['action'] for i in frontier['items']])
        other = self.r.contract('Different original request', [], completion='Different scope')
        target = self.r.claim('Other target', other)
        with self.assertRaises(StateError):
            self.co.request(other, [{'target': target, 'outcomes': ['proof'], 'assurance': 'audited-informal',
                'delivery': 'audited-result', 'duties': []}], self.proof, author='root', previous=request)

    def test_retained_unimported_negative_result_requires_substantive_clearance_after_withdrawal(self):
        request = self.request()
        candidate, _ = self.candidate()
        tasks = Tasks(self.r)
        task = tasks.create('falsifier', self.target, checks=['falsification'], mandate='Find a counterexample')
        packet = tasks.packet(task)
        dispatch = self.r.artifact(json.dumps({'kind': 'native-dispatch-capture', 'task_id': task,
            'packet_hash': packet['packet_hash'], 'conversation_id': 'negative-fixture',
            'host': 'antigravity', 'declared_tools': [], 'declared_inherited_history': False}))
        run = tasks._start_captured(task, 'negative-fixture', host='antigravity',
            dispatch_evidence=dispatch, tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': packet['packet_hash'], 'outcome': 'counterexample',
            'checks': ['falsification'], 'reasoning': 'Exact alleged witness preserved before mathematical import'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'negative-fixture', 'status': 'SUCCESS', 'response': output}))
        result = tasks._finish_captured(run, artifact, receipt, outcome='counterexample', checks=['falsification'])
        self.r.withdraw(result, 'Producer attribution retracted; allegation retained')
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        self.assertTrue(self.r.finding_effects(result)['finalization_hold'])
        self.assertFalse(self.r.finding_effects(result)['statement_scope_hold'])
        self.dismiss_report(result)
        self.assertEqual(self.store.status(result), 'withdrawn')
        self.assertFalse(self.r.finding_blocking(result))
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])

    def test_machine_checked_candidate_satisfies_weaker_request_without_relabel_or_refreeze(self):
        # Synthetic checker fixture exercises policy compatibility only.
        self.target = self.claim('True')
        request = self.request()
        evidence = Evidence(self.r)
        source = self.r.artifact('theorem t : True := by trivial')
        plan = evidence.formal_plan(self.target, source, 't', 'True', author='formalizer')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        toolchain = formal_fixture.toolchain(self.r)
        checked = formal_fixture.execution(self.r, plan)
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(checked)), \
             patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            receipt = evidence.run_lean(plan, toolchain=toolchain)
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        inference = self.r.inference(self.target, [], self.proof, 'author', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='formal-completion')
        candidate = self.r.freeze(self.target, self.proof, author='author', assurance='machine-checked')
        self.review(candidate, ['full-proof', 'dependency-closure', 'formal-environment'])
        self.review(candidate, ['target-fidelity', 'formal-target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])
        certificate = self.co.record_fulfillment(request, expected=self.store.revision, request_id='stronger')['certificate']
        self.assertTrue(self.co.certificate_current(certificate))
        self.assertEqual(len(self.store.records('candidate')), 1)
        self.assertEqual(self.store.get(candidate)['data']['assurance'], 'machine-checked')

    def test_imported_duty_evidence_cannot_erase_required_responsibility(self):
        request = self.request(duties=['Supply an explicit algorithm'])
        candidate, _ = self.candidate()
        evidence = self.co.evidence(request, 0, candidate, self.proof, author='root')
        data = deepcopy(self.store.get(evidence)['data'])
        data['checks'] = []
        with self.store.transaction():
            malformed = self.store.put('completion_evidence', data)
        self.review(malformed, ['unrelated-check'], role='fidelity-auditor')
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])

    def test_imported_publication_cannot_forge_candidate_metadata_or_audit_lineage(self):
        request = self.request(delivery='released-result')
        candidate, _ = self.candidate()
        baseline = {'candidate': candidate, 'target': self.target,
            'manifest_hash': self.store.get(candidate)['data']['manifest_hash'],
            'assurance': 'audited-informal', 'outcome': 'proof',
            'reviews': self.r._audit_reviews(candidate), 'supersedes': None, 'reason': None}
        for field, value in [('target', self.claim('Other target')), ('manifest_hash', 'forged'),
            ('assurance', 'machine-checked'), ('outcome', 'disproof'), ('supersedes', 'forged-publication')]:
            with self.store.transaction():
                publication = self.store.put('release', {**baseline, field: value})
                self.store.decide(publication, 'released', {'candidate': candidate, 'assurance': 'audited-informal'})
            self.assertFalse(self.r.release_current(publication))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])

    def test_quarantined_negative_result_remains_report_after_generic_concern_is_cleared(self):
        import test_orchestration
        request = self.request()
        candidate, _ = self.candidate()
        result = test_orchestration.OrchestrationTests.result(self, self.target, 'counterexample', [
            {'local_id': 'ce', 'kind': 'counterexample', 'data': {'target': self.target}},
            {'local_id': 'bad', 'kind': 'unsupported-kind', 'data': {}}])
        quarantine = Orchestration(self.r).ingest(result)
        finding = quarantine['substance_finding']
        response = self.r.artifact('Exact retained public substance assessment; ordinary concern only')
        case = self.r.adjudication(finding, response, disposition='dismissed', author='root')
        self.review(case, sorted(self.r._adjudication_checks(self.store.get(case)['data'])), role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(self.r.finding_blocking(result))
        self.assertFalse(self.r.candidate_audit_current(candidate))
        self.assertFalse(self.co.fulfillment(request)['contract_fulfilled'])
        self.dismiss_report(result)
        self.assertTrue(self.co.fulfillment(request)['contract_fulfilled'])


if __name__ == '__main__':
    unittest.main()
