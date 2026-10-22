"""Protocol/grounding scenarios; synthetic reviews do not prove mathematics."""
import unittest

import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.store import StateError
from mathtrace.witness import nodes, roots


class EvaluationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def example(self, target, dependencies=None, artifact=None):
        identifier = self.r.counterexample(target, artifact or self.proof, 'hunter', dependencies=dependencies)
        checks = ['domain', 'negation', 'scope'] + (['dependencies'] if dependencies else [])
        self.review(identifier, checks)
        self.r.validate_counterexample(identifier, expected=self.store.revision)
        return identifier

    def test_refutation_dependencies_are_and_with_or_support_and_frozen_choices(self):
        target, lemma, missing = self.claim('T'), self.claim('L'), self.claim('Missing')
        first, second = self.accept(lemma), self.accept(lemma)
        bad = self.r.counterexample(target, self.proof, 'hunter', dependencies=[lemma, missing])
        self.review(bad, ['domain', 'negation', 'scope', 'dependencies'])
        with self.assertRaises(StateError):
            self.r.validate_counterexample(bad, expected=self.store.revision)
        example = self.example(target, [lemma])
        candidate = self.r.freeze(target, self.proof, author='hunter', outcome='disproof')
        frozen = self.store.get(candidate)['data']
        self.assertEqual(roots(frozen['derivation']['witness'])[0]['inference'], first)
        self.assertIn(first, frozen['manifest'])
        self.r.withdraw(first, 'First proof fails')
        self.assertEqual(self.r.claim_state(target)['refutations'], [example])
        self.assertFalse(self.r.candidate_current(candidate))
        self.r.withdraw(second, 'Last proof fails')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertEqual(self.store.status(example), 'validated')

    def test_dependency_scope_and_completeness_are_required(self):
        target, lemma = self.claim(), self.claim('L')
        assumption = self.r.assumption('A')
        self.accept(lemma, assumptions=[assumption])
        example = self.r.counterexample(target, self.proof, 'hunter', dependencies=[lemma])
        self.review(example, ['domain', 'negation', 'scope'])
        with self.assertRaisesRegex(StateError, 'coverage'):
            self.r.validate_counterexample(example, expected=self.store.revision)
        self.review(example, ['dependencies'])
        with self.assertRaisesRegex(StateError, 'unconditional'):
            self.r.validate_counterexample(example, expected=self.store.revision)
        before = self.store.revision
        for invalid in [{lemma: True}, lemma, [lemma, lemma], [0], ['']]:
            with self.assertRaises(StateError):
                self.r.counterexample(target, self.proof, 'hunter', dependencies=invalid)
        self.assertEqual(self.store.revision, before)

    def test_refutation_cannot_ground_itself_through_its_target(self):
        a, b = self.claim('A'), self.claim('B')
        self.accept(a)
        self.accept(b, [a])
        for dependency in [a, b]:
            example = self.r.counterexample(a, self.proof, 'hunter', dependencies=[dependency])
            self.review(example, ['domain', 'negation', 'scope', 'dependencies'])
            with self.assertRaisesRegex(StateError, 'independent'):
                self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(a)['state'], 'supported')

    def test_alternative_loss_can_create_nonmonotonic_evidence_cycle(self):
        a, b, d = self.claim('A'), self.claim('B'), self.claim('D')
        self.accept(a)
        self.accept(b)
        direct_d = self.accept(d)
        ea = self.example(a, [b])
        eb = self.example(b, [d])
        self.assertEqual(self.r.claim_state(b)['refutations'], [eb])
        self.assertEqual(self.r.claim_state(a)['state'], 'supported')
        self.accept(d, [a])
        self.r.withdraw(direct_d, 'Independent grounding lost')
        for claim in [a, b]:
            view = self.r.claim_state(claim)
            self.assertEqual(view['state'], 'suspended')
            self.assertEqual(view['refutations'], [])
            self.assertEqual(view['usable_supports'], [])
            self.assertEqual(view['unresolved_refutations'], [ea] if claim == a else [eb])
            with self.assertRaises(StateError):
                self.r.freeze(claim, self.proof, author='root')
        self.assertEqual(self.r.claim_state(a, policy='formal-only')['state'], 'suspended')
        self.assertEqual(self.r.progress()['next']['action'], 'investigate-refutation-cycle')

    def test_ambient_assumption_does_not_launder_disputed_unconditional_proof(self):
        p = self.claim('P')
        a = self.r.assumption('A')
        unconditional = self.accept(p)
        conditional = self.accept(p, assumptions=[a])
        self.example(p)
        self.assertEqual(self.r.claim_state(p)['state'], 'conflict')
        self.assertEqual(self.r.eligible_supports(p, {a}), [conditional])
        self.assertNotIn(unconditional, self.r.eligible_supports(p, {a}))
        fresh = self.r.inference(p, [], self.proof, 'author', discharge=[a], rule='contradiction')
        self.review(fresh, ['validity', 'scope', 'dependencies', 'discharge'])
        with self.assertRaisesRegex(StateError, 'negative evidence'):
            self.r.promote(fresh, expected=self.store.revision, request_id='discharge-is-not-output-assumption')

    def test_scoped_contradiction_uses_explicit_negation_proof_and_freezes_exactly(self):
        p, not_p, not_a = self.claim('P'), self.claim('not P'), self.claim('not A')
        a = self.r.assumption('A')
        conditional = self.accept(p, assumptions=[a])
        negative_source = self.r.artifact('Complete independent argument establishing not P; fixture source.')
        # Mathematical argument, not the counterexample's validation status, is
        # consumed through a separately reviewed exact negation claim.
        negation = self.r.inference(not_p, [], negative_source, 'hunter')
        self.review(negation)
        self.r.promote(negation, expected=self.store.revision, request_id='negation-proof')
        self.example(p, artifact=negative_source)
        inference = self.r.inference(not_a, [p, not_p], self.proof, 'author',
            discharge=[a], rule='contradiction')
        self.review(inference, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(inference, expected=self.store.revision, request_id='legitimate-contradiction')
        self.assertEqual(self.r.claim_state(not_a)['state'], 'supported')
        candidate = self.r.freeze(not_a, self.proof, author='author')
        self.assertTrue(self.r.candidate_current(candidate))
        forest = self.store.get(candidate)['data']['derivation']['witness']
        self.assertEqual(nodes(forest)[roots(forest)[0]['premises'][0]]['inference'], conditional)
        self.r.withdraw(conditional, 'Conditional route withdrawn')
        self.accept(p, assumptions=[a])
        self.assertEqual(self.r.claim_state(not_a)['state'], 'supported')
        self.assertFalse(self.r.candidate_current(candidate))
        replacement = self.r.freeze(not_a, self.proof, author='author')
        self.r.withdraw(negative_source, 'Actual negation proof source withdrawn')
        self.assertFalse(self.r.candidate_current(replacement))
        self.assertEqual(self.r.claim_state(not_a)['state'], 'unsupported')

    def test_nested_discharge_and_environment_weakening_keep_exact_scope(self):
        a, b = self.r.assumption('A'), self.r.assumption('B')
        p, q, result = self.claim('P'), self.claim('Q'), self.claim('Result')
        self.accept(p, assumptions=[a, b])
        self.assertEqual(self.r.eligible_supports(p, {a}), [])
        intermediate = self.r.inference(q, [p], self.proof, 'author', assumptions=[b],
                                        discharge=[a], rule='scoped-derivation')
        self.review(intermediate, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(intermediate, expected=self.store.revision, request_id='inner-discharge')
        outer = self.r.inference(result, [q], self.proof, 'author', discharge=[b], rule='scoped-derivation')
        self.review(outer, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(outer, expected=self.store.revision, request_id='outer-discharge')
        candidate = self.r.freeze(result, self.proof, author='author')
        self.assertTrue(self.r.candidate_current(candidate))

    def test_repeated_claim_is_grounded_only_by_distinct_finite_inference_anchor(self):
        a, b = self.claim('A'), self.claim('B')
        anchor = self.accept(a)
        self.accept(b, [a])
        rederived = self.accept(a, [b])
        self.assertIn(rederived, self.r.eligible_supports(a))
        self.r.withdraw(anchor, 'Only anchor withdrawn')
        self.assertEqual(self.r.claim_state(a)['state'], 'unsupported')
        self.assertEqual(self.r.claim_state(b)['state'], 'unsupported')

    def test_counterexample_context_contains_exact_dependency_claims(self):
        target, lemma = self.claim('T'), self.claim('L')
        support = self.accept(lemma)
        example = self.r.counterexample(target, self.proof, 'hunter', dependencies=[lemma])
        task = Tasks(self.r).create('referee', example, checks=['domain', 'negation', 'scope', 'dependencies'],
                                   mandate='Audit complete refutation and declared dependency use')
        packet = Tasks(self.r).packet(task)
        self.assertIn(lemma, packet['records'])
        self.assertIn(support, packet['records'])
        self.assertEqual(roots(packet['dependency_evidence']['selected'])[0]['inference'], support)
        self.assertEqual(packet['dependency_evidence']['missing'], [])

    def test_scope_queries_reject_malformed_or_unregistered_environments(self):
        p, a = self.claim(), self.r.assumption('A')
        self.accept(p, assumptions=[a])
        for invalid in [{a: False}, a, False, [0], ['unregistered-assumption']]:
            with self.assertRaises(StateError):
                self.r.claim_state(p, invalid)
            with self.assertRaises(StateError):
                self.r.derivations(p, invalid)
        self.assertEqual(self.r.claim_state(p, [a])['state'], 'supported')

    def test_imported_counterexamples_revalidate_exact_dependency_contract(self):
        target, lemma = self.claim('T'), self.claim('L')
        self.accept(lemma)
        tasks = Tasks(self.r)
        original = tasks.create('referee', target, checks=['scope'], mandate='Original context', independence='informed')
        for dependencies in ([lemma, lemma], None, lemma, [self.proof], [{}], ['missing-claim']):
            with self.store.transaction():
                example = self.store.put('counterexample', {'target': target, 'artifact': self.proof,
                    'author': 'imported', 'formal_receipt': None, 'dependencies': dependencies})
            # The use boundary rejects an imported proposal before scope walking.
            with self.assertRaises(StateError):
                self.r.validate_counterexample(example, expected=self.store.revision)
            with self.assertRaises(StateError):
                Tasks(self.r).create('referee', example, checks=['domain', 'negation', 'scope', 'dependencies'],
                                     mandate='Review imported exact dependency evidence')
            with self.store.transaction():
                import copy
                historical = copy.deepcopy(self.store.get(original)['data'])
                historical['packet']['records'][example] = self.store.get(example)
                legacy = self.store.put('task', historical)
            with self.assertRaises(StateError):
                tasks.extend(legacy, [self.proof], 'Continue historical context')
            # A historical/imported validated flag must not manufacture eligibility.
            with self.store.transaction():
                self.store.decide(example, 'validated', {'reason': 'imported historical flag'})
            self.assertEqual(self.r.claim_state(target)['refutations'], [])
            with self.assertRaises(StateError):
                self.r.freeze(target, self.proof, author='hunter', outcome='disproof')

    def test_target_occurrence_inside_discharge_is_not_an_unconditional_self_dependency(self):
        p, negation = self.claim('False'), self.claim('not False')
        hypothesis = self.r.assumption('Assume False temporarily')
        self.accept(p, assumptions=[hypothesis])
        proof = self.r.inference(negation, [p], self.proof, 'author', discharge=[hypothesis], rule='contradiction')
        self.review(proof, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(proof, expected=self.store.revision, request_id='negation-by-assumption-discharge')
        example = self.example(p, [negation])
        self.assertEqual(self.r.claim_state(p)['refutations'], [example])
        self.assertEqual(self.r.claim_state(negation)['state'], 'supported')
        candidate = self.r.freeze(p, self.proof, author='hunter', outcome='disproof')
        self.assertTrue(self.r.candidate_current(candidate))


if __name__ == '__main__':
    unittest.main()
