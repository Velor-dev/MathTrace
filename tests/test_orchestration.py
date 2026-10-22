import json
import unittest
from unittest.mock import patch
import test_research

from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError, digest


class OrchestrationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.o = Orchestration(self.r)

    def result(self, target, outcome, proposals=None, requested=None):
        tasks = Tasks(self.r)
        task = tasks.create('prover', target, checks=['argument'], mandate='Solve exact target')
        conversation = 'native-worker-' + task
        run = tasks.start(task, conversation, host='antigravity', dispatch_evidence=self.proof, tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
            'outcome': outcome, 'reasoning': 'Durable partial mathematical argument',
            'proposals': proposals or [], 'requested_context': requested or []})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': conversation, 'status': 'SUCCESS', 'response': output}))
        return tasks.finish(run, artifact, receipt, outcome=outcome)

    def test_proposals_are_atomic_and_do_not_accept_mathematics(self):
        target = self.claim()
        result = self.result(target, 'proposal', [
            {'local_id': 'lemma', 'kind': 'claim', 'data': {'statement': 'New lemma'}},
            {'local_id': 'argument', 'kind': 'inference', 'data': {'conclusion': 'lemma'}},
        ])
        imported = self.o.ingest(result)
        self.assertFalse(imported['mathematical_acceptance'])
        inference = self.store.get(imported['registered'][-1])
        self.assertEqual(self.store.status(inference['id']), 'proposed')
        self.assertTrue(any(a.get('target') == inference['id'] and a['action'] == 'evaluate-inference-for-promotion'
                            for a in self.o.next_actions()['actions']))
        self.assertEqual(self.r.claim_state(inference['data']['conclusion'])['state'], 'unsupported')
        snapshot = self.store.revision
        self.assertEqual(self.o.ingest(result), imported)
        self.assertEqual(self.store.revision, snapshot)

    def test_partial_result_remains_actionable_until_explicit_disposition(self):
        target = self.claim()
        result = self.result(target, 'inconclusive')
        self.o.ingest(result)
        self.assertTrue(any(a.get('result') == result and a['action'] == 'assess-research-result'
                            for a in self.o.next_actions()['actions']))
        response = self.o.dispose_result(result, 'Preserved unsuccessful route; no proof obtained', [],
                                        'Reopen if a new estimate resolves the failed step')
        self.assertFalse(response['mathematical_acceptance'])
        self.assertFalse(any(a.get('result') == result for a in self.o.next_actions()['actions']))
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_disposition_history_is_scoped_advisory_and_retained_after_retraction(self):
        target, other = self.claim(), self.claim('Unrelated problem')
        result = self.result(target, 'inconclusive')
        self.o.ingest(result)
        route = self.r.route(target, 'Residual estimate', family='estimate')
        unrelated = self.r.route(other, 'Other work', family='other')
        before = self.store.revision
        with self.assertRaisesRegex(StateError, 'target-scoped'):
            self.o.dispose_result(result, 'Blocked estimate', [unrelated], 'A stronger bound')
        self.assertEqual(self.store.revision, before)
        self.o.dispose_result(result, 'Blocked estimate', [route], 'A stronger bound')
        item = self.r.portfolio(target)['dispositions'][0]
        self.assertEqual(item['reason'], 'Blocked estimate')
        self.assertEqual(item['followups'][0]['id'], route)
        self.assertFalse(item['mathematical_acceptance'])
        self.assertTrue(item['source_records_current'])
        self.assertEqual(self.r.portfolio(other)['dispositions'], [])
        strategy = Tasks(self.r).packet(self.o.strategize(target))
        projected = strategy['research_state']['dispositions'][0]
        self.assertEqual(projected['result_hash'], item['result_hash'])
        self.assertEqual(projected['followups_omitted'], 0)
        self.assertNotIn(result, strategy['records'])
        blind = Tasks(self.r).packet(Tasks(self.r).create('scout', target,
            checks=['exploration'], mandate='Independent route'))
        self.assertNotIn('research_state', blind)
        self.r.withdraw(result, 'Retract source provenance')
        history = self.r.portfolio(target)['dispositions'][0]
        self.assertEqual(history['decision_hash'], item['decision_hash'])
        self.assertFalse(history['source_records_current'])

    def test_imported_new_lemma_is_a_followup_without_becoming_accepted(self):
        target = self.claim()
        result = self.result(target, 'proposal', [
            {'local_id': 'residual', 'kind': 'claim', 'data': {'statement': 'Unproved residual lemma'}}])
        created = self.o.ingest(result)['registered']
        self.o.dispose_result(result, 'Reduction is incomplete', [created[-1]], 'Prove residual lemma')
        self.assertEqual(self.r.claim_state(created[-1])['state'], 'unsupported')
        self.assertEqual(self.r.portfolio(target)['dispositions'][0]['followups'][0]['id'], created[-1])

    def test_strategy_bounds_dispositions_without_erasing_canonical_history(self):
        target = self.claim()
        for n in range(34):
            result = self.result(target, 'inconclusive')
            self.o.ingest(result)
            self.o.dispose_result(result, str(n) + 'x' * 3000, [], 'New evidence')
        packet = Tasks(self.r).packet(self.o.strategize(target))
        self.assertEqual(len(packet['research_state']['dispositions']), 32)
        self.assertEqual(packet['research_state']['dispositions_omitted'], 2)
        self.assertTrue(packet['research_state']['dispositions'][0]['reason']['truncated'])
        self.assertEqual(len(self.r.portfolio(target)['dispositions']), 34)

    def test_disposition_followups_are_deduplicated_and_projection_is_bounded(self):
        target = self.claim()
        result = self.result(target, 'inconclusive')
        self.o.ingest(result)
        routes = [self.r.route(target, f'Method {n}', family='search') for n in range(18)]
        self.o.dispose_result(result, 'Failed methods retained', routes + [routes[0]] * 300, 'New estimate')
        self.assertEqual(len(self.r.portfolio(target)['dispositions'][0]['followups']), 18)
        packet = Tasks(self.r).packet(self.o.strategize(target))
        entry = packet['research_state']['dispositions'][0]
        self.assertEqual(len(entry['followups']), 16)
        self.assertEqual(entry['followups_omitted'], 2)

    def test_exact_evidence_retrieval_is_bounded_without_loading_unrelated_history(self):
        text = 'Exact proof evidence. ' * 300
        artifact = self.r.artifact(text)
        unrelated = self.r.artifact('Unrelated historical verdict')
        before = self.store.revision
        preview = self.o.inspect_record(artifact)
        self.assertTrue(preview['record']['data']['text']['truncated'])
        self.assertNotIn(unrelated, json.dumps(preview))
        self.assertEqual(self.o.inspect_record(artifact, full=True)['record']['data']['text'], text)
        self.assertEqual(self.store.revision, before)

    def test_strategy_receives_scoped_current_portfolio_without_contaminating_blind_work(self):
        target = self.claim()
        unrelated = self.claim('Different research target')
        route = self.r.route(target, 'Try a reduction', family='reduction')
        other_route = self.r.route(unrelated, 'Other route', family='other')
        certificate = self.r.artifact('Only reduced to an unproved statement of comparable strength.')
        self.r.route_status(route, 'blocked', certificate, reopen_condition='Find an independent proof of the residual lemma')
        obligation = self.r.obligation(route, 'Prove the residual lemma')
        task = self.o.strategize(target)
        packet = Tasks(self.r).packet(task)
        self.assertEqual(packet['independence'], 'informed')
        self.assertEqual(packet['research_state']['routes'][0]['status'], 'blocked')
        self.assertIn(obligation, packet['records'])
        self.assertNotIn(other_route, packet['records'])
        self.r.route_status(route, 'active', certificate, reopen_condition='A new route was proposed')
        self.assertEqual(Tasks(self.r).packet(task), packet)
        self.assertEqual(self.r.portfolio(target)['routes'][0]['status'], 'active')
        blind = Tasks(self.r).create('scout', target, checks=['exploration'], mandate='Independent route')
        blind_packet = Tasks(self.r).packet(blind)
        self.assertNotIn('research_state', blind_packet)
        self.assertNotIn(route, blind_packet['records'])
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_bad_later_proposal_rolls_back_whole_import(self):
        target = self.claim()
        result = self.result(target, 'proposal', [
            {'local_id': 'first', 'kind': 'claim', 'data': {'statement': 'Unaccepted lemma'}},
            {'local_id': 'second', 'kind': 'inference', 'data': {'conclusion': 'first', 'status': 'accepted'}},
        ])
        before_claims = self.store.records('claim')
        captured = self.o.ingest(result)
        self.assertEqual(captured['observation'], 'ingestion-quarantined')
        self.assertEqual(self.store.records('claim'), before_claims)
        self.assertEqual(self.store.records('inference'), [])
        self.assertTrue(self.r.finding_blocking(captured['substance_finding']))
        before = self.store.revision
        self.assertEqual(self.o.ingest(result), captured)
        self.assertEqual(self.store.revision, before)

    def test_worker_code_is_preserved_as_reviewable_plan_without_execution(self):
        target = self.claim()
        code = 'raise RuntimeError("proposal must not execute during ingestion")'
        result = self.result(target, 'proposal', [
            {'local_id': 'compute', 'kind': 'experiment', 'data': {
                'source_code': code, 'scope': 'Finite exploratory computation', 'inputs': {'n': 7}}},
            {'local_id': 'formal', 'kind': 'formal_plan', 'data': {
                'source_code': 'theorem t : True := by trivial', 'symbol': 't', 'expected_type': 'True'}},
        ])
        with patch('mathtrace.evidence.compute') as execute:
            imported = self.o.ingest(result)
            execute.assert_not_called()
        experiment = self.store.records('experiment')[0]
        self.assertEqual(self.store.get(experiment['data']['source'])['data']['text'], code)
        self.assertEqual(experiment['data']['inputs'], {'n': 7})
        self.assertEqual(len(self.store.records('formal_plan')), 1)
        self.assertEqual(self.store.records('formal_receipt'), [])
        self.assertFalse(imported['mathematical_acceptance'])
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_explicit_counterexample_outcome_registers_only_an_unvalidated_exact_claim_proposal(self):
        target = self.claim()
        result = self.result(target, 'counterexample')
        imported = self.o.ingest(result)
        example = self.store.records('counterexample')[0]
        self.assertIn(example['id'], imported['registered'])
        self.assertEqual(example['data']['target'], target)
        self.assertEqual(self.store.status(example['id']), 'proposed')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertTrue(any(a['action'] == 'evaluate-counterexample' and a.get('target') == example['id']
                            for a in self.o.next_actions()['actions']))
        inference = self.r.inference(target, [], self.proof, 'author')
        method_result = self.result(inference, 'counterexample')
        captured = self.o.ingest(method_result)
        self.assertEqual(captured['observation'], 'ingestion-quarantined')
        self.assertIn('method defect', self.store.get(captured['failure'])['data']['validation_error'])
        self.assertEqual(len(self.store.records('counterexample')), 1)

    def test_worker_result_retraction_suspends_argument_and_code_proposals(self):
        target = self.claim()
        result = self.result(target, 'proposal', [
            {'local_id': 'proof', 'kind': 'inference', 'data': {'conclusion': target}},
            {'local_id': 'compute', 'kind': 'experiment', 'data': {'source_code': 'print(1)', 'scope': 'Observation'}},
        ])
        self.o.ingest(result)
        inference = self.store.records('inference')[0]
        experiment = self.store.records('experiment')[0]
        self.review(inference['id'])
        self.r.promote(inference['id'], expected=self.store.revision, request_id='worker-proof')
        self.assertEqual(self.r.claim_state(target)['state'], 'supported')
        self.r.withdraw(result, 'Producer provenance retracted')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertFalse(self.r._scope_current(experiment['id']))
        self.assertFalse(self.r._scope_current(experiment['data']['source']))

        other = self.claim('Other target')
        negative_result = self.result(other, 'counterexample')
        self.o.ingest(negative_result)
        example = self.store.records('counterexample')[0]
        self.review(example['id'], ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example['id'], expected=self.store.revision)
        self.assertEqual(self.r.claim_state(other)['state'], 'refuted')
        self.r.withdraw(negative_result, 'Negative result provenance retracted')
        self.assertEqual(self.r.claim_state(other)['state'], 'unsupported')

    def test_context_request_remains_actionable_until_bound_continuation(self):
        result = self.result(self.claim(), 'context-request', requested=['Define whether naturals include zero'])
        self.o.ingest(result)
        self.assertIn({'action': 'supply-context', 'result': result}, self.o.next_actions()['actions'])
        definition = self.r.definition('Naturals', 'Includes zero')
        task = self.o.resolve_context(result, [definition], 'Explicit source convention')
        self.assertEqual(self.store.status(result), 'context-resolved')
        self.assertEqual(self.store.status(task), 'ready')
        with self.assertRaises(StateError):
            self.o.resolve_context(result, [definition], 'Duplicate continuation')

    def test_stale_audited_candidate_is_not_lost_behind_alternative_support(self):
        target = self.claim()
        first = self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.accept(target)
        self.r.withdraw(first, 'Frozen derivation invalid')
        actions = self.o.next_actions()['actions']
        self.assertIn({'action': 'revise-candidate', 'candidate': candidate, 'reuse_old_audit': False}, actions)

    def test_checkpoint_preserves_unresolved_partial_state(self):
        result = self.result(self.claim(), 'inconclusive')
        self.o.ingest(result)
        checkpoint = self.o.checkpoint('Strategy change after inconclusive route')
        data = self.store.get(checkpoint)['data']
        self.assertFalse(data['pending']['solved'])
        self.assertNotIn('snapshot', data)
        self.assertIn('base_revision', data)
        self.assertIn('event_head', data)
        self.assertIn('snapshot_hash', data)
        snapshot = self.o.checkpoint_snapshot(checkpoint)
        self.assertEqual(digest(snapshot), data['snapshot_hash'])
        self.assertTrue(any(r['id'] == result for r in snapshot['records']))

    def test_sequential_checkpoints_do_not_recursively_embed_snapshots(self):
        for i in range(1, 6):
            cp = self.o.checkpoint(f'Sequential checkpoint {i}')
            data = self.store.get(cp)['data']
            # Structural invariant: new-format checkpoint payloads never embed snapshots.
            self.assertNotIn('snapshot', data)
            reconstructed = self.o.checkpoint_snapshot(cp)
            self.assertEqual(digest(reconstructed), data['snapshot_hash'])
            self.assertEqual(reconstructed['events'][-1]['hash'], data['event_head'])
        self.assertTrue(self.store.health()['ok'])

    def test_legacy_embedded_snapshot_checkpoint_is_supported_and_immutable(self):
        target = self.claim()
        legacy_snapshot = self.store.export()
        with self.store.transaction():
            legacy_id = self.store.put('checkpoint', {
                'reason': 'Historical checkpoint',
                'snapshot': legacy_snapshot,
                'snapshot_hash': digest(legacy_snapshot),
                'pending': self.o.next_actions(),
            })
        # Reader handles legacy format seamlessly
        self.assertEqual(self.o.checkpoint_snapshot(legacy_id), legacy_snapshot)
        # Database health remains valid with legacy record
        self.assertTrue(self.store.health()['ok'])

    def test_checkpoint_snapshot_detects_tampered_hash(self):
        with self.store.transaction():
            corrupted_id = self.store.put('checkpoint', {
                'reason': 'Tampered checkpoint',
                'base_revision': self.store.revision,
                'event_head': self.store.export()['events'][-1]['hash'],
                'snapshot_hash': 'f' * 64,
                'pending': self.o.next_actions(),
            })
        with self.assertRaisesRegex(StateError, 'snapshot hash mismatch'):
            self.o.checkpoint_snapshot(corrupted_id)

    def test_checkpoint_snapshot_detects_tampered_event_head(self):
        with self.store.transaction():
            base_revision = self.store.revision
            snapshot = self.store.export()
            corrupted_id = self.store.put('checkpoint', {
                'reason': 'Tampered event lineage',
                'base_revision': base_revision,
                'event_head': '0' * 64,
                'snapshot_hash': digest(snapshot),
                'pending': self.o.next_actions(),
            })
        with self.assertRaisesRegex(StateError, 'event head mismatch'):
            self.o.checkpoint_snapshot(corrupted_id)

    def test_legacy_checkpoint_hash_is_verified(self):
        legacy_snapshot = self.store.export()
        with self.store.transaction():
            corrupted_id = self.store.put('checkpoint', {
                'reason': 'Tampered legacy checkpoint',
                'snapshot': legacy_snapshot,
                'snapshot_hash': 'f' * 64,
                'pending': self.o.next_actions(),
            })
        with self.assertRaisesRegex(StateError, 'snapshot hash mismatch'):
            self.o.checkpoint_snapshot(corrupted_id)

    def test_single_referee_cannot_certify_all_independent_lanes(self):
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.review(candidate, ['full-proof', 'target-fidelity', 'dependency-closure', 'falsification'])
        with self.assertRaisesRegex(StateError, 'distinct native'):
            self.r.audit_candidate(candidate, expected=self.store.revision)

    def test_proposal_ingest_rejects_collection_coercion_and_rolls_back(self):
        target = self.claim()
        asm = self.r.assumption("x is real")

        malformed_proposals = [
            # premises as dict
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'premises': {target: 'val'}}}],
            # premises as non-list
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'premises': target}}],
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'premises': 123}}],
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'premises': None}}],
            # assumptions as dict
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'assumptions': {asm: False}}}],
            # discharge as dict
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'discharge': {asm: False}}}],
            # applications as dict
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'applications': {'app': False}}}],
            # definitions in claim as dict
            [{'local_id': 'lemma', 'kind': 'claim', 'data': {'statement': 'L', 'definitions': {'def': False}}}],
            # formal_plan allowed_axioms as dict
            [{'local_id': 'fp', 'kind': 'formal_plan', 'data': {'source_code': 'theorem t : True := by trivial', 'symbol': 't', 'expected_type': 'True', 'allowed_axioms': {'propext': False}}}],
            # non-string reference in array
            [{'local_id': 'inf', 'kind': 'inference', 'data': {'conclusion': target, 'premises': [123]}}],
        ]

        for proposals in malformed_proposals:
            result = self.result(target, 'proposal', proposals)
            counts = {k: len(self.store.records(k)) for k in ('claim', 'inference', 'formal_plan')}
            captured = self.o.ingest(result)
            self.assertEqual(captured['observation'], 'ingestion-quarantined')
            self.assertEqual({k: len(self.store.records(k)) for k in counts}, counts)
            self.assertEqual(self.store.status(result), 'quarantined')
            self.assertTrue(self.r.finding_blocking(captured['substance_finding']))
            self.assertFalse(any(a['action'] == 'ingest-result' and a.get('result') == result
                                 for a in self.o.next_actions()['actions']))

    def test_resolve_context_and_dispose_result_reject_collection_coercion(self):
        target = self.claim()
        d1 = self.r.definition("D1", "First definition")
        result = self.result(target, 'context-request', requested=[target])
        self.o.ingest(result)
        self.assertEqual(self.store.status(result), 'context-needed')

        base_rev = self.store.revision
        base_count = len(self.store.records())

        # 1. resolve_context added must be an exact nonempty list of strings
        for invalid in [{d1: False}, d1, 123, [], [123], [""]]:
            with self.assertRaisesRegex(StateError, "added must be a nonempty list"):
                self.o.resolve_context(result, invalid, "need D1")

        # Transactional cleanliness: status still context-needed, no new records
        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)
        self.assertEqual(self.store.status(result), 'context-needed')

        # 2. dispose_result followups must be an exact list of strings
        result_inconclusive = self.result(target, 'inconclusive')
        self.o.ingest(result_inconclusive)
        for invalid in [{d1: False}, d1, 123, [123], [""]]:
            with self.assertRaisesRegex(StateError, "Followups must identify exact records"):
                self.o.dispose_result(result_inconclusive, "Unsuccessful route", invalid, "Reopen condition")

    def test_resolve_context_becomes_informed_rejects_non_boolean(self):
        target = self.claim()
        d1 = self.r.definition("D1", "First definition")
        result = self.result(target, 'context-request', requested=[target])
        self.o.ingest(result)

        base_rev = self.store.revision
        base_count = len(self.store.records())

        for invalid in ["false", "true", 0, 1, None, [], {}]:
            with self.assertRaisesRegex(StateError, "becomes_informed must be an exact boolean"):
                self.o.resolve_context(result, [d1], "need D1", becomes_informed=invalid)

        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)
        self.assertEqual(self.store.status(result), 'context-needed')



