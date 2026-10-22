"""Composition tests for operational disposition, qualification and advice.

Captured reviews/checker outputs are explicit synthetic protocol boundaries.
These tests do not establish mathematical validity or live host guarantees.
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


class ConditionTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    accept = test_research.ResearchTests.accept
    review = test_research.ResearchTests.review

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.o = Orchestration(self.r)
        self.tasks = Tasks(self.r)

    def formal(self):
        source = self.r.artifact('theorem t : True := by trivial')
        plan = Evidence(self.r).formal_plan(self.claim('True'), source, 't', 'True', author='formalizer')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        toolchain = formal_fixture.toolchain(self.r)
        symbol = self.store.get(plan)['data']['check_symbol']
        process = {'exit_code': 0, 'timed_out': False, 'namespace_setup': True, 'output_limited': False}
        checked = formal_fixture.execution(self.r, plan)
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(checked)), \
             patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            receipt = Evidence(self.r).run_lean(plan, toolchain=toolchain)
        return receipt, toolchain

    def lesson(self, source):
        return self.r.learning('Condition-specific research observation', [source],
            category='failed-mechanism', reopen_condition='The recorded evidence condition changes')

    def test_assessment_cannot_dispose_of_qualification_or_hide_subsequent_damage(self):
        receipt, _ = self.formal()
        data = self.store.get(receipt)['data']
        execution = data['execution']
        self.o.assess_execution(execution, 'Process completed; fidelity qualification remains open', [], 'Independent review')
        actions = [a for a in self.o.next_actions()['actions'] if a.get('execution') == execution]
        self.assertEqual([a['action'] for a in actions], ['review-formal-receipt'])
        self.assertFalse(self.r._formal_current(receipt))
        self.assertEqual(self.r.claim_state(data['target'])['state'], 'unsupported')
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.assertTrue(self.r._formal_current(receipt))
        self.assertTrue(any(a.get('receipt') == receipt and a['action'] == 'consider-formal-evidence'
                            for a in self.o.next_actions()['actions']))
        self.o.dispose_formal_evidence(receipt, 'Deliberate non-use of this exact evidence', 'Revisit this formal route')
        self.assertFalse(any(a.get('execution') == execution for a in self.o.next_actions()['actions']))
        self.r.withdraw(data['compiled_artifact'], 'Compiled artifact provenance retracted')
        actions = [a for a in self.o.next_actions()['actions'] if a.get('execution') == execution]
        self.assertEqual([a['action'] for a in actions], ['repair-formal-evidence'])
        self.assertTrue(self.r._review_condition(receipt, {'formal-receipt', 'formal-target-fidelity', 'foundations'})['current'])
        self.assertTrue(any(i['target'] == data['compiled_artifact'] for i in actions[0]['condition']['issues']))

    def test_missing_plan_review_is_distinct_from_missing_receipt_review(self):
        receipt, _ = self.formal()
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        data = self.store.get(receipt)['data']
        plan_review = next(r['id'] for r in self.store.records('review') if r['data']['target'] == data['plan'])
        self.r.withdraw(plan_review, 'Plan fidelity review provenance no longer usable')
        self.o.assess_execution(data['execution'], 'Observed completion', [], 'Plan qualification repaired')
        actions = [a for a in self.o.next_actions()['actions'] if a.get('execution') == data['execution']]
        self.assertEqual([a['action'] for a in actions], ['review-formal-plan'])
        self.assertEqual(actions[0]['target'], data['plan'])

    def test_false_to_false_formal_condition_changes_stale_advice(self):
        receipt, toolchain = self.formal()
        learning = self.lesson(receipt)
        self.assertFalse(self.r._formal_current(receipt))
        self.assertTrue(self.r.learning_current(learning))  # Useful unqualified-evidence lesson.
        self.claim('Unrelated mathematical question')
        self.assertTrue(self.r.learning_current(learning))  # Not tied to global revision.
        self.r.withdraw(toolchain, 'Toolchain provenance compromised')
        self.assertFalse(self.r._formal_current(receipt))
        self.assertFalse(self.r.learning_current(learning))  # Still false, for materially different reasons.
        self.assertEqual(self.store.status(receipt), 'checked')

    def test_exact_candidate_and_publication_lessons_follow_selected_support(self):
        target = self.claim()
        selected = self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        lessons = [self.lesson(source) for source in (candidate, release)]
        alternative = self.accept(target)
        self.assertTrue(all(self.r.learning_current(i) for i in lessons))
        self.r.withdraw(selected, 'Gap in the selected frozen argument')
        self.assertEqual(self.r.claim_state(target)['usable_supports'], [alternative])
        self.assertFalse(self.r.candidate_current(candidate))
        self.assertFalse(self.r.release_current(release))
        self.assertFalse(any(self.r.learning_current(i) for i in lessons))
        self.assertEqual(self.store.status(candidate), 'audited')
        self.assertEqual(self.store.status(release), 'released')

    def test_counterexample_and_application_lessons_follow_derived_dependencies(self):
        target, hypothesis = self.claim(), self.claim('Hypothesis')
        support = self.accept(hypothesis)
        example = self.r.counterexample(target, self.proof, 'hunter', dependencies=[hypothesis])
        self.review(example, ['domain', 'negation', 'scope', 'dependencies'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        theorem = self.r.external_theorem('H implies R', 'Exact synthetic source', self.proof, ['H'], [])
        application = self.r.application(theorem, self.claim('R'), {'H': hypothesis},
            'Exact substitution', self.proof, author='worker')
        self.review(application, ['source', 'hypotheses', 'substitution', 'conclusion'])
        self.r.accept_application(application, expected=self.store.revision)
        lessons = [self.lesson(source) for source in (example, application)]
        self.assertTrue(all(self.r.learning_current(i) for i in lessons))
        self.r.withdraw(support, 'Hypothesis argument lost')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertEqual(self.store.status(example), 'validated')
        self.assertEqual(self.store.status(application), 'accepted')
        self.assertFalse(any(self.r.learning_current(i) for i in lessons))

    def test_learning_admission_checks_own_hold_and_both_extension_paths(self):
        source, target = self.claim('Unresolved mechanism'), self.claim('Research target')
        learning = self.lesson(source)
        task = self.tasks.create('prover', target, checks=['argument'], mandate='Informed research',
            independence='informed', background=[learning])
        self.assertIn('never proof', self.tasks.packet(task)['records'][learning]['advisory']['authority'])
        self.r.objection(learning, self.proof, 'critic')
        self.assertFalse(self.r.learning_current(learning))
        with self.assertRaisesRegex(StateError, 'learning is stale'):
            self.tasks.extend(task, [self.proof], 'Preserve existing background')
        other = self.lesson(source)
        fresh = self.tasks.create('prover', target, checks=['argument'], mandate='Informed research', independence='informed')
        self.accept(source)
        self.assertFalse(self.r.learning_current(other))
        with self.assertRaisesRegex(StateError, 'learning is stale'):
            self.tasks.extend(fresh, [other], 'Add changed historical observation')
        with self.assertRaisesRegex(StateError, 'learning is stale'):
            self.tasks.create('prover', target, checks=['argument'], mandate='Informed research',
                              independence='informed', background=[other])

    def test_unrelated_proposals_do_not_hide_audit_or_open_obligations(self):
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        route = self.r.route(self.claim('Other target'), 'Independent route', family='independent')
        obligation = self.r.obligation(route, 'An exact open mathematical question', claim=self.claim('Open question'))
        proposal = self.r.inference(self.claim('Unrelated proposal'), [], self.proof, 'worker')
        actions = self.o.next_actions()['actions']
        self.assertTrue(any(a['action'] == 'audit' and candidate in a['targets'] for a in actions))
        self.assertTrue(any(a['action'] == 'research-obligations' and obligation in a['targets'] for a in actions))
        self.assertTrue(any(a.get('target') == proposal and a['action'] == 'evaluate-inference-for-promotion' for a in actions))

    def test_direct_review_lesson_stales_when_independence_is_lost(self):
        target = self.claim()
        inference = self.r.inference(target, [], self.proof, 'worker')
        review = self.review(inference)
        learning = self.lesson(review)
        self.assertTrue(self.r.learning_current(learning))
        self.tasks.expose(self.store.get(review)['data']['run_id'], 'other-verdict', self.proof,
                          'Previously unrecorded peer-verdict exposure')
        self.assertEqual(self.store.status(review), 'proposed')
        self.assertFalse(self.r.learning_current(learning))
        with self.assertRaisesRegex(StateError, 'learning is stale'):
            self.tasks.create('prover', target, checks=['argument'], mandate='Informed research',
                              independence='informed', background=[learning])

    def test_dismissal_lessons_follow_the_exact_adjudication_witnesses(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'critic')
        case = self.r.adjudication(finding, self.proof, disposition='dismissed', author='root')
        witness = self.review(case, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        resolution = self.r.adjudicate(case, expected=self.store.revision)
        lessons = [self.lesson(source) for source in (finding, case, resolution)]
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(all(self.r.learning_current(i) for i in lessons))
        self.r.withdraw(witness, 'Adjudicator provenance no longer usable')
        self.assertEqual(self.store.status(finding), 'dismissed')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertFalse(any(self.r.learning_current(i) for i in lessons))
        self.review(case, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertFalse(any(self.r.learning_current(i) for i in lessons))

    def test_qualified_formal_evidence_has_a_separate_use_or_defer_frontier(self):
        receipt, _ = self.formal()
        data = self.store.get(receipt)['data']
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.o.assess_execution(data['execution'], 'Actual checked output assessed', [], 'Mathematical incorporation')
        disposition = self.o.dispose_formal_evidence(receipt, 'Defer this exact route', 'New route insight')
        self.assertEqual(disposition, self.o.dispose_formal_evidence(receipt, 'Defer this exact route', 'New route insight'))
        self.assertFalse(disposition['mathematical_acceptance'])
        portfolio = self.r.portfolio(data['target'])
        self.assertTrue(portfolio['dispositions'][-1]['disposition_current'])
        self.assertEqual(self.r.claim_state(data['target'])['state'], 'unsupported')
        inference = self.r.inference(data['target'], [], self.proof, 'worker', assurance='formal', formal_receipt=receipt)
        actions = self.o.next_actions()['actions']
        self.assertFalse(any(a['action'] == 'consider-formal-evidence' and a.get('receipt') == receipt for a in actions))
        self.assertTrue(any(a.get('target') == inference and a['action'] == 'evaluate-inference-for-promotion' for a in actions))
        with self.assertRaisesRegex(StateError, 'active mathematical route'):
            self.o.dispose_formal_evidence(receipt, 'Try to hide a pending route', 'Later')
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='use-formal-receipt')
        self.r.withdraw(inference, 'This incorporation route was abandoned')
        actions = self.o.next_actions()['actions']
        self.assertTrue(any(a['action'] == 'consider-formal-evidence' and a.get('receipt') == receipt for a in actions))
        self.assertFalse(self.r.portfolio(data['target'])['dispositions'][-1]['disposition_current'])

    def test_result_and_generated_artifact_advice_follow_run_exposure(self):
        inference = self.r.inference(self.claim(), [], self.proof, 'worker')
        review = self.review(inference)
        provenance = self.store.get(review)['data']['provenance']
        result = provenance['result']
        with self.store.transaction():
            derived = self.store.put('artifact', {'text': 'Root-retained result projection', 'source_result': result})
        sources = [self.store.get(review)['data']['run_id'], result, derived]
        lessons = [self.lesson(source) for source in sources]
        self.assertTrue(all(self.r.learning_current(i) for i in lessons))
        self.tasks.expose(sources[0], 'other-verdict', self.proof, 'Observed peer exposure')
        self.assertFalse(any(self.r.learning_current(i) for i in lessons))

    def test_defer_basis_includes_target_state_and_exact_rationale_sources(self):
        receipt, _ = self.formal()
        target = self.store.get(receipt)['data']['target']
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        informal = self.accept(target)
        self.o.dispose_formal_evidence(receipt, 'An independent informal route establishes the target',
                                      'The target loses support')
        self.r.withdraw(informal, 'Last informal argument was invalid')
        self.assertTrue(self.r._formal_current(receipt))
        self.assertTrue(any(a['action'] == 'consider-formal-evidence' and a.get('receipt') == receipt
                            for a in self.o.next_actions()['actions']))
        rationale = self.r.artifact('Exact scientific rationale for deferral')
        self.o.dispose_formal_evidence(receipt, 'Defer according to an exact rationale', 'Rationale changes',
                                      basis_sources=[rationale])
        self.r.withdraw(rationale, 'Rationale provenance retracted')
        self.assertTrue(any(a['action'] == 'consider-formal-evidence' and a.get('receipt') == receipt
                            for a in self.o.next_actions()['actions']))
        with self.assertRaisesRegex(StateError, 'exact list'):
            self.o.dispose_formal_evidence(receipt, 'No container coercion', 'Later', basis_sources={rationale: True})

    def test_incomplete_adjudication_and_candidate_bases_track_partial_changes(self):
        target = self.claim()
        self.accept(target)
        finding = self.r.objection(target, self.proof, 'critic')
        first = self.r.adjudication(finding, self.proof, disposition='dismissed', author='root')
        response = self.r.artifact('Second proposed response')
        self.r.adjudication(finding, response, disposition='dismissed', author='root')
        self.r.objection(response, self.proof, 'challenge-one')
        lesson = self.lesson(first)
        self.assertFalse(self.r._adjudication_current(first))
        self.r.objection(response, self.proof, 'challenge-two')
        self.assertFalse(self.r._adjudication_current(first))
        self.assertFalse(self.r.learning_current(lesson))
        clean = self.claim('Independent supported result')
        self.accept(clean)
        candidate = self.r.freeze(clean, self.proof, author='author')
        self.review(candidate, ['full-proof', 'dependency-closure'], role='fidelity-auditor')
        lesson = self.lesson(candidate)
        before = self.r._candidate_review_condition(candidate)
        self.review(candidate, ['full-proof', 'dependency-closure'])
        after = self.r._candidate_review_condition(candidate)
        self.assertFalse(before['current'])
        self.assertFalse(after['current'])
        self.assertEqual(before['missing'], after['missing'])
        self.assertNotEqual(before['missing_responsibilities'], after['missing_responsibilities'])
        self.assertFalse(self.r.learning_current(lesson))


if __name__ == '__main__':
    unittest.main()
