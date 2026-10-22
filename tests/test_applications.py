"""Rule qualification versus actual scoped premise grounding.

Captured assessments are synthetic protocol evidence, not theorem validity.
"""
import unittest

import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.store import StateError
from mathtrace.witness import nodes, roots


class ApplicationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def proposed_application(self, hypothesis, target):
        theorem = self.r.external_theorem('T whenever H, with all source conditions stated',
            'Exact source/version fixture', self.proof, ['H'], [])
        return self.r.application(theorem, target, {'H': hypothesis},
                                  'Complete exact domain/substitution fixture', self.proof, 'author')

    def qualify(self, application):
        self.review(application, ['source', 'hypotheses', 'substitution', 'conclusion'], role='theorem-checker')
        self.r.accept_application(application, expected=self.store.revision)

    def test_rule_can_qualify_before_support_then_ground_only_under_exact_assumptions(self):
        hypothesis, target, discharged = [self.claim(x) for x in ['H', 'T', 'A implies T']]
        application = self.proposed_application(hypothesis, target)
        tasks = Tasks(self.r)
        task = tasks.create('theorem-checker', application,
            checks=['source', 'hypotheses', 'substitution', 'conclusion'], mandate='Check exact conditional instantiation')
        packet = tasks.packet(task)
        self.assertEqual(packet['application_contract']['mapped_premises'], [hypothesis])
        self.assertIn('no conclusion or antecedent', packet['application_contract']['qualification'])
        self.qualify(application)
        self.assertTrue(self.r._application_current(application))
        self.assertEqual(self.r.claim_state(hypothesis)['state'], 'unsupported')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        unsupported = self.r.inference(target, [], self.proof, 'author', applications=[application])
        self.assertEqual(self.store.get(unsupported)['data']['premises'], [hypothesis])
        self.review(unsupported)
        with self.assertRaises(StateError):
            self.r.promote(unsupported, expected=self.store.revision, request_id='rule-does-not-prove-H')
        assumption = self.r.assumption('A')
        self.accept(hypothesis, assumptions=[assumption])
        with self.assertRaises(StateError):
            self.r.promote(unsupported, expected=self.store.revision, request_id='conditional-H-is-not-unconditional')
        scoped = self.r.inference(target, [], self.proof, 'author', assumptions=[assumption], applications=[application])
        self.review(scoped)
        self.r.promote(scoped, expected=self.store.revision, request_id='scoped-external-rule')
        self.assertEqual(self.r.eligible_supports(target, {assumption}), [scoped])
        self.assertEqual(self.r.eligible_supports(target), [])
        with self.assertRaises(StateError):
            self.r.freeze(target, self.proof, author='root')
        outer = self.r.inference(discharged, [target], self.proof, 'author', discharge=[assumption],
                                 rule='implication-introduction')
        self.review(outer, ['validity', 'scope', 'dependencies', 'discharge'])
        self.r.promote(outer, expected=self.store.revision, request_id='explicit-external-discharge')
        candidate = self.r.freeze(discharged, self.proof, author='root')
        self.assertTrue(self.r.candidate_current(candidate))
        manifest = self.store.get(candidate)['data']['manifest']
        self.assertIn(application, manifest)
        self.assertIn(assumption, manifest)
        self.r.withdraw(assumption, 'Local hypothesis scope was wrong')
        self.assertFalse(self.r.candidate_current(candidate))

    def test_refuted_antecedent_remains_an_unconditional_veto_for_a_qualified_rule(self):
        hypothesis, target = self.claim('H'), self.claim('T')
        unconditional = self.accept(hypothesis)
        assumption = self.r.assumption('A')
        conditional = self.accept(hypothesis, assumptions=[assumption])
        example = self.r.counterexample(hypothesis, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(hypothesis)['state'], 'conflict')
        application = self.proposed_application(hypothesis, target)
        self.qualify(application)
        bad = self.r.inference(target, [], self.proof, 'author', applications=[application])
        self.review(bad)
        with self.assertRaises(StateError):
            self.r.promote(bad, expected=self.store.revision, request_id='rule-cannot-ignore-negation')
        scoped = self.r.inference(target, [], self.proof, 'author', assumptions=[assumption], applications=[application])
        self.review(scoped)
        self.r.promote(scoped, expected=self.store.revision, request_id='legitimate-conditional-rule')
        forest = self.r.derivations(target, {assumption})[0]
        child = nodes(forest)[roots(forest)[0]['premises'][0]]
        self.assertEqual(child['inference'], conditional)
        self.assertNotEqual(child['inference'], unconditional)
        self.assertEqual(self.r.eligible_supports(target), [])

    def test_unresolved_statement_source_and_rule_objections_still_prevent_qualification(self):
        hypothesis, target = self.claim('H'), self.claim('T')
        source_application = self.proposed_application(hypothesis, target)
        theorem = self.store.get(source_application)['data']['theorem']
        self.r.withdraw(theorem, 'Source theorem retracted')
        self.review(source_application, ['source', 'hypotheses', 'substitution', 'conclusion'], role='theorem-checker')
        with self.assertRaises(StateError):
            self.r.accept_application(source_application, expected=self.store.revision)
        rule_application = self.proposed_application(hypothesis, target)
        self.review(rule_application, ['source', 'hypotheses', 'substitution', 'conclusion'], role='theorem-checker')
        self.r.objection(rule_application, self.proof, 'critic')
        with self.assertRaises(StateError):
            self.r.accept_application(rule_application, expected=self.store.revision)
        statement_application = self.proposed_application(hypothesis, target)
        self.review(statement_application, ['source', 'hypotheses', 'substitution', 'conclusion'], role='theorem-checker')
        self.r.objection(hypothesis, self.proof, 'scope-auditor')
        with self.assertRaises(StateError):
            self.r.accept_application(statement_application, expected=self.store.revision)


if __name__ == '__main__':
    unittest.main()
