import tempfile
import unittest
import json
import uuid
from pathlib import Path

from mathtrace.store import Store, StateError, StaleState, digest
from mathtrace.research import Research
from mathtrace.context import Tasks


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'state.sqlite', create=True)
        self.r = Research(self.store)
        self.contract = self.r.contract('For x>0 in R, x²>0', [], completion='Full proof or valid disproof')
        self.proof = self.r.artifact('Explicit argument body; fixture tests bookkeeping, not mathematical validity.')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def claim(self, text='P'):
        return self.r.claim(text, self.contract)

    def review(self, target, checks=None, verdict='pass', reviewer='referee', role='referee', conversation_id=None):
        if reviewer == self.store.get(target)['data'].get('author'):
            return self.r.review(target, reviewer, 'invalid-self-run', verdict, self.proof,
                                 checks or ['validity', 'scope', 'dependencies'])
        checks = checks or ['validity', 'scope', 'dependencies']
        tasks = Tasks(self.r)
        independence = 'informed' if self.store.get(target)['kind'] == 'adjudication' else 'blind'
        task = tasks.create(role, target, checks=checks, mandate='Assess exactly these checks', independence=independence)
        conversation = conversation_id or reviewer + '-' + uuid.uuid4().hex
        capture = self.r.artifact(json.dumps({'kind': 'native-dispatch-capture', 'task_id': task,
            'packet_hash': tasks.packet(task)['packet_hash'], 'conversation_id': conversation,
            'host': 'antigravity', 'declared_tools': [], 'declared_inherited_history': False}))
        run = tasks._start_captured(task, conversation, host='antigravity', dispatch_evidence=capture,
                          tools=[], inherited_history=False)
        # Synthetic fixture of an external receipt: tests protocol binding, not a
        # live host execution or actual mathematical correctness.
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
                             'outcome': 'review', 'verdict': verdict, 'checks': checks,
                             'reasoning': 'Synthetic scoped assessment for deterministic protocol test'})
        result_artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': conversation, 'status': 'SUCCESS', 'response': output}))
        tasks._finish_captured(run, result_artifact, receipt, outcome='review', verdict=verdict, checks=checks)
        self.last_run = run
        exposure = tasks.review_provenance(run, target, verdict, result_artifact, checks)['exposure']
        return self.r.review(target, conversation, run, verdict, result_artifact, checks, exposure=exposure)

    def accept(self, claim, premises=None, assumptions=None):
        inf = self.r.inference(claim, premises or [], self.proof, 'author', assumptions=assumptions)
        self.review(inf)
        self.r.promote(inf, expected=self.store.revision, request_id='promote-' + inf)
        return inf

    def test_one_missing_and_premise_blocks_promotion(self):
        a, b, d = self.claim('A'), self.claim('B'), self.claim('D')
        self.accept(a)
        inf = self.r.inference(d, [a, b], self.proof, 'author')
        self.review(inf)
        with self.assertRaises(StateError):
            self.r.promote(inf, expected=self.store.revision, request_id='and')
        self.assertEqual(self.r.claim_state(d)['state'], 'unsupported')

    def test_alternate_proof_survives_and_last_withdrawal_is_not_refutation(self):
        a, d = self.claim('A'), self.claim('D')
        ai = self.accept(a)
        di = self.accept(d, [a])
        independent = self.accept(d)
        self.r.withdraw(ai, 'proof gap')
        self.assertEqual(self.r.claim_state(d)['supports'], [independent])
        self.r.withdraw(independent, 'separate proof gap')
        self.assertEqual(self.r.claim_state(d)['state'], 'unsupported')
        self.assertEqual(self.store.status(di), 'accepted')  # historical decision, current support lost

    def test_assumptions_cannot_be_laundered_through_premises(self):
        assumption = self.r.assumption('A')
        p, q = self.claim('P'), self.claim('Q')
        self.accept(p, assumptions=[assumption])
        self.assertEqual(self.r.claim_state(p)['state'], 'unsupported')
        self.assertEqual(self.r.claim_state(p, {assumption})['state'], 'supported')
        invalid = self.r.inference(q, [p], self.proof, 'author')
        self.review(invalid)
        with self.assertRaises(StateError):
            self.r.promote(invalid, expected=self.store.revision, request_id='scope')

    def test_discharge_requires_rule_and_independent_scope_review(self):
        assumption = self.r.assumption('A')
        p, q = self.claim('P'), self.claim('A implies P')
        self.accept(p, assumptions=[assumption])
        with self.assertRaises(StateError):
            self.r.inference(q, [p], self.proof, 'author', discharge=[assumption])
        inf = self.r.inference(q, [p], self.proof, 'author', discharge=[assumption],
                               rule='implication-introduction')
        self.review(inf)
        with self.assertRaises(StateError):
            self.r.promote(inf, expected=self.store.revision, request_id='discharge')
        scope_review = self.review(inf, ['discharge'], reviewer='scope-auditor')
        self.r.promote(inf, expected=self.store.revision, request_id='discharge')
        self.assertEqual(self.r.claim_state(q)['state'], 'supported')
        self.r.withdraw(scope_review, 'scope audit invalid')
        self.assertEqual(self.r.claim_state(q)['state'], 'unsupported')

    def test_cycle_cannot_bootstrap_acceptance(self):
        p, q = self.claim('P'), self.claim('Q')
        inf = self.r.inference(p, [q], self.proof, 'author')
        self.review(inf)
        with self.assertRaises(StateError):
            self.r.promote(inf, expected=self.store.revision, request_id='cycle')

    def test_failure_is_not_outvoted(self):
        p = self.claim()
        inf = self.r.inference(p, [], self.proof, 'author')
        for i in range(5):
            self.review(inf, reviewer=f'pass-{i}')
        self.review(inf, verdict='fail', reviewer='fatal-objection')
        with self.assertRaises(StateError):
            self.r.promote(inf, expected=self.store.revision, request_id='votes')

    def test_new_objection_stales_pending_promotion(self):
        inf = self.r.inference(self.claim(), [], self.proof, 'author')
        self.review(inf)
        snapshot = self.store.revision
        self.r.objection(inf, self.proof, 'hunter')
        with self.assertRaises(StaleState):
            self.r.promote(inf, expected=snapshot, request_id='stale')
        with self.assertRaises(StateError):
            self.r.promote(inf, expected=self.store.revision, request_id='stale')

    def test_alternate_support_does_not_resolve_objection(self):
        p = self.claim()
        first = self.accept(p)
        objection = self.r.objection(first, self.proof, 'hunter')
        second = self.accept(p)
        self.assertEqual(self.r.claim_state(p)['supports'], [second])
        self.assertEqual(self.store.status(objection), 'open')

    def test_verified_refutation_does_not_propagate_as_truth(self):
        p, q = self.claim('false lemma'), self.claim('downstream result')
        self.accept(p)
        self.accept(q, [p])
        example = self.r.counterexample(p, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(p)['state'], 'conflict')
        self.assertEqual(self.r.claim_state(q)['state'], 'unsupported')

    def test_counterexample_without_domain_review_is_not_refutation(self):
        p = self.claim()
        example = self.r.counterexample(p, self.proof, 'hunter')
        self.review(example, ['negation', 'scope'])
        with self.assertRaises(StateError):
            self.r.validate_counterexample(example, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(p)['state'], 'unsupported')

    def test_self_review_and_fake_formal_label_rejected(self):
        p = self.claim()
        inf = self.r.inference(p, [], self.proof, 'author')
        with self.assertRaises(StateError):
            self.review(inf, reviewer='author')
        with self.assertRaises(StateError):
            self.r.inference(p, [], self.proof, 'author', assurance='formal')
        self.accept(p)
        self.assertEqual(self.r.claim_state(p, policy='formal-only')['state'], 'unsupported')

    def test_retry_does_not_duplicate_acceptance(self):
        inf = self.r.inference(self.claim(), [], self.proof, 'author')
        self.review(inf)
        snapshot = self.store.revision
        first = self.r.promote(inf, expected=snapshot, request_id='retry')
        after = self.store.revision
        second = self.r.promote(inf, expected=snapshot, request_id='retry')
        self.assertEqual(first, second)
        self.assertEqual(after, self.store.revision)

    def test_withdrawn_evidence_cannot_be_resurrected_with_old_reviews(self):
        target = self.claim()
        inference = self.accept(target)
        self.r.withdraw(inference, 'proof gap')
        with self.assertRaisesRegex(StateError, 'new proposed inference'):
            self.r.promote(inference, expected=self.store.revision, request_id='resurrect')
        counterexample = self.r.counterexample(target, self.proof, 'hunter')
        self.review(counterexample, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(counterexample, expected=self.store.revision)
        self.r.withdraw(counterexample, 'invalid domain')
        with self.assertRaisesRegex(StateError, 'must be proposed'):
            self.r.validate_counterexample(counterexample, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_contract_policy_types_are_strictly_validated(self):
        for invalid in ['false', 'true', 0, 1, [], {}, None]:
            with self.assertRaisesRegex(StateError, 'allow_disproof must be an exact boolean'):
                self.r.contract('P', [], completion='Proof', allow_disproof=invalid)
        for invalid in ['propext', {'propext': False}, [123], [''], ['   '], ['propext', 'propext'], 42, ['sorryAx']]:
            with self.assertRaises(StateError):
                self.r.contract('P', [], completion='Proof', allowed_axioms=invalid)
        for invalid in ['not a list', {'def': 'val'}, 123]:
            with self.assertRaises(StateError):
                self.r.contract('P', invalid, completion='Proof')
        c_no_disproof = self.r.contract('P_nodis', [], completion='Proof', allow_disproof=False)
        self.assertFalse(self.store.get(c_no_disproof)['data']['allow_disproof'])
        c_disproof = self.r.contract('P_dis', [], completion='Proof', allow_disproof=True)
        self.assertTrue(self.store.get(c_disproof)['data']['allow_disproof'])

    def test_claim_and_inference_collection_types_are_strictly_validated(self):
        target = self.claim()
        asm = self.r.assumption("x is real")

        # 1. definitions in claim must be list or None
        for invalid in [{"def": False}, "def", 123]:
            with self.assertRaisesRegex(StateError, "definitions must be an exact list"):
                self.r.claim("sub-claim", self.contract, definitions=invalid)

        # 2. premises in inference must be list
        for invalid in [{target: False}, target, 123, None]:
            with self.assertRaisesRegex(StateError, "premises must be an exact list"):
                self.r.inference(target, invalid, self.proof, "author")

        # 3. assumptions, discharge, applications in inference must be list or None
        for invalid in [{asm: False}, asm, 123]:
            with self.assertRaisesRegex(StateError, "assumptions must be an exact list"):
                self.r.inference(target, [], self.proof, "author", assumptions=invalid)
            with self.assertRaisesRegex(StateError, "discharge must be an exact list"):
                self.r.inference(target, [], self.proof, "author", discharge=invalid)
            with self.assertRaisesRegex(StateError, "applications must be an exact list"):
                self.r.inference(target, [], self.proof, "author", applications=invalid)

        # 4. checks in review must be list
        for invalid in [{"validity": True}, "validity", 123, []]:
            with self.assertRaisesRegex(StateError, "Review must declare exact checks"):
                self.r.review(target, "reviewer", "run-1", "pass", self.proof, invalid)

    def test_definition_dependencies_reject_collection_coercion(self):
        d1 = self.r.definition("BaseDef", "Base definition text")
        base_revision = self.store.revision
        record_count = len(self.store.records())

        # Dict with valid definition ID as key must not be silently accepted
        with self.assertRaisesRegex(StateError, "dependencies must be an exact list"):
            self.r.definition("ChildDef", "Child definition", dependencies={d1: False})

        # Non-list iterables or types must be rejected
        for invalid in [d1, 123, {d1: "v"}, [123], [""]]:
            with self.assertRaisesRegex(StateError, "dependencies must be an exact list"):
                self.r.definition("ChildDef", "Child definition", dependencies=invalid)

        # Transactional cleanliness: no definition created on failure
        self.assertEqual(self.store.revision, base_revision)
        self.assertEqual(len(self.store.records()), record_count)

        # Valid list succeeds and stores clean list
        d2 = self.r.definition("ChildDef", "Child definition", dependencies=[d1])
        self.assertEqual(self.store.get(d2)["data"]["dependencies"], [d1])


def recorded_result(result, journal, *, mode=None):
    """Explicit synthetic producer boundary for deterministic protocol tests."""
    producer = {'execution': journal['execution'], 'request_hash': journal['request_hash'],
                'pid': 1, 'boot_id': 'synthetic-test', 'start_ticks': '1', 'recorder_hash': 'mock-recorder'}
    metadata = {'execution': journal['execution'], 'request_hash': journal['request_hash'],
                'producer': producer, 'producer_hash': digest(producer), 'ok': True,
                'teardown': 'recorder-owned-processes-waited'}
    if mode:
        producer.update(execution_mode=mode, execution_protocol='mode-aware-execution-v1')
        metadata.update(execution_mode=mode, execution_protocol='mode-aware-execution-v1', producer_hash=digest(producer))
    return {**result, '_producer': metadata}


def recorded_runner(result):
    return lambda *args, journal, **kwargs: recorded_result(result, journal, mode=(args[0].get('execution_mode') if args and isinstance(args[0], dict) else None))


if __name__ == '__main__':
    unittest.main()
