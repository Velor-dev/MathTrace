import json
import unittest
from unittest.mock import patch

import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.coordination import Coordination
from mathtrace.native_capture import NativeCapture
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class CoordinationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.co = Coordination(self.r)
        self.target = self.claim()

    def prepare(self, **changes):
        args = dict(target=self.target, key='discover:' + self.target, instance='one',
            work_target=self.target, role='scout', checks=['exploration'], mandate='Explore exact claim independently',
            rationale='Root portfolio selection; do not export this rationale', expected=self.store.revision,
            request_id='prepare-one')
        args.update(changes)
        return self.co.prepare_work(**args)

    def completed_context(self, intent):
        task = intent['task']
        packet = Tasks(self.r).packet(task)
        child = 'synthetic-native-child-' + task
        capture = self.r.artifact(json.dumps({'kind': 'native-dispatch-capture', 'task_id': task,
            'packet_hash': packet['packet_hash'], 'conversation_id': child,
            'host': 'antigravity', 'declared_tools': [], 'declared_inherited_history': False}))
        run = Tasks(self.r)._start_captured(task, child, host='antigravity', dispatch_evidence=capture,
                                          tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': packet['packet_hash'],
            'outcome': 'context-request', 'requested_context': ['An exact definition is required'],
            'reasoning': 'Synthetic context protocol fixture, not a live host execution'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': child, 'status': 'SUCCESS', 'response': output}))
        result = Tasks(self.r)._finish_captured(run, artifact, receipt, outcome='context-request')
        Orchestration(self.r).ingest(result)
        return result

    def test_work_identity_survives_checkpoint_and_replay_retains_changed_specification(self):
        first = self.prepare()
        self.assertTrue(first['current']['basis_unchanged'])
        packet = Tasks(self.r).packet(first['task'])
        self.assertNotIn('Root portfolio selection', json.dumps(packet))
        Orchestration(self.r).checkpoint('Unrelated bookkeeping checkpoint')
        second = self.prepare(request_id='new-request', expected=0)
        self.assertEqual(second['intent'], first['intent'])
        self.assertEqual(second['observation'], 'unchanged-work-recovery')
        changed = self.prepare(request_id='changed-spec', mandate='Different exact work')
        self.assertEqual(changed['observation'], 'reassessment-required')
        self.assertFalse(changed['specification_matches'])
        replay = self.prepare(request_id='changed-spec', mandate='Different exact work', expected=0)
        self.assertEqual(replay['observation'], 'reassessment-required')
        self.assertNotIn('reserve', replay['current']['next_operation'])
        self.assertEqual(len(self.store.records('task')), 1)

    def test_relevant_roster_change_reopens_work_without_creating_another_attempt(self):
        selectors = [{'kind': 'target-roster', 'target': self.target, 'categories': ['route', 'obligation']}]
        intent = self.prepare(role='strategist', independence='informed', selectors=selectors)
        self.assertTrue(intent['current']['basis_unchanged'])
        other = self.claim('Other unrelated target')
        self.r.route(other, 'Unrelated route', family='other')
        self.assertTrue(self.co.inspect_work(intent['intent'])['basis_unchanged'])
        self.r.route(self.target, 'Relevant route', family='bound')
        result = self.prepare(role='strategist', independence='informed', selectors=selectors, request_id='roster-change')
        self.assertEqual(result['observation'], 'reassessment-required')
        self.assertFalse(result['current']['basis_unchanged'])
        self.assertEqual(len(self.store.records('work_intent')), 1)

    def test_default_strategy_basis_covers_actual_portfolio_and_meaningful_dispositions(self):
        first = self.prepare(role='strategist', independence='informed')
        self.r.route(self.target, 'New material route', family='bound')
        self.assertFalse(self.co.inspect_work(first['intent'])['basis_unchanged'])
        fresh = self.prepare(key='strategy-after-route', role='strategist', independence='informed', request_id='after-route')
        self.assertTrue(fresh['current']['basis_unchanged'])
        task = Tasks(self.r).create('prover', self.target, checks=['argument'], mandate='Partial attempt')
        child = 'operator-partial-' + task
        run = Tasks(self.r).start(task, child, host='antigravity', dispatch_evidence=self.proof, tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': Tasks(self.r).packet(task)['packet_hash'],
                             'outcome': 'inconclusive', 'reasoning': 'Unsuccessful estimate'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': child, 'status': 'SUCCESS', 'response': output}))
        result = Tasks(self.r).finish(run, artifact, receipt, outcome='inconclusive')
        Orchestration(self.r).ingest(result)
        self.assertTrue(self.co.inspect_work(fresh['intent'])['basis_unchanged'])
        Orchestration(self.r).dispose_result(result, 'Residual estimate failed', [], 'A new estimate')
        self.assertFalse(self.co.inspect_work(fresh['intent'])['basis_unchanged'])

    def test_reserved_withdrawn_work_stays_visible_and_parallel_work_never_closes_it(self):
        first = self.prepare()
        NativeCapture(self.r).reserve([first['task']], '11111111-1111-4111-8111-111111111111')
        self.r.withdraw(first['task'], 'Retire this task without assuming that the child stopped')
        current = self.co.inspect_work(first['intent'])
        self.assertTrue(current['unknown_attempt'])
        self.assertFalse(current['retry_authorized'])
        frontier = self.co.frontier(self.target)
        self.assertTrue(any(i['action'] == 'inspect-native-allocation' for i in frontier['items']))
        with self.assertRaises(StateError):
            self.prepare(instance='successor', request_id='unknown-successor', relationship='successor',
                         parent_intent=first['intent'], purpose='Attempt replacement', source=first['task'])
        parallel = self.prepare(instance='independent-two', request_id='parallel', relationship='parallel',
            parent_intent=first['intent'], purpose='Complementary independent exploration while old allocation is unknown')
        self.assertNotEqual(parallel['task'], first['task'])
        self.assertTrue(self.co.inspect_work(first['intent'])['unknown_attempt'])

    def test_frontier_keeps_repair_discovery_and_falsification_simultaneous(self):
        self.r.objection(self.target, self.proof, 'critic')
        frontier = self.co.frontier(self.target)
        actions = {i['action'] for i in frontier['items']}
        self.assertIn('independent-discovery', actions)
        self.assertIn('independent-falsification', actions)
        self.assertTrue(any('adjudicat' in a for a in actions))
        self.assertFalse(next(i for i in frontier['items'] if i['action'] == 'independent-discovery')['permission']['packet_allowed'])
        self.assertFalse(frontier['solved'])

    def test_blind_linked_subclaim_excludes_route_rationale_and_owned_unknown_attempt_survives_satisfaction(self):
        q = self.claim('Exact residual Q')
        route = self.r.route(self.target, 'Secret selected route rationale', family='reduction')
        obligation = self.r.obligation(route, 'Q would discharge this exact residual', claim=q)
        work = self.prepare(key='custom-residual', work_target=q, anchors={'route': route, 'obligation': obligation})
        packet = Tasks(self.r).packet(work['task'])
        self.assertEqual(packet['claim'], q)
        for forbidden in (route, obligation, self.target, 'Secret selected route rationale', 'Root portfolio selection'):
            self.assertNotIn(forbidden, json.dumps(packet))
        NativeCapture(self.r).reserve([work['task']], '11111111-1111-4111-8111-111111111111')
        self.accept(q)
        self.review(obligation, ['obligation-mapping'])
        self.r.close_obligation(obligation, expected=self.store.revision)
        self.assertFalse(self.r.obligation_open(self.store.get(obligation)))
        owned = [i for i in self.co.frontier(self.target)['items'] if i['action'] == 'inspect-owned-work']
        self.assertTrue(any(i['detail']['intent'] == work['intent'] and i['detail']['unknown_attempt'] for i in owned))
        with self.assertRaises(StateError):
            self.prepare(instance='wrong-anchor', request_id='wrong-anchor', work_target=q, anchors={'route': route})

    def test_context_continuation_binds_parent_and_is_immediately_current_after_disposition(self):
        first = self.prepare()
        result = self.completed_context(first)
        definition = self.r.definition('D', 'Exact additional definition')
        new = self.co.continue_work(first['intent'], result, 'context-two', 'Sensitive root choice rationale',
            added=[definition], expected=self.store.revision, request_id='context-two')
        self.assertTrue(new['current']['basis_unchanged'])
        packet = Tasks(self.r).packet(new['task'])
        self.assertNotIn('Sensitive root choice rationale', json.dumps(packet))
        self.assertIn(definition, packet['records'])
        before = self.store.revision
        replay = self.co.continue_work(first['intent'], result, 'context-two', 'Sensitive root choice rationale',
            added=[definition], expected=0, request_id='context-two')
        self.assertEqual(replay['intent'], new['intent'])
        self.assertEqual(self.store.revision, before)
        wrong = self.prepare(key='different-parent-lane', instance='wrong-parent', request_id='wrong-parent')
        with self.assertRaises(StateError):
            self.co.continue_work(wrong['intent'], result, 'mismatch', 'Different parent',
                added=[definition], expected=self.store.revision, request_id='mismatch')

    def test_context_continuation_rejects_new_target_hold_and_retracted_producer(self):
        first = self.prepare()
        result = self.completed_context(first)
        definition = self.r.definition('D', 'Exact definition D')
        self.r.objection(self.target, self.proof, 'new-critic')
        with self.assertRaises(StateError):
            self.co.continue_work(first['intent'], result, 'blocked', 'Changed target', added=[definition],
                expected=self.store.revision, request_id='blocked')
        other = self.claim('Separate target')
        fresh = self.prepare(target=other, work_target=other, key='other', instance='other', request_id='other')
        terminal = self.completed_context(fresh)
        self.r.withdraw(self.store.get(terminal)['data']['host_receipt'], 'Producer receipt withdrawn')
        with self.assertRaises(StateError):
            self.co.continue_work(fresh['intent'], terminal, 'retracted', 'Changed producer', added=[definition],
                expected=self.store.revision, request_id='retracted')

    def test_frontier_uses_canonical_execution_events_without_reading_host_journals(self):
        with patch('mathtrace.evidence.Evidence.inspect_execution', side_effect=AssertionError('External journal read')):
            self.co.frontier(self.target)

    def test_fresh_instance_cannot_conceal_parallel_or_successor_work(self):
        first = self.prepare()
        NativeCapture(self.r).reserve([first['task']], '11111111-1111-4111-8111-111111111111')
        with self.assertRaisesRegex(StateError, 'parallel/successor'):
            self.prepare(instance='unexplained-extra', request_id='unexplained')
        self.assertTrue(self.co.inspect_work(first['intent'])['unknown_attempt'])


if __name__ == '__main__':
    unittest.main()
