"""Selected-argument sharing and composed exact-freeze checks.

Algorithm fixtures deliberately stub qualification; protocol composition uses
the existing synthetic captured-review seam, never claims live mathematics.
"""
from copy import deepcopy
import random
from types import SimpleNamespace
import unittest

import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.evaluation import Evaluation, EVALUATOR_VERSION
from mathtrace.store import StateError, digest
from mathtrace.witness import merge, nodes, pack, roots, single_root


def algorithm_evaluation(specifications):
    records = []
    for index, (claim, premises, assumptions, discharge, assurance) in enumerate(specifications):
        data = {'conclusion': claim, 'premises': premises, 'assumptions': assumptions,
                'discharge': discharge, 'assurance': assurance, 'artifact': 'fixture-proof'}
        body = {'id': f'i{index}', 'kind': 'inference', 'data': data}
        records.append({**body, 'hash': digest(body)})
    store = SimpleNamespace(db=SimpleNamespace(in_transaction=True), revision=1,
        records=lambda kind: records if kind == 'inference' else [], status=lambda _: 'accepted')
    research = SimpleNamespace(store=store, _truth_hold_findings=lambda _: {},
        _scope_current=lambda _: True, _blocked=lambda _: False, _formal_current=lambda _: True,
        _application_current=lambda _: True, _reviews=lambda *_: [])
    return Evaluation(research)


def reference_choices(records, claim, environment=frozenset(), *, policy='audited-informal',
                      forbidden=frozenset(), diagnostic=False, branch=frozenset()):
    """Independent uncached finite tree reference, retaining complete branches."""
    result = []
    for record in records:
        data, identifier = record['data'], record['id']
        if (data['conclusion'] != claim or identifier in branch
                or not set(data['assumptions']).issubset(environment)
                or (policy == 'formal-only' and data['assurance'] != 'formal')
                or (not data['assumptions'] and claim in forbidden and not diagnostic)):
            continue
        children = [reference_choices(records, p, frozenset(data['assumptions'] + data['discharge']),
            policy=policy, forbidden=forbidden, branch=branch | {identifier}) for p in data['premises']]
        if all(children):
            result.append((identifier, tuple(sorted(environment)), tuple(data['assumptions']),
                           tuple(c[0] for c in children)))
    return result


def expand_small(forest):
    table = nodes(forest)
    def visit(identifier):
        node = table[identifier]
        return (node['inference'], tuple(node['environment']), tuple(node['assumptions']),
                tuple(visit(c) for c in node['premises']))
    return [visit(r) for r in forest['roots']]


class WitnessAlgorithmTests(unittest.TestCase):
    def test_cache_preserves_reference_choices_across_scope_policy_veto_and_cycles(self):
        # Query history must not let a grounded cyclic region reuse an anchor
        # that the next caller's exact branch has excluded.
        cyclic = algorithm_evaluation([('P', ['Q'], [], [], 'informal'),
            ('Q', ['P'], [], [], 'informal'), ('P', [], [], [], 'informal')])
        self.assertEqual([single_root(w)['inference'] for w in cyclic.witnesses('P')], ['i0', 'i2'])
        self.assertEqual(cyclic.witnesses('P', stack={'i2'}), [])
        self.assertEqual([single_root(w)['inference'] for w in cyclic.witnesses('P')], ['i0', 'i2'])
        rng = random.Random(103)
        for _ in range(16):
            specifications = []
            for _ in range(9):
                specifications.append((rng.choice('PQRS'), rng.sample(list('PQRS'), rng.randrange(3)),
                    rng.choice([[], ['A'], ['B'], ['A', 'B']]), rng.choice([[], ['B']]),
                    rng.choice(['formal', 'informal'])))
            evaluation = algorithm_evaluation(specifications)
            for claim in 'PQRS':
                for env in [frozenset(), frozenset({'A', 'B'})]:
                    for policy in ['audited-informal', 'formal-only']:
                        for forbidden in [frozenset(), frozenset({'P', 'R'})]:
                            for diagnostic in [False, True]:
                                for branch in [frozenset(), frozenset({'i0', 'i2'})]:
                                    expected = reference_choices(evaluation.inferences, claim, env, policy=policy,
                                        forbidden=forbidden, diagnostic=diagnostic, branch=branch)
                                    actual = evaluation.witnesses(claim, env, policy=policy, forbidden=forbidden,
                                        diagnostic_root=diagnostic, stack=branch)
                                    self.assertEqual([expand_small(w)[0] for w in actual], expected)

    def test_diamond_shares_exact_nodes_and_acyclic_queries(self):
        specifications, previous = [('base', [], [], [], 'informal')], 'base'
        for level in range(12):
            left, right, joined = f'L{level}', f'R{level}', f'J{level}'
            specifications.extend([(left, [previous], [], [], 'informal'),
                (right, [previous], [], [], 'informal'), (joined, [left, right], [], [], 'informal')])
            previous = joined
        evaluation = algorithm_evaluation(specifications)
        forest = evaluation.witnesses(previous)[0]
        self.assertEqual(len(nodes(forest)), 37)
        self.assertEqual(len(evaluation._queries), 37)
        root = single_root(forest)
        left, right = [nodes(forest)[c] for c in root['premises']]
        self.assertEqual(left['premises'], right['premises'])
        self.assertTrue(evaluation.tree_current(forest))
        returned = deepcopy(forest)
        forest['nodes'].clear()  # Packet consumers cannot corrupt cached nodes.
        self.assertEqual(evaluation.witnesses(previous)[0], returned)

    def test_deep_linear_argument_does_not_require_python_recursion(self):
        specifications = [('C0', [], [], [], 'informal')]
        specifications.extend((f'C{i}', [f'C{i-1}'], [], [], 'informal') for i in range(1, 1100))
        evaluation = algorithm_evaluation(specifications)
        forest = evaluation.witnesses('C1099')[0]
        self.assertEqual(len(nodes(forest)), 1100)
        self.assertTrue(evaluation.tree_current(forest))

    def test_node_dag_can_still_contain_a_forbidden_inference_repeat(self):
        evaluation = algorithm_evaluation([('P', ['Q'], [], [], 'informal'),
            ('Q', ['P'], [], [], 'informal'), ('Q', [], [], [], 'informal')])
        forest = evaluation.witnesses('P')[0]
        self.assertTrue(evaluation.tree_current(forest))
        table = deepcopy(nodes(forest))
        original = single_root(forest)
        middle = {'inference': 'i1', 'inference_hash': evaluation.by_id['i1']['hash'],
                  'claim': 'Q', 'environment': [], 'assumptions': [], 'premises': forest['roots']}
        table[digest(middle)] = middle
        repeated = {**original, 'premises': [digest(middle)]}
        table[digest(repeated)] = repeated
        malformed = pack([digest(repeated)], table)
        nodes(malformed)  # A structurally exact, acyclic node graph.
        self.assertFalse(evaluation.tree_current(malformed))

    def test_exact_hash_children_reachability_and_scope_are_required(self):
        evaluation = algorithm_evaluation([('P', [], ['A'], [], 'informal'),
            ('Q', ['P'], [], ['A'], 'informal'), ('unused', [], [], [], 'informal')])
        good = evaluation.witnesses('Q')[0]
        self.assertTrue(evaluation.tree_current(good))
        stale_hash = deepcopy(good)
        old = single_root(stale_hash)
        modified = {**old, 'inference_hash': 'unbound'}
        stale_hash['nodes'][digest(modified)] = modified
        stale_hash = pack([digest(modified)], stale_hash['nodes'])
        self.assertFalse(evaluation.tree_current(stale_hash))
        wrong_child = {**old, 'premises': []}
        table = {digest(wrong_child): wrong_child}
        self.assertFalse(evaluation.tree_current(pack([digest(wrong_child)], table)))
        unused = evaluation.witnesses('unused')[0]
        injected = deepcopy(good)
        injected['nodes'].update(unused['nodes'])
        self.assertFalse(evaluation.tree_current(injected))
        self.assertFalse(evaluation.tree_current(evaluation.witnesses('P', {'A', 'B'})[0], {'A'}))
        self.assertFalse(evaluation.tree_current(good, policy='formal-only'))
        self.assertFalse(evaluation.tree_current(good, forbidden={'Q'}))
        # A scoped occurrence is legitimate inside reviewed discharge.
        self.assertTrue(evaluation.tree_current(good, forbidden={'P'}))
        dangling = deepcopy(good)
        dangling['nodes'].pop(next(c for c in good['nodes'] if c != good['roots'][0]))
        self.assertFalse(evaluation.tree_current(dangling))

    def test_cached_evaluation_cannot_cross_revision_or_transaction_boundary(self):
        evaluation = algorithm_evaluation([('P', [], [], [], 'informal')])
        evaluation.witnesses('P')
        evaluation.bounds()
        evaluation.store.revision += 1
        with self.assertRaises(StateError):
            evaluation.witnesses('P')
        with self.assertRaises(StateError):
            evaluation.bounds()
        evaluation.store.revision -= 1
        evaluation.store.db.in_transaction = False
        with self.assertRaises(StateError):
            evaluation.tree_current(pack([], {}))


class WitnessCompositionTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def test_shared_candidate_and_refutation_packet_keep_exact_choices_without_verdict_history(self):
        base, left, right, target = [self.claim(n) for n in ['B', 'L', 'R', 'T']]
        first = self.accept(base)
        self.accept(left, [base])
        self.accept(right, [base])
        self.accept(target, [left, right])
        proof_candidate = self.r.freeze(target, self.proof, author='root')
        forest = self.store.get(proof_candidate)['data']['derivation']['witness']
        self.assertEqual(len(nodes(forest)), 4)
        self.assertTrue(self.r.candidate_current(proof_candidate))
        negative = self.claim('N')
        example = self.r.counterexample(negative, self.proof, 'hunter', dependencies=[left, right])
        self.review(example, ['domain', 'negation', 'scope', 'dependencies'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        disproof_candidate = self.r.freeze(negative, self.proof, author='hunter', outcome='disproof')
        selected = self.store.get(disproof_candidate)['data']['derivation']['witness']
        self.assertEqual([r['claim'] for r in roots(selected)], [left, right])
        self.assertEqual(len(nodes(selected)), 3)
        tasks = Tasks(self.r)
        task = tasks.create('referee', example, checks=['domain', 'negation', 'scope', 'dependencies'],
                            mandate='Check the complete declared counterexample dependencies')
        packet = tasks.packet(task)
        self.assertEqual(packet['dependency_evidence']['selected'], selected)
        self.assertNotIn('review', {r['kind'] for r in packet['records'].values()})
        self.accept(base)
        self.r.withdraw(first, 'The selected shared argument fails')
        self.assertEqual(self.r.claim_state(target)['state'], 'supported')
        self.assertEqual(self.r.claim_state(negative)['state'], 'refuted')
        self.assertFalse(self.r.candidate_current(proof_candidate))
        self.assertFalse(self.r.candidate_current(disproof_candidate))

    def test_profile_migration_and_empty_disproof_forest_do_not_invent_evidence(self):
        target = self.claim()
        example = self.r.counterexample(target, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        candidate = self.r.freeze(target, self.proof, author='hunter', outcome='disproof')
        data = self.store.get(candidate)['data']
        self.assertEqual(data['derivation']['witness'], merge([]))
        self.assertTrue(self.r.candidate_current(candidate))
        old = deepcopy(data)
        old['evaluator'] = 'scoped-grounding-finding-effects-v2'
        old['manifest_hash'] = digest({'records': old['manifest'], 'derivation': old['derivation'],
                                       'evaluator': old['evaluator']})
        with self.store.transaction():
            historical = self.store.put('candidate', old)
            self.store.decide(historical, 'frozen', {'reason': 'Historical profile fixture'})
        self.assertFalse(self.r.candidate_current(historical))
        self.assertEqual(self.store.get(candidate)['data']['evaluator'], EVALUATOR_VERSION)
        self.r.withdraw(example, 'Counterexample argument withdrawn')
        self.assertFalse(self.r.candidate_current(candidate))


if __name__ == '__main__':
    unittest.main()
