"""Finding polarity across scope, grounding, evidence and publication.

Captured review/checker fixtures test protocol semantics, not mathematical
validity or observed live-host guarantees.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_research
import formal_fixture
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.evidence import Evidence
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class FindingEffectTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def certify(self, finding):
        response = self.r.artifact('The exact challenge addresses unconditional truth only. '
            'Definitions, domains, assumptions, fidelity and statement provenance are unaffected; synthetic scope fixture.')
        case = self.r.adjudication(finding, response, disposition='scope-classified',
                                   impact='unconditional-truth', author='root')
        checks = sorted(self.r._adjudication_checks(self.store.get(case)['data']))
        witness = self.review(case, checks, role='adjudicator')
        certificate = self.r.adjudicate(case, expected=self.store.revision)
        return case, witness, certificate

    def example(self, target, dependencies=None):
        example = self.r.counterexample(target, self.proof, 'hunter', dependencies=dependencies)
        self.review(example, ['domain', 'negation', 'scope'] + (['dependencies'] if dependencies else []))
        return example

    def test_scope_certification_precedes_substantive_truth_and_allows_negative_release(self):
        target = self.claim('False')
        finding = self.r.objection(target, self.proof, 'critic')
        example = self.example(target)
        with self.assertRaises(StateError):
            self.r.validate_counterexample(example, expected=self.store.revision)
        case = self.r.adjudication(finding, self.proof, disposition='scope-classified',
                                   impact='unconditional-truth', author='root')
        self.review(case, ['finding-scope', 'counterargument', 'scope-classified'], role='adjudicator')
        with self.assertRaises(StateError):
            self.r.adjudicate(case, expected=self.store.revision)
        self.review(case, sorted(self.r._adjudication_checks(self.store.get(case)['data'])), role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        self.assertEqual(self.store.status(finding), 'open')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertEqual(self.r.claim_state(target)['state'], 'disputed')
        self.assertEqual(self.r.claim_state(target)['refutations'], [])
        false_positive = self.r.inference(target, [], self.proof, 'worker')
        self.review(false_positive)
        with self.assertRaises(StateError):
            self.r.promote(false_positive, expected=self.store.revision, request_id='positive-remains-held')
        self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(target)['state'], 'refuted')
        candidate = self.r.freeze(target, self.proof, author='author', outcome='disproof')
        self.review(candidate, ['full-refutation', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        self.assertTrue(self.r.release_current(release))

    def test_conditional_contradiction_survives_but_ambient_assumptions_do_not_launder(self):
        assumption = self.r.assumption('A')
        target, negation, result = self.claim('P'), self.claim('Not P'), self.claim('Not A')
        finding = self.r.objection(target, self.proof, 'critic')
        conditional = self.r.inference(target, [], self.proof, 'worker', assumptions=[assumption])
        self.review(conditional)
        with self.assertRaises(StateError):
            self.r.promote(conditional, expected=self.store.revision, request_id='unknown-hold')
        self.certify(finding)
        self.r.promote(conditional, expected=self.store.revision, request_id='declared-conditional')
        self.assertEqual(self.r.eligible_supports(target), [])
        self.assertEqual(self.r.eligible_supports(target, {assumption}), [conditional])
        self.accept(negation)
        contradiction = self.r.inference(result, [target, negation], self.proof, 'worker',
                                         discharge=[assumption], rule='contradiction')
        self.review(contradiction, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(contradiction, expected=self.store.revision, request_id='scoped-contradiction')
        candidate = self.r.freeze(result, self.proof, author='author')
        self.assertTrue(self.r.candidate_current(candidate))
        unscoped = self.r.inference(target, [], self.proof, 'worker', discharge=[assumption], rule='contradiction')
        self.review(unscoped, ['validity', 'scope', 'dependencies', 'discharge'])
        with self.assertRaises(StateError):
            self.r.promote(unscoped, expected=self.store.revision, request_id='discharge-is-not-output-scope')
        second = self.r.objection(target, self.proof, 'different-critic')
        self.assertTrue(self.r.finding_effects(second)['statement_scope_hold'])
        self.assertEqual(self.r.eligible_supports(target, {assumption}), [])
        self.assertFalse(self.r.candidate_current(candidate))

    def test_truth_hold_forbids_transitive_positive_and_refutation_dependencies(self):
        premise, consequence, disproved = self.claim('P'), self.claim('Q'), self.claim('R')
        support = self.accept(premise)
        self.accept(consequence, [premise])
        example = self.example(disproved, [premise])
        self.r.validate_counterexample(example, expected=self.store.revision)
        finding = self.r.objection(premise, self.proof, 'critic')
        self.certify(finding)
        state = self.r.claim_state(premise)
        self.assertEqual(state['state'], 'disputed')
        self.assertEqual(state['supports'], [support])
        self.assertEqual(state['grounded_supports'], [support])
        self.assertEqual(state['usable_supports'], [])
        self.assertIn(premise, state['negative_use_blockers'])
        self.assertEqual(self.r.claim_state(consequence)['usable_supports'], [])
        self.assertEqual(self.r.claim_state(disproved)['refutations'], [])
        self.assertEqual(self.store.status(example), 'validated')
        with self.assertRaises(StateError):
            self.r.freeze(premise, self.proof, author='author')

    def test_scope_certificate_preserves_conflict_instead_of_outvoting_positive_evidence(self):
        target = self.claim()
        accepted = self.accept(target)
        finding = self.r.objection(target, self.proof, 'critic')
        self.certify(finding)
        example = self.example(target)
        self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(target)['state'], 'conflict')
        for outcome in ('proof', 'disproof'):
            with self.assertRaises(StateError):
                self.r.freeze(target, self.proof, author='author', outcome=outcome)
        self.r.withdraw(accepted, 'Erroneous positive argument abandoned after reconciliation')
        self.assertEqual(self.r.claim_state(target)['state'], 'refuted')
        self.assertTrue(self.r.candidate_current(self.r.freeze(target, self.proof, author='author', outcome='disproof')))

    def test_scope_evidence_is_pinned_and_recovers_only_by_explicit_recertification(self):
        target = self.claim()
        finding = self.r.objection(target, self.proof, 'critic')
        case, witness, certificate = self.certify(finding)
        example = self.example(target)
        self.r.validate_counterexample(example, expected=self.store.revision)
        candidate = self.r.freeze(target, self.proof, author='author', outcome='disproof')
        learning = self.r.learning('Exact negative route remained usable', [candidate, finding],
                                  category='counterexample', reopen_condition='Scope evidence changes')
        self.r.withdraw(witness, 'Scope reviewer provenance lost')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertFalse(self.r.candidate_current(candidate))
        self.assertFalse(self.r.learning_current(learning))
        self.review(case, sorted(self.r._adjudication_checks(self.store.get(case)['data'])), role='adjudicator')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        self.certify(finding)
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertTrue(self.r.candidate_current(candidate))
        response = self.store.get(case)['data']['response']
        challenge = self.r.objection(response, self.proof, 'counterargument-critic')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        repaired, _, _ = self.certify(finding)
        self.assertIn(challenge, self.store.get(repaired)['data']['prior_findings'])
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.r.withdraw(self.r.finding_effects(finding)['scope_certificate'], 'Latest certificate retracted')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])  # No fallback to an old event.
        self.assertEqual(self.store.get(certificate)['data']['reviews'], [witness])

    def test_retraction_requires_fresh_scope_evidence_but_validation_is_a_separate_axis(self):
        target = self.claim()
        finding = self.r.objection(target, self.proof, 'critic')
        self.certify(finding)
        substantive = self.r.adjudication(finding, self.proof, disposition='validated', author='root')
        self.review(substantive, ['finding-scope', 'counterargument', 'validated'], role='adjudicator')
        self.r.adjudicate(substantive, expected=self.store.revision)
        self.assertEqual(self.store.status(finding), 'validated')
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertNotIn(finding, self.r.progress()['unresolved_findings'])
        self.assertEqual(self.r.progress()['next']['action'], 'investigate-disputed-claims')
        self.r.withdraw(finding, 'Negative producer attribution retracted')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        self.certify(finding)
        self.assertEqual(self.store.status(finding), 'provenance-retracted')
        self.assertTrue(self.r.finding_effects(finding)['unconditional_use_hold'])
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])

    def test_certificate_cannot_exempt_infrastructure_or_resurrect_a_withdrawn_statement(self):
        definition = self.r.definition('Exact domain', 'Integers with ordinary equality')
        target = self.r.claim('0 = 1', self.contract, definitions=[definition])
        finding = self.r.objection(target, self.proof, 'critic')
        case, _, _ = self.certify(finding)
        self.assertIn(definition, self.store.get(case)['data']['scope_manifest'])
        infrastructure = self.r.objection(definition, self.proof, 'definition-critic')
        with self.assertRaises(StateError):
            self.r.adjudication(infrastructure, self.proof, disposition='scope-classified',
                                impact='unconditional-truth', author='root')
        self.assertFalse(self.r._scope_current(target))
        self.assertIsNone(self.r.finding_effects(finding)['scope_certificate'])
        self.r.withdraw(target, 'Exact statement withdrawn')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])

    def test_formal_checking_is_evidence_and_cannot_bypass_the_unconditional_hold(self):
        evidence = Evidence(self.r)
        target = self.claim('True')
        source = self.r.artifact('theorem t : True := by trivial')
        plan = evidence.formal_plan(target, source, 't', 'True', author='formalizer')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        toolchain = formal_fixture.toolchain(self.r)
        symbol = self.store.get(plan)['data']['check_symbol']
        process = {'exit_code': 0, 'timed_out': False, 'namespace_setup': True, 'output_limited': False}
        checked = formal_fixture.execution(self.r, plan)
        finding = self.r.objection(target, self.proof, 'critic')
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(checked)) as runner, \
             patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            with self.assertRaises(StateError):
                evidence.run_lean(plan, toolchain=toolchain)
            self.assertEqual(runner.call_count, 0)
            self.certify(finding)
            receipt = evidence.run_lean(plan, toolchain=toolchain)
            self.assertEqual(runner.call_count, 1)
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.assertTrue(self.r._formal_current(receipt))
        inference = self.r.inference(target, [], self.proof, 'worker', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        with self.assertRaises(StateError):
            self.r.promote(inference, expected=self.store.revision, request_id='checking-is-not-acceptance')
        dismissal = self.r.adjudication(finding, self.proof, disposition='dismissed', author='root')
        self.review(dismissal, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        self.r.adjudicate(dismissal, expected=self.store.revision)
        self.r.promote(inference, expected=self.store.revision, request_id='after-substantive-dismissal')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'supported')
        negative_target = self.claim('False')
        negative_finding = self.r.objection(negative_target, self.proof, 'negative-critic')
        negative_source = self.r.artifact('theorem negation : Not False := by intro h; cases h')
        negative_plan = evidence.formal_plan(negative_target, negative_source, 'negation', 'Not False',
                                            author='formalizer', outcome='disproof')
        self.review(negative_plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        self.certify(negative_finding)
        negative_symbol = self.store.get(negative_plan)['data']['check_symbol']
        checked = formal_fixture.execution(self.r, negative_plan)
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(checked)), \
             patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            negative_receipt = evidence.run_lean(negative_plan, toolchain=toolchain)
        self.review(negative_receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.assertTrue(self.r._formal_current(negative_receipt))
        example = self.r.counterexample(negative_target, self.proof, 'hunter', formal_receipt=negative_receipt)
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        candidate = self.r.freeze(negative_target, self.proof, author='author', outcome='disproof', assurance='machine-checked')
        self.assertTrue(self.r.candidate_current(candidate))

    def test_scope_and_substantive_response_challenges_do_not_cross_couple(self):
        target = self.claim()
        finding = self.r.objection(target, self.proof, 'critic')
        scope, _, _ = self.certify(finding)
        response = self.r.artifact('Independent exact substantive dismissal argument')
        substantive = self.r.adjudication(finding, response, disposition='dismissed', author='root')
        self.review(substantive, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        self.r.adjudicate(substantive, expected=self.store.revision)
        scope_challenge = self.r.objection(self.store.get(scope)['data']['response'], self.proof, 'scope-critic')
        self.assertIsNone(self.r.finding_effects(finding)['scope_certificate'])
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(self.r._scope_current(target))
        fresh_substantive = self.r.adjudication(finding, self.proof, disposition='dismissed', author='root')
        self.assertNotIn(scope_challenge, self.store.get(fresh_substantive)['data']['prior_findings'])
        scope, _, _ = self.certify(finding)
        self.r.objection(response, self.proof, 'substantive-critic')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertIsNotNone(self.r.finding_effects(finding)['scope_certificate'])
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])

    def test_challenge_and_second_order_evidence_changes_revoke_old_scope_permission(self):
        target = self.claim()
        challenge = self.r.artifact('Exact challenge whose retained meaning is being classified')
        finding = self.r.objection(target, challenge, 'critic')
        self.certify(finding)
        self.r.withdraw(challenge, 'Original challenge producer provenance retracted')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        fresh, _, _ = self.certify(finding)
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertFalse(self.store.get(fresh)['data']['finding_evidence'][challenge]['scope']['current'])
        second = self.r.objection(finding, self.proof, 'identity-critic')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        repaired, _, _ = self.certify(finding)
        self.assertIn(second, self.store.get(repaired)['data']['scope_evidence_challenges'])
        self.assertIn('scope-evidence-challenges', self.r._adjudication_checks(self.store.get(repaired)['data']))
        packet = Tasks(self.r).packet(Tasks(self.r).create('adjudicator', repaired, independence='informed',
            checks=sorted(self.r._adjudication_checks(self.store.get(repaired)['data'])), mandate='Inspect exact scope evidence'))
        self.assertIn(second, packet['records'])
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.assertTrue(self.r.finding_blocking(second))  # Retained bytes were assessed; source finding not dismissed.

    def test_failed_review_producer_loss_invalidates_scope_certification(self):
        target = self.claim()
        finding = self.review(target, ['claim-validity'], verdict='fail', role='falsifier')
        self.certify(finding)
        result = self.store.get(finding)['data']['provenance']['result']
        receipt = self.store.get(result)['data']['host_receipt']
        self.r.withdraw(receipt, 'Original failed review completion binding was retracted')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])
        case, _, _ = self.certify(finding)
        provenance = self.store.get(case)['data']['finding_evidence'][finding]['provenance']
        self.assertFalse(provenance['current'])
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.r.objection(receipt, self.proof, 'producer-critic')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])  # False-to-false cause changed.

    def test_scope_packets_reject_support_history_and_malformed_target_binding(self):
        target = self.claim()
        finding = self.r.objection(target, self.proof, 'critic')
        case = self.r.adjudication(finding, self.proof, disposition='scope-classified',
                                   impact='unconditional-truth', author='root')
        tasks = Tasks(self.r)
        example = self.example(target)
        with self.assertRaisesRegex(StateError, 'support/history additions'):
            tasks.create('adjudicator', case, independence='informed', checks=['statement-boundary'],
                         mandate='No mathematical acceptance context', background=[example])
        task = tasks.create('adjudicator', case, independence='informed', checks=['statement-boundary'],
                            mandate='Exact scope only')
        with self.assertRaisesRegex(StateError, 'support/history additions'):
            tasks.extend(task, [example], 'No context-bootstrap through extension')
        other = self.claim('Other target')
        with self.store.transaction():
            bad = self.store.put('objection', {'target': target, 'target_hash': self.store.get(other)['hash'],
                'artifact': self.proof, 'author': 'malformed-import'})
            self.store.decide(bad, 'open', {'reason': 'Malformed imported fixture'})
        bad_case = self.r.adjudication(bad, self.proof, disposition='scope-classified',
                                       impact='unconditional-truth', author='root')
        self.review(bad_case, sorted(self.r._adjudication_checks(self.store.get(bad_case)['data'])), role='adjudicator')
        with self.assertRaises(StateError):
            self.r.adjudicate(bad_case, expected=self.store.revision)
        self.assertTrue(self.r.finding_effects(bad)['statement_scope_hold'])

    def test_response_producer_is_a_known_party_and_its_loss_revokes_certification(self):
        producer_subject = self.r.inference(self.claim('Other exact subject'), [], self.proof, 'worker')
        report = self.review(producer_subject)
        result = self.store.get(report)['data']['provenance']['result']
        producer = self.store.get(report)['data']['reviewer']
        with self.store.transaction():
            response = self.store.put('artifact', {'text': 'Self-contained scope response, synthetic producer fixture',
                                                  'source_result': result})
        finding = self.r.objection(self.claim(), self.proof, 'critic')
        case = self.r.adjudication(finding, response, disposition='scope-classified', impact='unconditional-truth', author='root')
        self.assertIn(producer, self.store.get(case)['data']['parties'])
        self.review(case, sorted(self.r._adjudication_checks(self.store.get(case)['data'])), role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        self.assertFalse(self.r.finding_effects(finding)['statement_scope_hold'])
        self.r.withdraw(result, 'Scope response producer no longer qualified')
        self.assertTrue(self.r.finding_effects(finding)['statement_scope_hold'])


if __name__ == '__main__':
    unittest.main()
