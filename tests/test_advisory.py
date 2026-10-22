"""Synthetic coordination checks, with no mathematical or live host authority."""
import unittest
from copy import deepcopy

import test_research
from mathtrace.advisory import Advisory
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class AdvisoryTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    accept = test_research.ResearchTests.accept
    review = test_research.ResearchTests.review

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.a = Advisory(self.r)
        self.target = self.claim()
        self.route = self.r.route(self.target, 'Independent route', family='direct')

    def transition(self, **changes):
        args = dict(route=self.route, status='blocked', certificate=self.proof, sources=[self.target],
            rationale='Exact unresolved estimate; no mathematical refutation', reopen_condition='A new bound resolves it',
            author='root', expected=self.store.revision, previous_decision=self.a.condition(self.route)['decision_hash'],
            request_id='transition-one')
        args.update(changes)
        return self.a.transition(**args)

    def test_route_decision_is_immediately_current_and_replay_preserves_history(self):
        original = self.a.condition(self.route)['decision_hash']
        result = self.transition(previous_decision=original)
        self.assertTrue(result['current'])
        self.assertEqual(self.r.claim_state(self.target)['state'], 'unsupported')
        Orchestration(self.r).checkpoint('Unrelated checkpoint')
        replay = self.transition(previous_decision=original, expected=0)
        self.assertEqual(replay['certificate'], result['certificate'])
        self.assertTrue(replay['current'])
        self.accept(self.target)
        self.assertFalse(self.a.condition(self.route)['current'])
        self.assertEqual(self.store.status(self.route), 'blocked')

    def test_direct_and_transitive_self_basis_rejected_but_historical_boundary_is_allowed(self):
        with self.assertRaises(StateError):
            self.transition(sources=[self.route])
        other = self.r.route(self.target, 'Second route', family='other')
        result = self.transition(route=other, sources=[self.route],
            previous_decision=self.a.condition(other)['decision_hash'])
        with self.assertRaises(StateError):
            self.transition(sources=[result['certificate']], request_id='indirect')
        old = self.a._latest(self.route)
        boundary = self.a.boundary(old['revision'], old['hash'], target=self.route)
        self.assertTrue(self.transition(sources=[boundary], request_id='historical')['current'])

    def test_legacy_status_needs_explicit_source_bound_reclassification_without_closing_obligations(self):
        obligation = self.r.obligation(self.route, 'Comparable-strength unresolved statement',
            claim=self.claim('Q'), relation='comparable-strength-residual', relation_artifact=self.proof)
        self.r.route_status(self.route, 'closed', self.proof, reopen_condition='Historical unbound certificate')
        condition = self.a.condition(self.route)
        self.assertTrue(condition['needs_reclassification'])
        self.assertFalse(condition['current'])
        self.assertTrue(self.r.obligation_open(self.store.get(obligation)))
        revised = self.transition(status='dormant')
        self.assertTrue(revised['current'])
        self.assertTrue(self.r.obligation_open(self.store.get(obligation)))
        packet = Tasks(self.r).packet(Orchestration(self.r).strategize(self.target))
        self.assertIn(revised['certificate'], packet['records'])
        self.assertTrue(packet['records'][revised['certificate']]['data']['basis']['omitted'])

    def test_boundary_constructor_and_reader_reject_forged_event_addresses(self):
        event = self.a._latest(self.route)
        with self.assertRaises(StateError):
            self.a.boundary(event['revision'], 'forged', target=self.route)
        with self.assertRaises(StateError):
            self.a.boundary(event['revision'], event['hash'], target=self.target)
        boundary = self.a.boundary(event['revision'], event['hash'], target=self.route)
        self.assertEqual(self.a.boundary(event['revision'], event['hash'], target=self.route), boundary)
        data = deepcopy(self.store.get(boundary)['data'])
        data['event']['payload']['status'] = 'forged'
        with self.store.transaction():
            bad = self.store.put('boundary_certificate', data)
        with self.assertRaises(StateError):
            self.a.boundary_data(bad)

    def test_obligation_mapping_supplies_actual_T_Q_without_route_narrative(self):
        q = self.claim('Exact residual Q')
        obligation = self.r.obligation(self.route, 'Q is the exact residual for this selected route', claim=q,
            relation='heuristic-reduction', relation_artifact=self.proof)
        task = Tasks(self.r).create('theorem-checker', obligation, checks=['obligation-mapping'],
            mandate='Assess exact mapping independently')
        packet = Tasks(self.r).packet(task)
        self.assertIn(self.target, packet['records'])
        self.assertIn(q, packet['records'])
        self.assertNotIn(self.route, packet['records'])
        self.accept(q)
        self.review(obligation, ['obligation-mapping'])
        self.r.close_obligation(obligation, expected=self.store.revision)
        self.assertFalse(self.r.obligation_open(self.store.get(obligation)))
        self.r.withdraw(self.proof, 'Mapping evidence withdrawn')
        self.assertTrue(self.r.obligation_open(self.store.get(obligation)))

    def test_typed_boundary_targets_and_malformed_imported_route_decisions_fail_closed(self):
        with self.store.transaction():
            seq = self.store.event('completion-qualification', self.target, {'captured': True, 'result': self.target})
        event_hash = self.store.db.execute('SELECT hash FROM events WHERE seq=?', (seq,)).fetchone()['hash']
        with self.assertRaises(StateError):
            self.a.boundary(seq, event_hash, target=self.target)
        correct = self.transition()['certificate']
        data = deepcopy(self.store.get(correct)['data'])
        data['status'], data['artifact'] = 'bogus', self.route
        data['sources'] *= 2
        with self.store.transaction():
            malformed = self.store.put('route_decision', data)
            self.store.decide(self.route, 'bogus', {'certificate': malformed, 'profile': data['profile']})
        self.assertFalse(self.a.condition(self.route)['current'])
        with self.store.transaction():
            obligation = self.store.put('obligation', {'route': 'missing-route', 'claim': self.target, 'statement': 'Malformed residual'})
            self.store.decide(obligation, 'satisfied', {'reason': 'Imported malformed fixture'})
        self.assertTrue(self.r.obligation_open(self.store.get(obligation)))
        self.assertIn(obligation, self.r.progress()['open_obligations'])

    def test_orphan_decision_and_unfinished_completion_are_not_authentic_boundaries(self):
        with self.store.transaction():
            seq = self.store.event('decision', self.route, {'status': 'blocked', 'reason': {'reason': 'Unprojected event'}})
        event_hash = self.store.db.execute('SELECT hash FROM events WHERE seq=?', (seq,)).fetchone()['hash']
        with self.assertRaises(StateError):
            self.a.boundary(seq, event_hash, target=self.route)
        task = Tasks(self.r).create('scout', self.target, checks=['exploration'], mandate='Exact exploration')
        run = Tasks(self.r).start(task, 'unfinished', host='antigravity', dispatch_evidence=self.proof,
            tools=[], inherited_history=False)
        with self.store.transaction():
            result = self.store.put('result', {'run': run, 'task': task})
            seq = self.store.event('completion-qualification', run, {'captured': True, 'result': result})
        event_hash = self.store.db.execute('SELECT hash FROM events WHERE seq=?', (seq,)).fetchone()['hash']
        with self.assertRaises(StateError):
            self.a.boundary(seq, event_hash, target=run)
