"""Adaptive routes, exact theorem applications, candidates and local learning."""

from __future__ import annotations

import json
from .research import Research, nonempty
from .store import StateError, digest
from .evaluation import Evaluation, EVALUATOR_VERSION
from .witness import merge, nodes, roots


class Campaign(Research):
    def portfolio(self, target: str) -> dict:
        """Current target-scoped research state, advisory to an informed strategist."""
        self.store.get(target, 'claim')
        with self.store.transaction():
            routes, records = [], []
            for route in self.store.records('route'):
                if route['data']['target'] != target:
                    continue
                status = self.store.status(route['id'])
                event = self.store.db.execute('SELECT e.payload,e.hash FROM events e JOIN decisions d '
                    'ON d.event_seq=e.seq WHERE d.target=?', (route['id'],)).fetchone()
                reason = json.loads(event['payload']).get('reason', {})
                certificate = reason.get('certificate')
                from .advisory import Advisory
                route_condition = Advisory(self).condition(route['id'])
                routes.append({'id': route['id'], 'status': status, 'family': route['data']['family'],
                    'decision_hash': event['hash'], 'certificate': certificate,
                    'certificate_current': route_condition['current'], 'condition': route_condition,
                    'reopen_condition': reason.get('reopen_condition')})
                records.append(route['id'])
                if certificate:
                    records.append(certificate)
            route_ids = {r['id'] for r in routes}
            obligations = []
            for obligation in self.store.records('obligation'):
                if obligation['data']['route'] in route_ids:
                    obligations.append({'id': obligation['id'], 'open': self.obligation_open(obligation)})
                    records.append(obligation['id'])
            dispositions = []
            for result in self.store.records('result'):
                data = result['data']
                packet = self.store.get(data['task'], 'task')['data']['packet']
                if packet['claim'] != target:
                    continue
                # A retracted source still leaves advisory historical intelligence.
                for event in self.store.db.execute("SELECT seq,payload,hash FROM events "
                        "WHERE type='decision' AND target=? ORDER BY seq", (result['id'],)):
                    decision = json.loads(event['payload'])
                    if decision.get('status') != 'incorporated':
                        continue
                    reason = decision['reason']
                    dispositions.append({'result': result['id'], 'result_hash': result['hash'],
                        'artifact': data['artifact'], 'artifact_hash': self.store.get(data['artifact'])['hash'],
                        'outcome': data['outcome'], 'decision_revision': event['seq'],
                        'decision_hash': event['hash'], 'reason': reason['reason'],
                        'reopen_condition': reason['reopen_condition'],
                        'followups': [{'id': f, 'hash': self.store.get(f)['hash'],
                                      'status': self.store.status(f)} for f in reason['followups']],
                        'source_records_current': (self.store.status(result['id']) == 'incorporated'
                            and self.store.status(data['run']) == 'completed'
                            and self.store.status(data['task']) == 'completed'
                            and all(self._scope_current(a) for a in [data['artifact'], data['host_receipt'],
                                self.store.get(data['run'], 'run')['data']['dispatch_evidence']])),
                        'mathematical_acceptance': False})
            for execution in self.store.records('execution'):
                if self.store.get(execution['data']['plan'])['data']['target'] != target:
                    continue
                for event in self.store.db.execute("SELECT seq,payload,hash FROM events "
                        "WHERE type='execution-assessment' AND target=? ORDER BY seq", (execution['id'],)):
                    certificate = json.loads(event['payload'])
                    receipt = certificate['receipt']
                    dispositions.append({'execution': execution['id'], 'execution_hash': execution['hash'],
                        'observation': certificate['observation'], 'observation_hash': certificate['observation_hash'],
                        'receipt': receipt, 'receipt_hash': self.store.get(receipt)['hash'] if receipt else None,
                        'outcome': certificate['outcome'],
                        'decision_revision': event['seq'], 'decision_hash': event['hash'],
                        'reason': certificate['reason'], 'reopen_condition': certificate['reopen_condition'],
                        'followups': [{'id': f, 'hash': self.store.get(f)['hash'], 'status': self.store.status(f)}
                                     for f in certificate['followups']],
                        'source_records_current': (self.store.status(execution['id']) in {'completed', 'failed'}
                            and not self._blocked(execution['id']) and self._scope_current(execution['data']['plan'])
                            and self._scope_current(certificate['observation'])
                            and (receipt is None or (self.store.status(receipt) not in {'withdrawn', 'rejected'}
                                                     and not self._blocked(receipt)))),
                        'mathematical_acceptance': False})
            for receipt in self.store.records('formal_receipt'):
                if receipt['data']['target'] != target:
                    continue
                events = list(self.store.db.execute("SELECT seq,payload,hash FROM events "
                        "WHERE type='formal-evidence-disposition' AND target=? ORDER BY seq", (receipt['id'],)))
                for event in events:
                    certificate = json.loads(event['payload'])
                    dispositions.append({'receipt': receipt['id'], 'receipt_hash': receipt['hash'],
                        'outcome': 'deferred-formal-evidence', 'decision_revision': event['seq'],
                        'decision_hash': event['hash'], 'reason': certificate['reason'],
                        'reopen_condition': certificate['reopen_condition'], 'followups': [],
                        'source_records_current': self._formal_current(receipt['id']),
                        'disposition_current': event['seq'] == events[-1]['seq'] and self._formal_disposition_current(receipt['id'], certificate),
                        'mathematical_acceptance': False})
            dispositions.sort(key=lambda item: item['decision_revision'])
            return {'target': target, 'revision': self.store.revision,
                'target_state': self.claim_state(target), 'routes': routes, 'obligations': obligations,
                'dispositions': dispositions,
                'records': list(dict.fromkeys(records)), 'authority': 'research coordination, not mathematical acceptance'}

    def route(self, target: str, strategy: str, *, family: str) -> str:
        self.store.get(target, "claim")
        with self.store.transaction():
            route = self.store.put("route", {"target": target, "strategy": nonempty(strategy, "strategy"),
                                            "family": nonempty(family, "route family")})
            self.store.decide(route, "active", {"reason": "Independent route registered"})
            return route

    def obligation(self, route: str, statement: str, *, claim: str | None = None,
                   relation: str = 'required-for-selected-route', relation_artifact: str | None = None) -> str:
        route_record = self.store.get(route, "route")
        if claim:
            self.store.get(claim, "claim")
        if relation not in {'required-for-selected-route', 'heuristic-reduction', 'comparable-strength-residual'}:
            from .store import InputContractError
            raise InputContractError('Unknown operational obligation relation')
        if relation_artifact:
            self.store.get(relation_artifact, 'artifact')
        with self.store.transaction():
            record = self.store.put("obligation", {"route": route, "statement": nonempty(statement, "obligation"),
                "claim": claim, 'route_target': route_record['data']['target'],
                'route_target_hash': self.store.get(route_record['data']['target'])['hash'],
                'relation': relation, 'relation_artifact': relation_artifact,
                'authority': 'Operational route relation; mathematical implication/equivalence needs explicit reviewed claims and inferences'})
            self.store.decide(record, "open", {"reason": "Unresolved research obligation"})
            return record

    def close_obligation(self, identifier: str, *, expected: int) -> None:
        data = self.store.get(identifier, "obligation")["data"]
        with self.store.transaction(expected):
            if self.store.status(identifier) != 'open':
                raise StateError('Only an open obligation may be satisfied')
            if not self._obligation_structure(identifier) or not self._scope_current(identifier):
                raise StateError('Obligation needs its exact current route/target/relation mapping')
            if not data["claim"] or self.claim_state(data["claim"])["state"] != "supported":
                raise StateError("Obligation needs an unconditionally supported exact claim")
            reviews = self._reviews(identifier, {"obligation-mapping"})
            self.store.decide(identifier, "satisfied", {"claim": data["claim"], "reviews": reviews})

    def obligation_open(self, record: dict) -> bool:
        if self.store.status(record["id"]) != "satisfied":
            return True
        if not self._obligation_structure(record['id']) or not self._scope_current(record['id']):
            return True
        claim = record["data"].get("claim")
        if not claim or self.claim_state(claim)["state"] != "supported":
            return True
        try:
            self._reviews(record["id"], {"obligation-mapping"})
        except StateError:
            return True
        return self._blocked(record["id"])

    def _obligation_structure(self, identifier):
        try:
            return self._exact_obligation_structure(identifier)
        except (StateError, KeyError, TypeError, ValueError):
            return False

    def _exact_obligation_structure(self, identifier):
        d = self.store.get(identifier, 'obligation')['data']
        target = self.store.get(d['route'], 'route')['data']['target']
        if d.get('claim'):
            self.store.get(d['claim'], 'claim')
        if 'route_target' not in d:
            return True  # Historic exact statement/mapping remains a historic contract.
        return (d['route_target'] == target and d['route_target_hash'] == self.store.get(target)['hash']
            and d.get('relation') in {'required-for-selected-route', 'heuristic-reduction', 'comparable-strength-residual'})

    def route_status(self, route: str, status: str, certificate: str, *, reopen_condition: str) -> None:
        self.store.get(route, "route")
        self.store.get(certificate, "artifact")
        if status not in {"active", "blocked", "dormant", "refuted", "closed"}:
            raise StateError("Unknown route state")
        nonempty(reopen_condition, "reopening condition or explanation")
        with self.store.transaction():
            self.store.decide(route, status, {"certificate": certificate, "reopen_condition": reopen_condition})

    def external_theorem(self, statement: str, source: str, source_artifact: str,
                         hypotheses: list[str], definitions: list[str]) -> str:
        self.store.get(source_artifact, "artifact")
        if not isinstance(definitions, list) or any(not isinstance(d, str) or not d.strip() for d in definitions):
            raise StateError("definitions must be an exact list of definition IDs")
        for d in definitions:
            self.store.get(d, "definition")
        if (not isinstance(hypotheses, list)
                or any(not isinstance(h, str) or not h.strip() for h in hypotheses)
                or len(set(hypotheses)) != len(hypotheses)):
            raise StateError("Hypotheses must have distinct nonempty labels")
        with self.store.transaction():
            return self.store.put("external_theorem", {"statement": nonempty(statement, "theorem"),
                "source": nonempty(source, "source/version"), "source_artifact": source_artifact,
                "hypotheses": list(hypotheses), "definitions": list(definitions)})

    def application(self, theorem: str, conclusion: str, mapping: dict[str, str],
                    substitution: str, artifact: str, author: str) -> str:
        if (not isinstance(mapping, dict)
                or any(not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip() for k, v in mapping.items())):
            raise StateError("mapping must be an exact dictionary mapping hypothesis labels to claim IDs")
        source = self.store.get(theorem, "external_theorem")["data"]
        self.store.get(conclusion, "claim")
        self.store.get(artifact, "artifact")
        if set(mapping) != set(source["hypotheses"]):
            raise StateError("Every exact theorem hypothesis must have a mapping, without extras")
        for claim in mapping.values():
            self.store.get(claim, "claim")
        with self.store.transaction():
            return self.store.put("application", {"theorem": theorem, "conclusion": conclusion,
                "mapping": dict(mapping), "substitution": nonempty(substitution, "substitution/domain mapping"),
                "artifact": artifact, "author": nonempty(author, "author")})

    def accept_application(self, identifier: str, *, expected: int) -> str:
        """Qualify an exact conditional rule; grounding remains in its inference."""
        application = self.store.get(identifier, "application")["data"]
        with self.store.transaction(expected):
            if self.store.status(identifier) != 'proposed' or not self._scope_current(identifier):
                raise StateError('Application must be proposed with current source and scope')
            if not self._application_structure(identifier):
                raise StateError('Application must map every exact theorem hypothesis without extras')
            reviews = self._reviews(identifier, {"source", "hypotheses", "substitution", "conclusion"})
            if (self._blocked(identifier) or self._blocked(application["theorem"])
                    or self.store.status(application["theorem"]) == "withdrawn"):
                raise StateError("External source or application is blocked")
            self.store.decide(identifier, "accepted", {"reviews": reviews,
                'meaning': 'qualified exact conditional instantiation; all mapped hypotheses remain mandatory inference premises'})
            return identifier

    def freeze(self, target: str, proof: str, *, author: str, outcome: str = "proof",
               assurance: str = 'audited-informal') -> str:
        self.store.get(target, "claim")
        self.store.get(proof, "artifact")
        if outcome not in {"proof", "disproof"}:
            raise StateError("Candidate outcome must be proof or disproof")
        if assurance not in {'audited-informal', 'machine-checked'}:
            raise StateError('Unknown candidate assurance')
        policy = 'formal-only' if assurance == 'machine-checked' else 'audited-informal'
        with self.store.transaction():
            evaluation = Evaluation(self)
            state = evaluation.view(target, policy=policy)
            contract = self.store.get(self.store.get(target)["data"]["contract"], "contract")["data"]
            if outcome == "disproof" and not contract["allow_disproof"]:
                raise StateError("This contract does not permit a disproof release")
            if state["state"] != ("supported" if outcome == "proof" else "refuted"):
                raise StateError("Freeze requires supported target, with no known refutation")
            # Select one complete derivation. Preserve exact choices rather than
            # silently substituting a different proof after the audit begins.
            refutations = state['refutations']
            if outcome == 'disproof' and assurance == 'machine-checked':
                refutations = [r for r in refutations if self._formal_current(self.store.get(r)['data'].get('formal_receipt'))]
                if not refutations:
                    raise StateError('Disproof has no eligible formal negation receipt')
            options = evaluation.derivations(target, policy=policy) if outcome == 'proof' else []
            if outcome == 'proof' and not options:
                raise StateError('Freeze requires a currently usable unconditional derivation')
            derivation = {'claim': target, 'witness': options[0]} if outcome == 'proof' else None
            if outcome == 'disproof':
                forbidden = evaluation.bounds()['forbidden'] | {target}
                for refutation in refutations:
                    example = self.store.get(refutation)['data']
                    options = [evaluation.witnesses(p, policy=policy, forbidden=forbidden)
                               for p in example.get('dependencies', [])]
                    if all(options):
                        derivation = {'counterexample': refutation, 'claim': target,
                                      'witness': merge([p[0] for p in options])}
                        break
                if derivation is None:
                    raise StateError('Refutation dependencies lack the declared candidate assurance')

            if outcome == 'proof':
                current = evaluation.tree_current(derivation['witness'], policy=policy)
            else:
                current = evaluation.forest_current(derivation['witness'], policy=policy, forbidden=forbidden)
            closure = self._candidate_manifest(target, proof, derivation, outcome)
            if not current or not self._manifest_current(closure):
                raise StateError('Selected candidate witness or proof artifact is not currently usable')
            identifier = self.store.put("candidate", {"target": target, "proof": proof,
                "manifest": closure, "derivation": derivation, "outcome": outcome, 'assurance': assurance,
                'evaluator': EVALUATOR_VERSION,
                "manifest_hash": digest({"records": closure, "derivation": derivation, 'evaluator': EVALUATOR_VERSION}),
                "author": nonempty(author, "author"), "base_snapshot": self.store.revision})
            self.store.decide(identifier, "frozen", {"reason": "Immutable proof/support manifest"})
            return identifier

    def _candidate_manifest(self, target: str, proof: str, derivation: dict, outcome: str) -> dict:
        """Reconstruct the complete mathematical witness; never select alternatives."""
        if not isinstance(derivation, dict) or derivation.get('claim') != target:
            raise StateError('Frozen derivation must establish the exact candidate target')
        expected_fields = {'claim', 'witness'} | ({'counterexample'} if outcome == 'disproof' else set())
        if set(derivation) != expected_fields:
            raise StateError('Malformed frozen derivation')
        table = nodes(derivation['witness'])
        selected_claims = [r['claim'] for r in roots(derivation['witness'])]
        self.store.get(target, 'claim')
        self.store.get(proof, 'artifact')
        closure = {}
        def add_definition(identifier):
            if identifier in closure:
                return
            record = self.store.get(identifier, 'definition')
            closure[identifier] = record['hash']
            for dependency in record['data'].get('dependencies', []):
                add_definition(dependency)

        def add_formal(identifier: str):
            receipt = self.store.get(identifier)
            if receipt['data'].get('receipt_version'):
                from .formal import receipt_evidence
                closure.update(receipt_evidence(self.store, identifier)['records'])
                return
            plan = self.store.get(receipt['data']['plan'])
            records_to_add = [receipt, plan, self.store.get(receipt['data']['source']),
                              self.store.get(plan['data']['source']), self.store.get(receipt['data']['toolchain'])]
            if receipt['data'].get('compiled_artifact'):
                records_to_add.append(self.store.get(receipt['data']['compiled_artifact']))
            for record in records_to_add:
                closure[record['id']] = record['hash']

        def visit(witness: dict):
            claim = witness["claim"]
            self.store.get(claim, "claim")
            selected = witness["inference"]
            record = self.store.get(selected, 'inference')
            closure[selected] = record["hash"]
            closure[claim] = self.store.get(claim)["hash"]
            data = record["data"]
            if data.get('formal_receipt'):
                add_formal(data['formal_receipt'])
            closure[data["artifact"]] = self.store.get(data["artifact"])["hash"]
            current_claim = self.store.get(claim)["data"]
            claim_contract = self.store.get(current_claim["contract"])
            for d in current_claim["definitions"] + claim_contract["data"]["definitions"]:
                add_definition(d)
            closure[claim_contract["id"]] = claim_contract["hash"]
            for app in data.get("applications", []):
                app_record = self.store.get(app)
                theorem = self.store.get(app_record["data"]["theorem"])
                for entry in [app_record, theorem, self.store.get(app_record["data"]["artifact"]),
                              self.store.get(theorem["data"]["source_artifact"])]:
                    closure[entry["id"]] = entry["hash"]
                for d in theorem["data"]["definitions"]:
                    add_definition(d)
            for a in data["assumptions"] + data["discharge"]:
                closure[a] = self.store.get(a)["hash"]
        if outcome == 'proof':
            if selected_claims != [target]:
                raise StateError('Frozen proof has a different root')
        elif outcome == 'disproof':
            refutation = self.store.get(derivation['counterexample'], 'counterexample')
            if refutation['data']['target'] != target:
                raise StateError('Frozen refutation targets another claim')
            if refutation['data'].get('formal_receipt'):
                add_formal(refutation['data']['formal_receipt'])
            for record in [self.store.get(target), refutation, self.store.get(refutation['data']['artifact'])]:
                closure[record['id']] = record['hash']
            if selected_claims != refutation['data'].get('dependencies', []):
                raise StateError('Frozen refutation omits or changes ordered dependencies')
        else:
            raise StateError('Unknown candidate outcome')
        for witness in table.values():
            visit(witness)
        claim = self.store.get(target)['data']
        closure[claim['contract']] = self.store.get(claim['contract'])['hash']
        closure[proof] = self.store.get(proof)['hash']
        for definition in claim['definitions'] + self.store.get(claim['contract'])['data']['definitions']:
            add_definition(definition)
        return closure

    def _manifest_current(self, manifest: dict) -> bool:
        for identifier, hashed in manifest.items():
            record = self.store.get(identifier)
            if record['hash'] != hashed or not self._scope_current(identifier):
                return False
            if record['kind'] == 'formal_receipt' and not self._formal_current(identifier):
                return False
        return True

    def candidate_current(self, identifier: str) -> bool:
        with self.store.transaction():
            return self._candidate_current(identifier)

    def _candidate_current(self, identifier: str) -> bool:
        candidate = self.store.get(identifier, 'candidate')['data']
        if (candidate.get('evaluator') != EVALUATOR_VERSION
                or self.store.status(identifier) not in {'frozen', 'audited'} or self._blocked(identifier)):
            return False
        try:
            outcome, assurance = candidate['outcome'], candidate['assurance']
            if outcome not in {'proof', 'disproof'} or assurance not in {'audited-informal', 'machine-checked'}:
                return False
            policy = 'formal-only' if assurance == 'machine-checked' else 'audited-informal'
            target, derivation = candidate['target'], candidate['derivation']
            closure = self._candidate_manifest(target, candidate['proof'], derivation, outcome)
            if (candidate['manifest'] != closure or candidate['manifest_hash'] != digest({
                    'records': closure, 'derivation': derivation, 'evaluator': EVALUATOR_VERSION})):
                return False
            evaluation = Evaluation(self)
            if evaluation.view(target, policy=policy)['state'] != ('supported' if outcome == 'proof' else 'refuted'):
                return False
            if outcome == 'proof':
                if not evaluation.tree_current(derivation['witness'], policy=policy):
                    return False
            else:
                selected = derivation['counterexample']
                if selected not in evaluation.refutations(target):
                    return False
                example = self.store.get(selected)['data']
                if assurance == 'machine-checked' and not self._formal_current(example.get('formal_receipt')):
                    return False
                forbidden = evaluation.bounds()['forbidden'] | {target}
                if not evaluation.forest_current(derivation['witness'], policy=policy, forbidden=forbidden):
                    return False
            return self._manifest_current(closure)
        except (StateError, KeyError, TypeError, ValueError):
            return False  # Invalid/imported records cannot bypass the normal freeze writer.

    def audit_candidate(self, identifier: str, *, expected: int) -> None:
        with self.store.transaction(expected):
            if not self.candidate_current(identifier):
                raise StateError("Frozen candidate has stale or invalidated support")
            reviews = self._candidate_reviews(identifier)
            self.store.decide(identifier, "audited", {"reviews": reviews})

    def _candidate_checks(self, identifier: str) -> set[str]:
        data = self.store.get(identifier, "candidate")["data"]
        checks = {"full-refutation" if data.get("outcome") == "disproof" else "full-proof",
                  "target-fidelity", "dependency-closure", "falsification"}
        if data.get('assurance') == 'machine-checked':
            checks |= {'formal-target-fidelity', 'formal-environment'}
        return checks

    def _audit_reviews(self, identifier: str) -> list[str]:
        if self.store.status(identifier) != 'audited' or not self.candidate_current(identifier):
            raise StateError('Candidate has no current audit decision')
        event = self.store.db.execute('SELECT e.payload FROM events e JOIN decisions d '
            'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
        witnesses = json.loads(event['payload']).get('reason', {}).get('reviews')
        if not isinstance(witnesses, list) or not witnesses or any(not isinstance(w, str) for w in witnesses):
            raise StateError('Candidate audit decision lacks its exact review witnesses')
        return self._candidate_reviews(identifier, witnesses=witnesses)

    def candidate_audit_current(self, identifier: str) -> bool:
        try:
            self._audit_reviews(identifier)
        except StateError:
            return False
        return True

    def _candidate_reviews(self, identifier: str, *, witnesses: list[str] | None = None) -> list[str]:
        condition = self._candidate_review_condition(identifier, witnesses=witnesses)
        if not condition['current']:
            raise StateError(condition['reason'])
        return condition['reviews']

    def _candidate_review_condition(self, identifier: str, *, witnesses: list[str] | None = None) -> dict:
        from .finalization import candidate_report_condition
        reports = candidate_report_condition(self, identifier)
        if not reports['current']:
            return {'current': False, 'reviews': [], 'missing': [], 'missing_responsibilities': [],
                    'pending_reports': reports['pending_reports'], 'reason': reports['reason']}
        checks = self._candidate_checks(identifier)
        condition = self._review_condition(identifier, checks, witnesses=witnesses)
        reviews = condition['reviews']
        roles = {'full-proof': {'referee'}, 'full-refutation': {'referee'},
                 'target-fidelity': {'fidelity-auditor'}, 'falsification': {'falsifier'},
                 'dependency-closure': {'referee', 'theorem-checker'},
                 'formal-target-fidelity': {'fidelity-auditor'},
                 'formal-environment': {'referee', 'theorem-checker'}}
        covered = set()
        for identifier in reviews:
            data = self.store.get(identifier, 'review')['data']
            task = self.store.get(data['provenance']['task'], 'task')['data']['packet']
            for check in data['checks']:
                if check in roles and task['role'] in roles[check]:
                    covered.add(check)
        if not condition['current']:
            return {**condition, 'missing_responsibilities': sorted(checks - covered)}
        if not checks.issubset(covered):
            return {**condition, 'current': False, 'missing_responsibilities': sorted(checks - covered),
                    'reason': 'Candidate audit needs distinct native proof, fidelity and falsification responsibilities'}
        return {**condition, 'missing_responsibilities': []}

    def release(self, candidate: str, *, expected: int, assurance: str,
                supersedes: str | None = None, reason: str | None = None) -> str:
        if assurance not in {'audited-informal', 'machine-checked'}:
            raise StateError('Unknown release assurance')
        with self.store.transaction(expected):
            record = self.store.get(candidate, "candidate")
            if record['data'].get('assurance', 'audited-informal') != assurance:
                raise StateError('Release cannot upgrade the frozen assurance by relabeling')
            if self.store.status(candidate) != "audited" or not self.candidate_current(candidate):
                raise StateError("Release requires current audited candidate")
            prior = [r for r in self.store.records('release')
                     if r['data']['target'] == record['data']['target']
                     and r['data']['manifest_hash'] == record['data']['manifest_hash']]
            if prior:
                latest = prior[-1]['id']
                if (supersedes is None and reason is None and prior[-1]['data']['candidate'] == candidate
                        and self.release_current(latest)):
                    return latest
                if supersedes != latest or self._blocked(latest):
                    raise StateError('Republication must name the latest release and resolve its findings')
                nonempty(reason, 'republication reason')
            elif supersedes is not None:
                raise StateError('First release cannot supersede another publication')
            if reason is not None:
                nonempty(reason, 'publication reason')
            reviews = self._audit_reviews(candidate)
            release = self.store.put("release", {"candidate": candidate, "target": record["data"]["target"],
                "manifest_hash": record["data"]["manifest_hash"], "assurance": assurance, "reviews": reviews,
                "outcome": record["data"].get("outcome", "proof"),
                "supersedes": supersedes, "reason": reason})
            if supersedes:
                self.store.decide(supersedes, 'superseded', {'release': release, 'reason': reason})
            self.store.decide(release, "released", {"candidate": candidate, "assurance": assurance})
            return release

    def release_current(self, identifier: str) -> bool:
        try:
            return self._release_current(identifier)
        except (StateError, KeyError, TypeError, ValueError):
            return False

    def _release_current(self, identifier: str) -> bool:
        data = self.store.get(identifier, 'release')['data']
        if self.store.status(identifier) != 'released' or self._blocked(identifier):
            return False
        frozen = self.store.get(data['candidate'], 'candidate')['data']
        if any(data[k] != frozen[k] for k in ('target', 'manifest_hash', 'assurance', 'outcome')):
            return False
        registered = self.store.db.execute("SELECT seq FROM events WHERE type='registered' AND target=?",
                                           (identifier,)).fetchone()['seq']
        audit = self.store.db.execute("SELECT payload FROM events WHERE type='decision' AND target=? AND seq<? "
            'ORDER BY seq DESC LIMIT 1', (data['candidate'], registered)).fetchone()
        decision = json.loads(audit['payload']) if audit else {}
        if decision.get('status') != 'audited' or decision.get('reason', {}).get('reviews') != data['reviews']:
            return False
        publications = self.store.records('release')
        prior = []
        for publication in publications:
            if publication['id'] == identifier:
                break
            if (publication['data'].get('target') == data['target']
                    and publication['data'].get('manifest_hash') == data['manifest_hash']):
                prior.append(publication['id'])
        if data.get('supersedes') != (prior[-1] if prior else None):
            return False
        if prior:
            if not isinstance(data.get('reason'), str) or not data['reason'].strip():
                return False
            previous = [json.loads(r['payload']) for r in self.store.db.execute(
                "SELECT payload FROM events WHERE type='decision' AND target=? AND seq>?", (prior[-1], registered))]
            if not any(p.get('status') == 'superseded' and p.get('reason', {}).get('release') == identifier for p in previous):
                return False
        if not self.candidate_current(data['candidate']) or self.store.status(data['candidate']) != 'audited':
            return False
        try:
            self._candidate_reviews(data['candidate'], witnesses=data['reviews'])
        except StateError:
            return False
        return True

    def _formal_references(self, receipt: str) -> list[dict]:
        """Exact pending/useful routes; historical acceptance alone is not use."""
        references = []
        for kind in ('inference', 'counterexample'):
            for record in self.store.records(kind):
                data, identifier = record['data'], record['id']
                if data.get('formal_receipt') != receipt:
                    continue
                status, use = self.store.status(identifier), 'unusable'
                if status == 'proposed':
                    links = ([data['conclusion'], data['artifact'], *data['premises'], *data['assumptions'],
                              *data['discharge'], *data.get('applications', [])]
                             if kind == 'inference' else [identifier])
                    if not self._blocked(identifier) and all(self._scope_current(i) for i in links):
                        use = 'pending'
                elif kind == 'inference' and status == 'accepted':
                    policy = 'formal-only' if data['assurance'] == 'formal' else 'audited-informal'
                    if identifier in self.eligible_supports(data['conclusion'], set(data['assumptions']), policy=policy):
                        use = 'incorporated'
                elif kind == 'counterexample' and status == 'validated' and identifier in self._refutations(data['target']):
                    use = 'incorporated'
                references.append({'id': identifier, 'kind': kind, 'status': status, 'use': use})
        return references

    def _formal_disposition_basis(self, receipt: str, references: list[dict], basis_sources=None) -> dict:
        target = self.store.get(receipt, 'formal_receipt')['data']['target']
        return {'receipt': self._source_semantics(receipt), 'target': self._source_semantics(target),
                'references': {r['id']: self._source_semantics(r['id']) for r in references},
                'rationale_sources': {s: self._source_semantics(s) for s in basis_sources or []}}

    def _formal_disposition_current(self, receipt: str, certificate: dict) -> bool:
        return (certificate.get('disposition') == 'deferred'
                and certificate.get('receipt_hash') == self.store.get(receipt)['hash']
                and self._formal_current(receipt)
                and certificate.get('basis_hash') == digest(certificate.get('basis'))
                and certificate.get('basis_hash') == digest(self._formal_disposition_basis(receipt,
                    self._formal_references(receipt), certificate.get('basis_sources', []))))

    def learning(self, summary: str, sources: list[str], *, category: str, reopen_condition: str,
                 target=None, applicability=None, origin=None) -> str:
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or not s.strip() for s in sources)):
            raise StateError("Local learning requires exact source records")
        for source in sources:
            self.store.get(source)
        if category not in {"failed-mechanism", "counterexample", "structural-insight", "theorem-trap", "reopen"}:
            raise StateError("Unknown learning category")
        if target is not None:
            self.store.get(target, 'claim')
            nonempty(applicability, 'learning applicability')
        if origin is not None:
            from .curation import CURATION_PROFILE, Curation
            candidate = self.store.get(origin['candidate'], 'learning_candidate')
            if (origin.get('profile') != CURATION_PROFILE or candidate['hash'] != origin['candidate_hash']
                    or candidate['data']['target'] != target or candidate['data']['boundary'] != origin['boundary']
                    or self.store.status(candidate['id']) != 'curated'
                    or not Curation(self).candidate_current(candidate['id'])
                    or not set(candidate['data']['sources']).issubset(sources)):
                raise StateError('Curated learning must retain its exact extraction lineage')
        with self.store.transaction():
            return self.store.put("learning", {"summary": nonempty(summary, "summary"),
                'target': target, 'applicability': applicability, 'origin': origin,
                'curation': 'root-curated-extraction' if origin else 'explicit-root-manual',
                'mathematical_acceptance': False,
                "sources": {s: self.store.get(s)["hash"] for s in sources}, "category": category,
                "source_status": {s: self.store.status(s) for s in sources},
                "source_semantics": {s: self._source_semantics(s) for s in sources},
                "reopen_condition": nonempty(reopen_condition, "reopening condition")})

    def learning_current(self, identifier: str) -> bool:
        try:
            return self._learning_current(identifier)
        except (StateError, KeyError, TypeError, ValueError, RecursionError):
            return False

    def _learning_current(self, identifier: str) -> bool:
        with self.store.transaction():
            data = self.store.get(identifier, 'learning')['data']
            if (not isinstance(data.get('sources'), dict) or not data['sources']
                    or not isinstance(data.get('source_status'), dict) or set(data['source_status']) != set(data['sources'])
                    or not isinstance(data.get('source_semantics'), dict) or set(data['source_semantics']) != set(data['sources'])
                    or data.get('category') not in {'failed-mechanism', 'counterexample', 'structural-insight', 'theorem-trap', 'reopen'}
                    or not all(isinstance(data.get(k), str) and data[k].strip() for k in ('summary', 'reopen_condition'))):
                return False
            if (self.store.status(identifier) != 'proposed' or self._blocked(identifier)
                    or data.get('mathematical_acceptance', False) is not False
                    or data.get('curation') not in {None, 'explicit-root-manual', 'root-curated-extraction'}):
                return False
            if data.get('target') is not None:
                self.store.get(data['target'], 'claim')
                nonempty(data.get('applicability'), 'learning applicability')
            event = self.store.db.execute('SELECT e.type,e.payload FROM events e JOIN decisions d '
                'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
            if event['type'] == 'decision' and json.loads(event['payload']).get('reason', {}).get('mathematical_acceptance', False) is not False:
                return False
            if data.get('origin'):
                from .curation import CURATION_PROFILE
                candidate = self.store.get(data['origin']['candidate'], 'learning_candidate')
                if (data['origin'].get('profile') != CURATION_PROFILE or candidate['hash'] != data['origin']['candidate_hash']
                        or candidate['data']['target'] != data.get('target')
                        or candidate['data']['category'] != data['category']
                        or candidate['data']['boundary'] != data['origin']['boundary']
                        or candidate['data']['basis'] != data['source_semantics']
                        or not set(candidate['data']['sources']).issubset(data['sources'])):
                    return False
            for source, hashed in data['sources'].items():
                if (self.store.get(source)['hash'] != hashed
                        or self.store.status(source) != data['source_status'][source]
                        or self._source_semantics(source) != data['source_semantics'][source]):
                    return False
            return True

    def _source_semantics(self, identifier: str):
        from .learning import source_basis
        return source_basis(self, identifier)

    def progress(self) -> dict:
        with self.store.transaction():
            return self._progress()

    def _progress(self) -> dict:
        from .completion import Completion
        claims = [self.claim_state(c["id"]) for c in self.store.records("claim")]
        obligations = [o["id"] for o in self.store.records("obligation") if self.obligation_open(o)]
        objections = [o["id"] for o in self.store.records("objection") if self.finding_blocking(o['id'])]
        findings = objections + [r['id'] for r in self.store.records('review')
                                if r['data']['verdict'] == 'fail' and self.finding_blocking(r['id'])]
        effects = {f: self.finding_effects(f) for f in findings}
        unresolved = [f for f in findings if not effects[f]['substantive_current']]
        repairs = [f for f in findings if effects[f]['substantive_current'] and effects[f]['statement_scope_hold']
                   and self.store.status(self.store.get(f)['data']['target']) not in {'withdrawn', 'rejected'}]
        releases = []
        for release in self.store.records("release"):
            releases.append({"id": release["id"], "current": self.release_current(release['id']),
                             "status": self.store.status(release['id']),
                             "candidate": release['data']['candidate'],
                             "assurance": release["data"]["assurance"]})
        published_manifests = {(r['data']['target'], r['data']['manifest_hash']) for r in self.store.records('release')}
        ready, reaudit = [], []
        for candidate in self.store.records('candidate'):
            identifier = candidate['id']
            if (self.store.status(identifier) != 'audited'
                    or not self.candidate_current(identifier)):
                continue
            try:
                self._audit_reviews(identifier)
            except StateError:
                reaudit.append(identifier)
                continue
            if (candidate['data']['target'], candidate['data']['manifest_hash']) not in published_manifests:
                ready.append(identifier)
        if unresolved:
            next_action = {"action": "adjudicate", "targets": unresolved}
        elif any(c['state'] == 'suspended' for c in claims):
            next_action = {'action': 'investigate-refutation-cycle',
                           'targets': [c['id'] for c in claims if c['state'] == 'suspended']}
        elif any(c["state"] == "conflict" for c in claims):
            next_action = {"action": "investigate-conflict", "targets": [c["id"] for c in claims if c["state"] == "conflict"]}
        elif repairs:
            next_action = {'action': 'repair-validated-findings', 'targets': repairs}
        elif any(c['state'] == 'disputed' for c in claims):
            next_action = {'action': 'investigate-disputed-claims', 'targets': [c['id'] for c in claims if c['state'] == 'disputed']}
        elif obligations:
            next_action = {"action": "research-obligations", "targets": obligations}
        else:
            frozen = [c["id"] for c in self.store.records("candidate") if self.store.status(c["id"]) == "frozen" and self.candidate_current(c["id"])]
            next_action = ({'action': 'release-candidate', 'targets': ready, 'automatic_release': False}
                           if ready else {'action': 'reaudit-candidate', 'targets': reaudit}
                           if reaudit else {"action": "audit" if frozen else "explore", "targets": frozen})
        requests = [r for r in self.store.records('completion_request') if self.store.status(r['id']) == 'active']
        drafts = [r['id'] for r in self.store.records('completion_request') if self.store.status(r['id']) == 'draft']
        fulfillment = [Completion(self).fulfillment(r['id']) for r in requests]
        math = bool(fulfillment) and all(r['mathematics_sufficient'] for r in fulfillment)
        fulfilled = math and all(r['contract_fulfilled'] for r in fulfillment)
        if math:
            next_action = {'action': 'contract-fulfilled' if fulfilled else 'finish-requested-delivery',
                'requests': [r['request'] for r in fulfillment], 'further_research': 'optional',
                'maintenance': [m for r in fulfillment for m in r['maintenance']]}
        return {"revision": self.store.revision, "claims": claims, "open_obligations": obligations,
                'unresolved_findings': unresolved, 'validated_scope_repairs': repairs,
                "open_objections": objections, "releases": releases, "release_ready": ready,
                'reaudit_needed': reaudit, "next": next_action,
                'completion_bound': bool(requests), 'completion_requests': fulfillment,
                'draft_completion_requests': drafts, 'mathematics_sufficient': math,
                'contract_fulfilled': fulfilled, 'research_exhaustion': 'not-claimed'}
