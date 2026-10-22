"""Snapshot-local grounding and conservative refutation eligibility.

This is a deterministic evidence projection, not a mathematical truth oracle.
No derived graph or truth-maintenance database is authoritative. Negatives are
admitted independently of the consumer's positive formal/informal policy.
"""

from .store import StateError, digest
from .witness import nodes, pack, single_root

EVALUATOR_VERSION = 'scoped-selected-forest-v3'


class Evaluation:
    def __init__(self, research, *, proposed_inference=None, proposed_counterexample=None):
        self.r, self.store = research, research.store
        if not self.store.db.in_transaction:
            raise StateError('Evidence evaluation requires one coherent snapshot')
        self.revision = self.store.revision
        # Scope certification is static qualification metadata, independent of
        # this evaluator's support/refutation fixed point. Unknown holds remain
        # rejected by the statement scope gate; certified truth holds forbid
        # unconditional positive uses but preserve legitimate scoped judgments.
        self.truth_holds = {c['id']: findings for c in self.store.records('claim')
                            if (findings := self.r._truth_hold_findings(c['id']))}
        self.inferences = []
        for record in self.store.records('inference'):
            if self.store.status(record['id']) != 'accepted' and record['id'] != proposed_inference:
                continue
            data = record['data']
            if not self.r._scope_current(data['conclusion']) or self.r._blocked(record['id']):
                continue
            if not all(self.r._scope_current(i) for i in [data['artifact'], *data['assumptions'], *data['discharge']]):
                continue
            if data['assurance'] == 'formal' and not self.r._formal_current(data.get('formal_receipt')):
                continue
            if not all(self.r._application_current(a) for a in data.get('applications', [])):
                continue
            applications = [self.store.get(a, 'application')['data'] for a in data.get('applications', [])]
            if any(a['conclusion'] != data['conclusion'] or not set(a['mapping'].values()).issubset(data['premises'])
                   for a in applications):
                continue
            try:
                checks = {'validity', 'scope', 'dependencies'}
                if data['discharge']:
                    checks.add('discharge')
                self.r._reviews(record['id'], checks)
            except StateError:
                continue
            self.inferences.append(record)
        self.examples = []
        for record in self.store.records('counterexample'):
            if self.store.status(record['id']) != 'validated' and record['id'] != proposed_counterexample:
                continue
            data = record['data']
            try:
                self.r._counterexample_dependencies(data.get('dependencies', []))
            except StateError:
                continue
            if not self.r._scope_current(record['id']):
                continue
            if data.get('formal_receipt') and not self.r._formal_current(data['formal_receipt']):
                continue
            try:
                checks = {'domain', 'negation', 'scope'}
                if data.get('dependencies'):
                    checks.add('dependencies')
                self.r._reviews(record['id'], checks)
            except StateError:
                continue
            self.examples.append(record)
        self._bounds = None
        self.by_id = {r['id']: r for r in self.inferences}
        self.by_claim = {}
        for record in self.inferences:
            self.by_claim.setdefault(record['data']['conclusion'], []).append(record)
        self._reachable = {}
        self._queries = {}
        self._nodes = {}

    def _assert_snapshot(self):
        if not self.store.db.in_transaction or self.store.revision != self.revision:
            raise StateError('Evidence evaluation cannot outlive its unchanged snapshot')

    def _reachable_inferences(self, claim):
        """Overapproximate all branch exclusions that can affect this query."""
        if claim not in self._reachable:
            reached, claims, pending = set(), set(), [claim]
            while pending:
                current = pending.pop()
                if current in claims:
                    continue
                claims.add(current)
                for record in self.by_claim.get(current, []):
                    reached.add(record['id'])
                    pending.extend(record['data']['premises'])
            self._reachable[claim] = frozenset(reached)
        return self._reachable[claim]

    def _query_key(self, claim, environment, policy, forbidden, diagnostic_root, stack):
        if policy not in {'audited-informal', 'formal-only'}:
            raise StateError('Unknown assurance policy')
        # Exclusions outside this static reachable subgraph cannot affect any
        # descendant. Cyclic regions retain every relevant branch exclusion.
        return (claim, frozenset(environment), policy, frozenset(forbidden), bool(diagnostic_root),
                frozenset(stack) & self._reachable_inferences(claim))

    def _witness_ids(self, claim, environment=frozenset(), *, policy='audited-informal',
                     forbidden=frozenset(), diagnostic_root=False, stack=frozenset()):
        """Select exact finite arguments with snapshot-local, branch-safe sharing.

        Only repeated inference IDs on one branch are circular. Ordered AND
        children retain their first eligible alternative; OR roots remain in
        canonical admission order. This does not enumerate Cartesian products.
        """
        self._assert_snapshot()
        key = self._query_key(claim, environment, policy, forbidden, diagnostic_root, stack)
        if key in self._queries:
            return self._queries[key]

        def frame(query):
            return {'key': query, 'cursor': 0, 'answer': [], 'record': None, 'children': []}

        pending, active = [frame(key)], {key}
        while pending:
            current = pending[-1]
            c, env, assurance, excluded, diagnostic, branch = current['key']
            if current['record'] is None:
                alternatives = self.by_claim.get(c, [])
                if current['cursor'] == len(alternatives):
                    self._queries[current['key']] = tuple(current['answer'])
                    active.remove(current['key'])
                    pending.pop()
                    continue
                record = alternatives[current['cursor']]
                current['cursor'] += 1
                identifier, data = record['id'], record['data']
                if (identifier in branch or not set(data['assumptions']).issubset(env)
                        or (assurance == 'formal-only' and data['assurance'] != 'formal')
                        or (not data['assumptions'] and c in excluded and not diagnostic)):
                    continue
                child_environment = frozenset(data['assumptions'] + data['discharge'])
                current['record'], current['children'] = record, []
                current['child_keys'] = [self._query_key(p, child_environment, assurance, excluded,
                    False, branch | {identifier}) for p in data['premises']]
            child_keys = current['child_keys']
            position = len(current['children'])
            if position < len(child_keys):
                child = child_keys[position]
                if child not in self._queries:
                    if child in active:
                        raise StateError('Circular evaluator query escaped branch exclusion')
                    active.add(child)
                    pending.append(frame(child))
                elif not self._queries[child]:
                    current['record'] = None  # This AND route is ungrounded.
                else:
                    current['children'].append(self._queries[child][0])
                continue
            record = current['record']
            node = {'inference': record['id'], 'inference_hash': record['hash'], 'claim': c,
                    'environment': sorted(env), 'assumptions': list(record['data']['assumptions']),
                    'premises': current['children']}
            identifier = digest(node)
            self._nodes[identifier] = node
            current['answer'].append(identifier)
            current['record'] = None
        return self._queries[key]

    def witnesses(self, claim, environment=frozenset(), *, policy='audited-informal',
                  forbidden=frozenset(), diagnostic_root=False, stack=frozenset()):
        """One exact selected forest per eligible root inference."""
        # With no forbidden set this is raw finite grounding, used only for
        # diagnosis. Consumer derivations, refutation bounds and frozen-tree
        # currentness supply the combined refutation/truth-hold veto.
        return [pack([identifier], self._nodes) for identifier in self._witness_ids(claim, environment,
            policy=policy, forbidden=forbidden, diagnostic_root=diagnostic_root, stack=stack)]

    def _refutation_options(self, forbidden):
        result = {}
        for example in self.examples:
            data = example['data']
            # A refutation cannot rely on the unconditional truth of its target.
            # Scoped occurrences of that target inside a discharged proof are
            # legitimate and are checked by the reviewed inference evidence.
            excluded = forbidden | {data['target']}
            options = [self._witness_ids(p, forbidden=excluded) for p in data.get('dependencies', [])]
            if all(options):
                result[example['id']] = [p[0] for p in options]
        return result

    def bounds(self):
        self._assert_snapshot()
        if self._bounds is not None:
            return self._bounds
        by_id = {e['id']: e for e in self.examples}
        lower, upper = set(), set(by_id)
        for _ in range(2 * len(by_id) + 2):
            low_targets = {by_id[i]['data']['target'] for i in lower} | self.truth_holds.keys()
            high_targets = {by_id[i]['data']['target'] for i in upper} | self.truth_holds.keys()
            certain = self._refutation_options(high_targets)
            possible = self._refutation_options(low_targets)
            next_lower, next_upper = set(certain), set(possible)
            if not (lower <= next_lower <= next_upper <= upper):
                raise StateError('Refutation information bounds are not monotone')
            if (next_lower, next_upper) == (lower, upper):
                self._bounds = {'certain': certain, 'possible': possible,
                    'unresolved': [i for i in by_id if i in upper - lower],
                    'forbidden': high_targets}
                return self._bounds
            lower, upper = next_lower, next_upper
        raise StateError('Finite refutation evaluation failed to converge')

    def derivations(self, claim, environment=frozenset(), *, policy='audited-informal', diagnostic=False):
        return self.witnesses(claim, environment, policy=policy,
            forbidden=self.bounds()['forbidden'], diagnostic_root=diagnostic)

    def refutations(self, claim):
        bounds = self.bounds()
        return [e['id'] for e in self.examples
                if e['data']['target'] == claim and e['id'] in bounds['certain']]

    def view(self, claim, environment=frozenset(), *, policy='audited-informal'):
        # Status packets need root identities, not copies of every full forest.
        grounded = self._witness_ids(claim, environment, policy=policy)
        forbidden = self.bounds()['forbidden']
        diagnostic = self._witness_ids(claim, environment, policy=policy,
                                      forbidden=forbidden, diagnostic_root=True)
        usable = self._witness_ids(claim, environment, policy=policy, forbidden=forbidden)
        refs = self.refutations(claim)
        unresolved = [e['id'] for e in self.examples
            if e['data']['target'] == claim and e['id'] in self.bounds()['unresolved']]
        state = ('conflict' if diagnostic and refs else 'refuted' if refs else 'suspended' if unresolved
                 else 'disputed' if claim in self.truth_holds
                 else 'supported' if diagnostic else 'unsupported')
        blocked = set()
        inspected, pending = set(), list(grounded)
        while pending:
            identifier = pending.pop()
            if identifier in inspected:
                continue
            inspected.add(identifier)
            node = self._nodes[identifier]
            if not node['assumptions'] and node['claim'] in forbidden:
                blocked.add(node['claim'])
            pending.extend(node['premises'])
        return {'id': claim, 'state': state, 'supports': [self._nodes[w]['inference'] for w in diagnostic],
            'grounded_supports': [self._nodes[w]['inference'] for w in grounded], 'negative_use_blockers': sorted(blocked),
            'usable_supports': [self._nodes[w]['inference'] for w in usable], 'refutations': refs,
            'unresolved_refutations': unresolved, 'truth_hold_findings': self.truth_holds.get(claim, {}), 'policy': policy,
            'negative_policy': 'current audited mathematical evidence at every positive assurance',
            'assumptions': sorted(environment), 'revision': self.revision, 'evaluator': EVALUATOR_VERSION,
            'use': 'eligible-in-declared-scope' if usable else 'suspended' if grounded or unresolved or claim in self.truth_holds else 'unavailable'}

    def tree_current(self, witness, environment=frozenset(), *, policy='audited-informal',
                     forbidden=None, stack=frozenset()):
        """Check an exact frozen choice without substituting another derivation."""
        self._assert_snapshot()
        try:
            single_root(witness)
        except StateError:
            return False
        return self.forest_current(witness, environment, policy=policy, forbidden=forbidden, stack=stack)

    def forest_current(self, witness, environment=frozenset(), *, policy='audited-informal',
                       forbidden=None, stack=frozenset()):
        self._assert_snapshot()
        forbidden = (self.bounds()['forbidden'] if forbidden is None else forbidden) | self.truth_holds.keys()
        if policy not in {'audited-informal', 'formal-only'}:
            raise StateError('Unknown assurance policy')
        try:
            table = nodes(witness)
        except StateError:
            return False
        pending = [(root, frozenset(environment), frozenset(stack)) for root in witness['roots']]
        checked = set()
        while pending:
            identifier, env, branch = pending.pop()
            node = table[identifier]
            branch = branch & self._reachable_inferences(node['claim'])
            key = (identifier, env, branch)
            if key in checked:
                continue
            record = self.by_id.get(node['inference'])
            if record is None or record['id'] in branch:
                return False
            data = record['data']
            if (record['hash'] != node['inference_hash'] or data['conclusion'] != node['claim']
                    or node['environment'] != sorted(env) or node['assumptions'] != data['assumptions']
                    or not set(data['assumptions']).issubset(env)
                    or (policy == 'formal-only' and data['assurance'] != 'formal')
                    or (not data['assumptions'] and data['conclusion'] in forbidden)
                    or [table[c]['claim'] for c in node['premises']] != data['premises']):
                return False
            checked.add(key)
            child_environment = frozenset(data['assumptions'] + data['discharge'])
            pending.extend((child, child_environment, branch | {record['id']}) for child in node['premises'])
        return True
