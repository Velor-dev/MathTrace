"""Mathematical research operations and policy-relative support evaluation.

Independent review is an evidence requirement, not an oracle. The runtime checks
identities, scope declarations and provenance; reviewers check the mathematics.
"""

from __future__ import annotations

import json
from typing import Any

from .store import Store, StateError, InputContractError, digest
from .witness import single_root
from .formal import RECEIPT_VERSION, RECEIPT_VERSIONS, PROFILE, receipt_evidence


def nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateError(f"{name} must be nonempty text")
    return value


class Research:
    def __init__(self, store: Store):
        self.store = store

    def artifact(self, text: str, media_type: str = "text/markdown") -> str:
        nonempty(text, "artifact")
        with self.store.transaction():
            return self.store.put("artifact", {"text": text, "media_type": media_type,
                                               "content_hash": digest(text)})

    def contract(self, statement: str, definitions: list[str], *,
                 completion: str, allow_disproof: bool = True,
                 allowed_axioms: list[str] | None = None) -> str:
        nonempty(statement, "original statement")
        nonempty(completion, "completion criterion")
        if type(allow_disproof) is not bool:
            raise StateError("allow_disproof must be an exact boolean")
        if not isinstance(definitions, list):
            raise StateError("definitions must be an exact list of definition record IDs")
        for definition in definitions:
            self.store.get(definition, "definition")
        if allowed_axioms is not None:
            if not isinstance(allowed_axioms, list):
                raise StateError("allowed_axioms must be an exact list of strings or None")
            for axiom in allowed_axioms:
                if not isinstance(axiom, str) or not axiom.strip():
                    raise StateError("allowed_axioms entries must be nonempty strings")
            if len(allowed_axioms) != len(set(allowed_axioms)):
                raise StateError("allowed_axioms must not contain duplicate entries")
            if "sorryAx" in allowed_axioms:
                raise StateError("Invalid axiom policy; sorryAx cannot be admitted")
        with self.store.transaction():
            record = self.store.put("contract", {"statement": statement, "definitions": definitions,
                                                "completion": completion, "allow_disproof": allow_disproof,
                                                "allowed_axioms": ['propext', 'Classical.choice', 'Quot.sound'] if allowed_axioms is None else allowed_axioms})
            self.store.decide(record, "active", {"reason": "Explicit research contract"})
            return record

    def definition(self, name: str, text: str, dependencies: list[str] | None = None) -> str:
        if dependencies is not None:
            if not isinstance(dependencies, list) or any(not isinstance(d, str) or not d.strip() for d in dependencies):
                raise StateError("dependencies must be an exact list of definition IDs or None")
        for dependency in dependencies or []:
            self.store.get(dependency, "definition")
        with self.store.transaction():
            return self.store.put("definition", {"name": nonempty(name, "name"),
                                                "text": nonempty(text, "definition"),
                                                "dependencies": list(dependencies) if dependencies else []})

    def assumption(self, text: str) -> str:
        with self.store.transaction():
            return self.store.put("assumption", {"text": nonempty(text, "assumption")})

    def claim(self, statement: str, contract: str, *, definitions: list[str] | None = None,
              previous: str | None = None) -> str:
        self.store.get(contract, "contract")
        if definitions is not None and (not isinstance(definitions, list) or any(not isinstance(d, str) or not d.strip() for d in definitions)):
            raise StateError("definitions must be an exact list of definition record IDs or None")
        for definition in definitions or []:
            self.store.get(definition, "definition")
        if previous:
            self.store.get(previous, "claim")
        with self.store.transaction():
            return self.store.put("claim", {"statement": nonempty(statement, "statement"),
                                           "contract": contract, "definitions": list(definitions) if definitions else [],
                                           "previous": previous})

    def inference(self, conclusion: str, premises: list[str], artifact: str, author: str, *,
                  assumptions: list[str] | None = None, discharge: list[str] | None = None,
                  rule: str = "argument", assurance: str = "informal",
                  applications: list[str] | None = None, formal_receipt: str | None = None) -> str:
        self.store.get(conclusion, "claim")
        if not isinstance(premises, list):
            raise StateError("premises must be an exact list of claim IDs")
        for premise in premises:
            self.store.get(premise, "claim")
        self.store.get(artifact, "artifact")
        if assumptions is not None and not isinstance(assumptions, list):
            raise StateError("assumptions must be an exact list of assumption IDs or None")
        if discharge is not None and not isinstance(discharge, list):
            raise StateError("discharge must be an exact list of assumption IDs or None")
        if applications is not None and not isinstance(applications, list):
            raise StateError("applications must be an exact list of application IDs or None")
        assumptions, discharge = assumptions or [], discharge or []
        for assumption in assumptions + discharge:
            self.store.get(assumption, "assumption")
        if set(assumptions) & set(discharge):
            raise InputContractError("Discharged assumptions must not remain in the output environment")
        if discharge and rule not in {"implication-introduction", "contradiction", "scoped-derivation"}:
            raise InputContractError("Assumption discharge requires an explicit scoped rule")
        if assurance not in {"informal", "formal"}:
            raise StateError('Unknown inference assurance')
        if assurance == 'formal':
            if formal_receipt is None:
                raise StateError('Formal assurance requires a checked receipt')
            receipt = self.store.get(formal_receipt, 'formal_receipt')['data']
            if (receipt['target'] != conclusion or receipt.get('outcome', 'proof') != 'proof'
                    or set(receipt['assumptions']) != set(assumptions) or discharge):
                raise StateError('Formal receipt target, outcome or assumption scope differs')
        elif formal_receipt is not None:
            raise StateError('Declare formal assurance when linking a formal receipt')
        applications = applications or []
        premises = list(premises)
        for application in applications:
            data = self.store.get(application, "application")["data"]
            if data["conclusion"] != conclusion:
                raise InputContractError("External application must establish this exact conclusion")
            premises.extend(data["mapping"].values())
        with self.store.transaction():
            return self.store.put("inference", {
                "conclusion": conclusion, "premises": list(dict.fromkeys(premises)),
                "artifact": artifact, "author": nonempty(author, "author identity"),
                "assumptions": sorted(set(assumptions)), "discharge": sorted(set(discharge)),
                "rule": nonempty(rule, "rule"), "assurance": assurance,
                "applications": applications,
                "formal_receipt": formal_receipt,
                "base_snapshot": self.store.revision,
            })

    def review(self, target: str, reviewer: str, run_id: str, verdict: str,
               artifact: str, checks: list[str], *, exposure: str = "independent") -> str:
        record = self.store.get(target)
        self.store.get(artifact, "artifact")
        if verdict not in {"pass", "fail", "inconclusive"}:
            raise StateError("Review verdict must be pass, fail, or inconclusive")
        if exposure not in {"independent", "reported-independent", "informed", "self-review", "unknown"}:
            raise StateError("Unknown review exposure")
        nonempty(reviewer, "reviewer")
        nonempty(run_id, "review run")
        if reviewer == record["data"].get("author") and exposure == "independent":
            raise StateError("An author cannot supply the independent review of their own artifact")
        if not isinstance(checks, list) or not checks or any(not isinstance(c, str) or not c.strip() for c in checks):
            raise StateError("Review must declare exact checks performed")
        from .context import Tasks
        provenance = Tasks(self).review_provenance(run_id, target, verdict, artifact, checks)
        if reviewer != provenance["conversation_id"] or exposure != provenance["exposure"]:
            raise StateError("Reviewer identity/exposure must match the native task receipt")
        with self.store.transaction():
            if any(r["data"]["run_id"] == run_id for r in self.store.records("review")):
                raise StateError("A native result cannot be counted as another review")
            return self.store.put("review", {"target": target, "target_hash": record["hash"],
                "reviewer": reviewer, "run_id": run_id, "verdict": verdict,
                "artifact": artifact, "checks": sorted(set(checks)), "exposure": exposure,
                "base_snapshot": self.store.revision, "provenance": provenance})

    def _reviews(self, target: str, required: set[str], *, witnesses: list[str] | None = None,
                 disputes: frozenset = frozenset()) -> list[str]:
        """Fail-closed review coverage; negative reviews are not outvoted."""
        condition = self._review_condition(target, required, witnesses=witnesses, disputes=disputes)
        if not condition['current']:
            raise StateError(condition['reason'])
        return condition['reviews']

    def _review_condition(self, target: str, required: set[str], *, witnesses: list[str] | None = None,
                          disputes: frozenset = frozenset()) -> dict:
        """Describe the same qualification gate used by promotion, without raising."""
        record = self.store.get(target)
        passes, covered, ineligible = [], set(), {}
        for review in self.store.records("review"):
            data = review["data"]
            if data["target"] != target or data["target_hash"] != record["hash"]:
                continue
            if data["verdict"] == "fail":
                if self.finding_blocking(review['id'], disputes):
                    return {'current': False, 'reviews': [], 'missing': sorted(required),
                            'finding': review['id'], 'reason': 'Unresolved failing review blocks promotion'}
                continue
            if witnesses is not None and review['id'] not in witnesses:
                continue
            if self.store.status(review['id']) in {'withdrawn', 'dismissed', 'provenance-retracted'}:
                ineligible[review['id']] = {'reason': 'review-disposition', 'status': self.store.status(review['id'])}
                continue
            if data["verdict"] == "pass" and data["reviewer"] != record["data"].get("author"):
                from .context import Tasks
                try:
                    provenance = Tasks(self).review_provenance(data["run_id"], target,
                        data["verdict"], data["artifact"], data["checks"])
                except StateError as error:
                    ineligible[review['id']] = {'reason': 'producer-provenance', 'detail': str(error)}
                    continue
                holds = {e: findings for e in self._review_evidence_ids(review['id'])
                         if (findings := self._blocking_findings(e, disputes | {review['id']}))}
                if holds:
                    ineligible[review['id']] = {'reason': 'producer-or-review-finding', 'holds': holds}
                    continue
                if provenance.get('native_context_current') is False:
                    ineligible[review['id']] = {'reason': 'native-recorded-input-admission-not-current'}
                    continue
                if record['kind'] == 'adjudication':
                    task = self.store.get(provenance['task'], 'task')['data']['packet']
                    if (task['role'] != 'adjudicator' or task['independence'] != 'informed'
                            or provenance['qualification_scope'] != 'observed-public-task-context'
                            or data['reviewer'] in record['data']['parties']
                            or any(e['data']['run'] == data['run_id'] for e in self.store.records('exposure'))):
                        ineligible[review['id']] = {'reason': 'adjudicator-role-party-or-exposure',
                            'exposures': [e['id'] for e in self.store.records('exposure') if e['data']['run'] == data['run_id']]}
                        continue
                elif data['exposure'] != 'independent' or provenance['exposure'] != 'independent':
                    ineligible[review['id']] = {'reason': 'independence-not-qualified', 'provenance': provenance}
                    continue
                passes.append(review["id"])
                covered.update(data["checks"])
        if witnesses is not None and set(passes) != set(witnesses):
            return {'current': False, 'reviews': passes, 'missing': sorted(required - covered),
                    'lost_witnesses': sorted(set(witnesses) - set(passes)),
                    'ineligible': ineligible,
                    'reason': 'An exact review witness is no longer eligible'}
        if not passes or not required.issubset(covered):
            return {'current': False, 'reviews': passes, 'missing': sorted(required - covered),
                    'ineligible': ineligible,
                    'reason': 'Independent review coverage is incomplete'}
        return {'current': True, 'reviews': passes, 'missing': [], 'reason': None}

    def finding_blocking(self, identifier: str, disputes: frozenset = frozenset()) -> bool:
        """Retraction of provenance never silently disposes of a negative finding."""
        record = self.store.get(identifier)
        from .finalization import report_source
        if record['kind'] == 'result' and report_source(record):
            if identifier in disputes:
                return True
            row = self.store.db.execute("SELECT payload FROM events WHERE type='counterexample-report-disposed' "
                'AND target=? ORDER BY seq DESC LIMIT 1', (identifier,)).fetchone()
            resolution = json.loads(row['payload']).get('resolution') if row else None
            return not resolution or not self._resolution_current(resolution, identifier, disputes | {identifier})
        if record['kind'] != 'objection' and not report_source(record) and not (record['kind'] == 'review' and record['data']['verdict'] == 'fail'):
            raise StateError('Not a negative finding')
        if identifier in disputes or self.store.status(identifier) != 'dismissed':
            return True
        event = self.store.db.execute('SELECT e.payload FROM events e JOIN decisions d '
            'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
        resolution = json.loads(event['payload']).get('reason', {}).get('resolution')
        return not resolution or not self._resolution_current(resolution, identifier, disputes | {identifier})

    def _resolution_current(self, identifier: str, finding: str, disputes: frozenset) -> bool:
        return self._qualified_resolution_current(identifier, finding, 'dismissed', disputes)

    def _qualified_resolution_current(self, identifier: str, finding: str, disposition: str,
                                       disputes: frozenset = frozenset()) -> bool:
        if identifier in disputes or self.store.status(identifier) in {'withdrawn', 'rejected'}:
            return False
        record = self.store.get(identifier, 'resolution')['data']
        if record.get('finding', record.get('objection')) != finding or record['disposition'] != disposition:
            return False
        trail = disputes | {identifier}
        if self._blocked(identifier, trail):
            return False
        case_id = record.get('case')
        if case_id:
            case = self.store.get(case_id, 'adjudication')['data']
            if (case['finding'] != finding or case['disposition'] != disposition
                    or self.store.status(case_id) != 'resolved'
                    or not self._adjudication_current(case_id, trail)):
                return False
            target, checks = case_id, self._adjudication_checks(case)
        else:
            if disposition != 'dismissed':
                return False
            # Read earlier exact-objection resolutions, without allowing witness substitution.
            target, checks = finding, {'objection-scope', 'dismissed'}
        try:
            self._reviews(target, checks, witnesses=record['reviews'], disputes=trail)
        except StateError:
            return False
        return True

    def _finding_scope_certificate(self, finding: str, disputes: frozenset = frozenset()) -> str | None:
        """Current scope-only evidence; never validation of the finding's truth."""
        if finding in disputes:
            return None
        record = self.store.get(finding)
        subject = self.store.get(record['data']['target'])
        if subject['kind'] != 'claim' or self.store.status(subject['id']) in {'withdrawn', 'rejected'}:
            return None
        event = self.store.db.execute("SELECT payload FROM events WHERE type='finding-impact-certified' "
                                     'AND target=? ORDER BY seq DESC LIMIT 1', (finding,)).fetchone()
        resolution = json.loads(event['payload']).get('resolution') if event else None
        if not resolution or not self._qualified_resolution_current(resolution, finding, 'scope-classified', disputes | {finding}):
            return None
        return resolution

    def finding_effects(self, identifier: str) -> dict:
        with self.store.transaction():
            from .finalization import report_source
            if report_source(self.store.get(identifier)):
                return {**self.counterexample_report_condition(identifier),
                    'finalization_hold': self.finding_blocking(identifier),
                    'statement_scope_hold': False,
                    'authority': 'Retained allegation limits finalization of relevant selected unconditional judgments; it is neither a negation premise nor an ordinary statement-scope finding'}
            blocking = self.finding_blocking(identifier)
            certificate = self._finding_scope_certificate(identifier)
            disposition = self.store.status(identifier)
            event = self.store.db.execute('SELECT e.payload FROM events e JOIN decisions d '
                'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
            resolution = json.loads(event['payload']).get('reason', {}).get('resolution') if event else None
            substantive_current = (disposition in {'validated', 'dismissed'} and resolution is not None
                and self._qualified_resolution_current(resolution, identifier, disposition, frozenset({identifier})))
            return {'finding': identifier, 'unconditional_use_hold': blocking,
                    'statement_scope_hold': blocking and certificate is None,
                    'scope_certificate': certificate, 'substantive_status': disposition,
                    'substantive_current': substantive_current,
                    'impact': 'unconditional-truth' if certificate else 'undetermined-or-all-use',
                    'authority': 'Reviewed scope qualification only; not a mathematical negation premise'}

    def _adjudication_current(self, identifier: str, disputes: frozenset = frozenset()) -> bool:
        case = self.store.get(identifier, 'adjudication')['data']
        finding = self.store.get(case['finding'])
        subject = self.store.get(case['subject'])
        from .finalization import report_source, report_subject
        intended = report_subject(self, finding['id']) if report_source(finding) else finding['data']['target']
        if (case['finding_hash'] != finding['hash'] or case['subject_hash'] != subject['hash']
                or case['subject'] != intended or case['challenge'] != finding['data']['artifact']):
            return False
        if report_source(finding):
            from .finalization import REPORT_DISPOSITIONS, report_basis
            if (case['disposition'] != 'dismissed' or case.get('report_disposition') not in REPORT_DISPOSITIONS
                    or case.get('counterexample_report_basis') != report_basis(self, finding['id'])):
                return False
        if case['disposition'] == 'scope-classified':
            if (subject['kind'] != 'claim' or case.get('impact') != 'unconditional-truth'
                    or finding['data'].get('target_hash') != subject['hash']
                    or case.get('scope_manifest') != self._statement_manifest(subject['id'])
                    or case.get('finding_evidence') != self._finding_evidence_basis(case['finding'], disputes)
                    or self.store.status(subject['id']) in {'withdrawn', 'rejected'}
                    or not all(self._scope_current(ref, disputes=disputes)
                               for ref in [subject['data']['contract'], *subject['data']['definitions']])):
                return False
            # Retraction changes the provenance question. A fresh scope review
            # may assess retained challenge bytes, but old evidence cannot carry
            # its permission across that change. Ordinary substantive validation
            # or dismissal does not itself alter a certified statement boundary.
            retracted = {'withdrawn', 'rejected', 'provenance-retracted'}
            if ((self.store.status(case['finding']) in retracted or case.get('finding_status') in retracted)
                    and self.store.status(case['finding']) != case.get('finding_status')):
                return False
        # Challenge bytes survive provenance retraction; the response must remain
        # usable. Subject/finding currentness is the question being adjudicated.
        return (self.store.status(identifier) not in {'withdrawn', 'rejected'}
            and not self._blocked(identifier, disputes)
            and self._scope_current(case['response'], disputes=disputes)
            and set(self._related_case_findings(case['finding'], exclude=identifier, disputes=disputes,
                    scope_only=case['disposition'] == 'scope-classified'))
                .issubset(case.get('prior_findings', [])))

    def _finding_evidence_basis(self, finding: str, disputes: frozenset = frozenset()) -> dict:
        """Static challenge/provenance conditions; no mathematical eligibility.

        Fresh scope review may assess exact retained bytes whose producer was
        retracted. That does not requalify the report. Changes to those observed
        conditions invalidate an older certification, even false-to-false ones.
        """
        from .context import Tasks
        records = {}
        def visit(target):
            if target in records:
                return
            record = self.store.get(target)
            kind, data = record['kind'], record['data']
            status = self.store.status(target)
            item = {'hash': record['hash'], 'kind': kind,
                    'status': (status if status in {'withdrawn', 'rejected', 'provenance-retracted'} else 'retained')
                              if target == finding else status,
                    'scope': self._scope_condition(target, disputes=disputes | {finding})}
            records[target] = item
            links = []
            if kind == 'objection':
                links = [data['artifact']]
                origin = data.get('native_origin')
                if origin:
                    from .native_capture import native_substance_origin_evidence
                    native_substance_origin_evidence(self.store, origin)
                    source = self.store.get(origin['source_record'])
                    item['native_origin'] = {'origin': origin, 'source_hash': source['hash'],
                        'source_status': self.store.status(source['id']) if self.store.status(source['id'])
                            in {'withdrawn', 'rejected', 'provenance-retracted'} else 'retained'}
                    # Static producer observations, not source-record scope:
                    # native failure scope includes its target, whose permission
                    # this very certification changes. Following that scope
                    # would make the certificate immediately self-stale.
                    links += list(origin['producer_records'])
                    links += self._blocking_findings(source['id'], disputes | {finding})
            elif kind == 'review':
                links = self._review_evidence_ids(target)
                try:
                    item['provenance'] = Tasks(self).review_provenance(data['run_id'], data['target'],
                        data['verdict'], data['artifact'], data['checks'])
                except StateError as error:
                    item['provenance'] = {'current': False, 'reason': str(error)}
            elif kind == 'artifact' and data.get('source_result'):
                links = [data['source_result']]
            elif kind == 'result':
                links = [data['artifact'], data['host_receipt'], data['run'], data['task']]
            elif kind == 'run':
                links = [data['dispatch_evidence'], data['task']]
                item['exposures'] = {e['id']: e['data']['category'] for e in self.store.records('exposure')
                                     if e['data']['run'] == target}
            for link in links:
                visit(link)
            # Challenges against the finding/provenance are retained as exact
            # questions in fresh review. They are never silently neutralized by
            # a previously issued statement-scope permission.
            for challenge in self._blocking_findings(target, disputes | {finding}):
                visit(challenge)
        visit(finding)
        return records

    def _statement_manifest(self, identifier: str) -> dict:
        """Exact statement infrastructure, without positive/negative judgments."""
        manifest = {}
        def visit(target):
            if target in manifest:
                return
            record = self.store.get(target)
            data, kind = record['data'], record['kind']
            manifest[target] = record['hash']
            if kind == 'claim':
                links = [data['contract'], *data['definitions']]
            elif kind == 'contract':
                links = data['definitions']
            elif kind == 'definition':
                links = data.get('dependencies', [])
            else:
                raise StateError('Statement manifest requires exact claim/contract/definition records')
            for link in links:
                visit(link)
        visit(identifier)
        return manifest

    def _related_case_findings(self, finding: str, *, exclude: str | None = None,
                               disputes: frozenset = frozenset(), scope_only: bool | None = None) -> list[str]:
        return list(self._related_case_context(finding, exclude=exclude, disputes=disputes, scope_only=scope_only))

    def _review_evidence_ids(self, identifier: str) -> list[str]:
        data = self.store.get(identifier, 'review')['data']
        execution = self.store.get(data['run_id'], 'run')['data']
        result = self.store.get(data['provenance']['result'], 'result')['data']
        admission = execution.get('native_context_admission')
        receipt = json.loads(self.store.get(result['host_receipt'], 'artifact')['data']['text'])
        if execution.get('native_context_profile') or receipt.get('producer_evidence'):
            from .native_controls import retained_context
            admission = retained_context(self, self.store.get(data['run_id'], 'run')).get('native_context_admission')
        return [identifier, data['artifact'], data['run_id'], data['provenance']['task'],
                data['provenance']['result'], result['host_receipt'], execution['dispatch_evidence'],
                *([receipt['producer_evidence']] if receipt.get('producer_evidence') else []),
                *([admission] if admission else [])]

    def _related_case_context(self, finding: str, *, exclude: str | None = None,
                              disputes: frozenset = frozenset(), scope_only: bool | None = None) -> dict[str, str]:
        cases = [c for c in self.store.records('adjudication')
                 if c['data']['finding'] == finding and c['id'] != exclude
                 and (scope_only is None or (c['data']['disposition'] == 'scope-classified') == scope_only)]
        affected = {}
        for case in cases:
            ids = [case['id'], case['data']['response']]
            resolutions = [r for r in self.store.records('resolution') if r['data'].get('case') == case['id']]
            for resolution in resolutions:
                ids.append(resolution['id'])
                for review in resolution['data']['reviews']:
                    ids.extend(self._review_evidence_ids(review))
            for identifier in ids:
                affected.setdefault(identifier, case['id'])
        findings = [o for o in self.store.records('objection') if o['data']['target'] in affected]
        findings += [r for r in self.store.records('review')
                     if r['data']['target'] in affected and r['data']['verdict'] == 'fail']
        return {r['id']: affected[r['data']['target']] for r in findings if self.finding_blocking(r['id'], disputes)}

    def _adjudication_checks(self, case: dict) -> set[str]:
        checks = {'finding-scope', 'counterargument', case['disposition']}
        if case['disposition'] == 'scope-classified':
            checks |= {'statement-boundary', 'truth-only-impact', 'evidence-provenance'}
            if case.get('scope_evidence_challenges'):
                checks.add('scope-evidence-challenges')
        if case.get('prior_findings'):
            checks.add('prior-challenges')
        if case.get('report_disposition'):
            checks |= {'counterexample-report', 'retained-substance', 'domain', 'negation',
                       'source-scope', 'mathematical-report-disposition'}
        return checks

    def _blocked(self, identifier: str, disputes: frozenset = frozenset()) -> bool:
        return bool(self._blocking_findings(identifier, disputes))

    def _blocking_findings(self, identifier: str, disputes: frozenset = frozenset()) -> dict:
        findings = [o for o in self.store.records('objection') if o['data']['target'] == identifier]
        findings += [r for r in self.store.records('review')
                     if r['data']['target'] == identifier and r['data']['verdict'] == 'fail']
        return {r['id']: self.store.status(r['id']) for r in findings
                if self.finding_blocking(r['id'], disputes)}

    def _statement_scope_findings(self, identifier: str, disputes: frozenset = frozenset()) -> dict:
        return {f: status for f, status in self._blocking_findings(identifier, disputes).items()
                if self._finding_scope_certificate(f, disputes) is None}

    def _truth_hold_findings(self, identifier: str) -> dict:
        return {f: status for f, status in self._blocking_findings(identifier).items()
                if self._finding_scope_certificate(f) is not None}

    def eligible_supports(self, claim: str, assumptions: set[str] | None = None,
                          *, policy: str = "audited-informal") -> list[str]:
        return [single_root(w)["inference"] for w in self.derivations(claim, assumptions, policy=policy)]

    def _environment(self, assumptions) -> frozenset:
        if assumptions is None:
            return frozenset()
        if (not isinstance(assumptions, (list, set, frozenset))
                or any(not isinstance(a, str) or not a.strip() for a in assumptions)):
            raise StateError('Assumption environment must be an exact collection of assumption IDs')
        for assumption in assumptions:
            self.store.get(assumption, 'assumption')
        return frozenset(assumptions)

    def derivations(self, claim: str, assumptions: set[str] | None = None,
                    *, policy: str = "audited-informal") -> list[dict]:
        self.store.get(claim, "claim")
        if policy not in {"audited-informal", "formal-only"}:
            raise StateError("Unknown assurance policy")
        from .evaluation import Evaluation
        with self.store.transaction():
            return Evaluation(self).derivations(claim, self._environment(assumptions), policy=policy)

    def promote(self, identifier: str, *, expected: int, request_id: str) -> dict:
        record = self.store.get(identifier, "inference")
        fingerprint = digest({"operation": "promote", "id": identifier, "hash": record["hash"]})
        # Retry receipt must be checked before snapshot freshness: successful retry
        # naturally presents the old snapshot after its own commit advanced state.
        with self.store.transaction():
            prior = self.store.request(request_id, fingerprint)
            if prior is not None:
                return prior
            if self.store.status(identifier) != 'proposed':
                raise StateError('Only a new proposed inference may be promoted; withdrawn evidence needs a new reviewed derivation')
            if self.store.revision != expected:
                from .store import StaleState
                raise StaleState("Reassess current objections and dependencies before promotion")
            data = record["data"]
            checks = {"validity", "scope", "dependencies"}
            if data["discharge"]:
                checks.add("discharge")
            reviews = self._reviews(identifier, checks)
            if data['assurance'] == 'formal' and not self._formal_current(data.get('formal_receipt')):
                raise StateError('Formal checking and independent fidelity evidence incomplete')
            if self._blocked(identifier) or (not data['assumptions'] and self._blocked(data['conclusion'])):
                raise StateError("Blocking objection remains open")
            if not all(self._scope_current(ref) for ref in [data["conclusion"], data["artifact"], *data["assumptions"], *data["discharge"]]):
                raise StateError("Statement, definition, assumption or artifact is withdrawn")
            if not all(self._application_current(a) for a in data.get("applications", [])):
                raise StateError("External theorem application is not currently accepted")
            policy = 'formal-only' if data['assurance'] == 'formal' else 'audited-informal'
            from .evaluation import Evaluation
            preview = Evaluation(self, proposed_inference=identifier)
            if identifier not in {single_root(w)['inference'] for w in preview.derivations(data['conclusion'],
                    frozenset(data['assumptions']), policy=policy)}:
                raise StateError('No grounded usable derivation under the declared assumptions; negative evidence remains a veto')
            event = self.store.decide(identifier, "accepted", {"reviews": reviews,
                "policy": policy, "assumptions": data["assumptions"]})
            response = {"id": identifier, "decision_event": event, "status": "accepted",
                        "assurance": 'machine-checked' if data['assurance'] == 'formal' else "audited-informal", "assumptions": data["assumptions"]}
            self.store.finish_request(request_id, fingerprint, response)
            return response

    def _formal_current(self, identifier: str | None) -> bool:
        return self._formal_condition(identifier)['current']

    def _formal_condition(self, identifier: str | None) -> dict:
        """Qualification and repair causes, separate from operational assessment."""
        issues = []
        def issue(target, category, reason, **details):
            issues.append({'target': target, 'category': category, 'reason': reason, **details})
        def scope(target):
            condition = self._scope_condition(target)
            if not condition['current']:
                issue(target, 'scope', 'Scope or provenance is not current', issues=condition['issues'])
        if identifier is None:
            return {'current': False, 'issues': [{'target': None, 'category': 'evidence',
                                                 'reason': 'No formal receipt supplied'}]}
        record = self.store.get(identifier, 'formal_receipt')
        data = record['data']
        if self.store.status(identifier) != 'checked':
            issue(identifier, 'status', 'Formal receipt is not checked', status=self.store.status(identifier))
        if self._blocked(identifier):
            issue(identifier, 'finding', 'Formal receipt has an unresolved finding')
        if data.get('receipt_version') not in RECEIPT_VERSIONS or data.get('checking_profile') != PROFILE:
            issue(identifier, 'migration', 'Legacy formal evidence requires a new modern plan/check, binding and audit')
            return {'current': False, 'issues': issues}
        try:
            evidence = receipt_evidence(self.store, identifier)
        except (StateError, ValueError, TypeError, KeyError, RecursionError) as error:
            issue(identifier, 'binding', str(error))
            return {'current': False, 'issues': issues}
        for target in evidence['records']:
            scope(target)
        if self.store.status(data['toolchain']) != 'installed':
            issue(data['toolchain'], 'status', 'Toolchain is not installed', status=self.store.status(data['toolchain']))
        for target, checks in ((data['plan'], {'formal-source-integrity', 'formal-target-fidelity', 'foundations'}),
                               (identifier, {'formal-receipt', 'formal-target-fidelity', 'foundations'})):
            condition = self._review_condition(target, checks,
                witnesses=data['source_reviews'] if target == data['plan'] else None)
            if not condition['current']:
                issue(target, 'finding' if condition.get('finding') else 'qualification',
                      condition['reason'], missing=condition['missing'],
                      ineligible=condition.get('ineligible', {}))
        return {'current': not issues, 'issues': issues}

    def _application_structure(self, identifier: str) -> bool:
        data = self.store.get(identifier, 'application')['data']
        theorem = self.store.get(data['theorem'], 'external_theorem')['data']
        mapping = data.get('mapping')
        if (not isinstance(mapping, dict) or set(mapping) != set(theorem['hypotheses'])
                or any(not isinstance(v, str) or not v.strip() for v in mapping.values())):
            return False
        for claim in mapping.values():
            self.store.get(claim, 'claim')
        self.store.get(data['conclusion'], 'claim')
        return True

    def _application_current(self, identifier: str) -> bool:
        data = self.store.get(identifier, "application")["data"]
        if (self.store.status(identifier) != "accepted" or not self._application_structure(identifier)
                or not self._scope_current(identifier)):
            return False
        try:
            self._reviews(identifier, {"source", "hypotheses", "substitution", "conclusion"})
        except StateError:
            return False
        return True

    def _scope_current(self, identifier: str, seen: frozenset = frozenset(), *, disputes: frozenset = frozenset()) -> bool:
        return self._scope_condition(identifier, seen, disputes=disputes)['current']

    def _scope_condition(self, identifier: str, seen: frozenset = frozenset(), *, disputes: frozenset = frozenset()) -> dict:
        """Reason-bearing projection of the existing scope/provenance gate."""
        issues = []
        def issue(reason, **details):
            issues.append({'target': identifier, 'reason': reason, **details})
        if identifier in seen:
            return {'current': False, 'issues': [{'target': identifier, 'reason': 'scope-cycle'}]}
        record = self.store.get(identifier)
        if self.store.status(identifier) in {'withdrawn', 'rejected'}:
            issue('withdrawn-or-rejected', status=self.store.status(identifier))
        findings = self._statement_scope_findings(identifier, disputes)
        if findings:
            issue('unresolved-finding', findings=findings)
        data, links = record["data"], []
        if record["kind"] == "claim":
            links = [data["contract"], *data["definitions"]]
        elif record['kind'] == 'completion_request':
            links = [data['contract'], data['mapping_artifact'], *[o['target'] for o in data['outputs']]]
        elif record['kind'] == 'completion_evidence':
            links = [data['request'], data['candidate'], data['artifact'], *data['additional_evidence']]
        elif record['kind'] == 'obligation':
            links = [data[k] for k in ('claim', 'route_target', 'relation_artifact') if data.get(k)]
        elif record['kind'] == 'route_decision':
            links = [data['artifact'], data['target']]
        elif record["kind"] == "contract":
            links = data["definitions"]
        elif record["kind"] == "definition":
            links = data.get("dependencies", [])
        elif record['kind'] == 'external_theorem':
            links = [data['source_artifact'], *data['definitions']]
        elif record['kind'] == 'application':
            links = [data['artifact'], data['theorem'], data['conclusion'], *data['mapping'].values()]
        elif record['kind'] == 'counterexample':
            links = [data['target'], data['artifact'], *data.get('dependencies', [])]
        elif record['kind'] == 'experiment':
            links = [data['target'], data['source']]
            links += [data[key] for key in ('plan', 'execution') if data.get(key)]
        elif record['kind'] == 'formal_plan':
            links = [data['target'], data['source'], data['check_source'], *data['assumptions']]
            if data.get('helper_artifact'):
                links.append(data['helper_artifact'])
        elif record['kind'] == 'formal_receipt':
            links = [data['target'], data['source'], data['plan'], data['toolchain']]
            links += [data['execution']] if data.get('execution') else []
            links += list(data.get('compiled_parts', {}).values())
            links += [data[k] for k in ('helper_artifact', 'semantic_artifact', 'reference_artifact',
                                       'resolution_artifact') if data.get(k)]
        elif record['kind'] == 'execution':
            if self.store.status(identifier) != 'completed':
                issue('execution-not-completed', status=self.store.status(identifier))
            links = [data['plan'], data['source']]
            links += [data['metadata']['toolchain']] if data['metadata'].get('toolchain') else []
            event = self.store.db.execute('SELECT e.payload FROM events e JOIN decisions d '
                'ON d.event_seq=e.seq WHERE d.target=?', (identifier,)).fetchone()
            observation = json.loads(event['payload']).get('reason', {}).get('observation') if event else None
            if not observation:
                issue('terminal-observation-absent')
            else:
                links.append(observation)
        elif record['kind'] == 'artifact' and data.get('source_result'):
            links = [data['source_result']]
        elif record['kind'] == 'artifact' and data.get('source_execution'):
            links = [data['source_execution']]
        elif record['kind'] == 'result':
            if self.store.status(data['run']) != 'completed' or self.store.status(data['task']) != 'completed':
                issue('result-run-or-task-not-completed', run_status=self.store.status(data['run']),
                      task_status=self.store.status(data['task']))
            links = [data['artifact'], data['host_receipt'], data['run'], data['task']]
            try:
                receipt = json.loads(self.store.get(data['host_receipt'], 'artifact')['data']['text'])
                if receipt.get('producer_evidence'):
                    links.append(receipt['producer_evidence'])
            except (StateError, ValueError, KeyError, TypeError):
                issue('native-completion-receipt-invalid')
        elif record['kind'] == 'native_failure':
            links = [data['capture_artifact'], data['response_artifact'], data['run'], data['task'], data['target']]
        elif record['kind'] == 'native_conflict':
            links = [data['capture_artifact'], data['response_artifact'], data['comparison_artifact'],
                     data['previous_run'], data['previous_outcome'], data['task']]
        elif record['kind'] == 'ingestion_failure':
            links = [data['result'], data['artifact'], data['host_receipt'], data['run'], data['task']]
        elif record['kind'] == 'run':
            links = [data['dispatch_evidence'], data['task']]
            admission = data.get('native_context_admission')
            if self.store.status(identifier) == 'completed':
                from .native_controls import retained_context_record
                try:
                    context_record = retained_context_record(self, record)
                    links.append(context_record['id'])
                    if data.get('native_context_profile') or context_record['id'] != data['dispatch_evidence']:
                        admission = json.loads(context_record['data']['text']).get('native_context_admission')
                except (StateError, ValueError, KeyError, TypeError):
                    issue('native-completion-context-invalid')
            if admission:
                links.append(admission)
        elif record['kind'] == 'background':
            links = [data['target'], data['source'], data['rationale']]
        for ref in links:
            issues.extend(self._scope_condition(ref, seen | {identifier}, disputes=disputes)['issues'])
        # Shared dependencies can have several paths. Their exact failed gates
        # matter; repeating an identical cause does not.
        unique = {digest(item): item for item in issues}
        return {'current': not issues, 'issues': sorted(unique.values(), key=lambda item: digest(item))}

    def withdraw(self, identifier: str, reason: str) -> None:
        record = self.store.get(identifier)
        with self.store.transaction():
            negative = record['kind'] == 'objection' or (record['kind'] == 'review' and record['data']['verdict'] == 'fail')
            self.store.decide(identifier, 'provenance-retracted' if negative else 'withdrawn',
                              {"reason": nonempty(reason, "reason"), 'substantive_dismissal': False})
        # Descendant eligibility is derived afresh; no false-refutation cascade.

    def objection(self, target: str, artifact: str, reporter: str) -> str:
        record = self.store.get(target)
        self.store.get(artifact, "artifact")
        with self.store.transaction():
            identifier = self.store.put("objection", {"target": target, "target_hash": record["hash"],
                "artifact": artifact, "author": nonempty(reporter, "reporter")})
            self.store.decide(identifier, "open", {"reason": "Identified objection requires adjudication"})
            return identifier

    def adjudication(self, finding: str, response: str, *, disposition: str, author: str,
                     impact: str | None = None, report_disposition: str | None = None) -> str:
        record = self.store.get(finding)
        from .finalization import report_source, report_subject
        if record['kind'] != 'objection' and not report_source(record) and not (record['kind'] == 'review' and record['data']['verdict'] == 'fail'):
            raise StateError('Adjudication requires one exact negative finding')
        if report_source(record):
            from .finalization import REPORT_DISPOSITIONS
            if disposition != 'dismissed' or report_disposition not in REPORT_DISPOSITIONS or impact is not None:
                raise StateError('Counterexample report needs explicit substantive invalid/irrelevant/unsubstantiated disposition')
        elif report_disposition is not None:
            raise StateError('Report disposition applies only to the exact retained counterexample')
        if disposition not in {'validated', 'dismissed', 'scope-classified'}:
            raise StateError('Adjudication disposition must be validated, dismissed or scope-classified')
        self.store.get(response, 'artifact')
        subject = self.store.get(report_subject(self, finding) if report_source(record) else record['data']['target'])
        if disposition == 'scope-classified':
            if subject['kind'] != 'claim' or impact != 'unconditional-truth':
                raise StateError('Scope-only certification requires an exact claim and unconditional-truth impact')
        elif impact is not None:
            raise StateError('Substantive finding adjudication is separate from scope classification')
        self.store.get(record['data']['artifact'], 'artifact')
        parties = {nonempty(author, 'case author'), record['data'].get('author', record['data'].get('reviewer'))}
        parties.update(self._subject_parties(subject['id']))
        parties.update(self._subject_parties(finding))
        parties.update(self._subject_parties(response))
        parties.update(self._subject_parties(record['data']['artifact']))
        with self.store.transaction():
            prior_cases = self._related_case_context(finding, scope_only=disposition == 'scope-classified')
            prior_findings = list(prior_cases)
            evidence = self._finding_evidence_basis(finding) if disposition == 'scope-classified' else None
            evidence_challenges = {r: self.store.get(r)['data']['target'] for r in evidence or {}
                if r != finding and (self.store.get(r)['kind'] == 'objection'
                    or (self.store.get(r)['kind'] == 'review' and self.store.get(r)['data']['verdict'] == 'fail'))}
            for prior_id in prior_findings:
                prior = self.store.get(prior_id)
                parties.add(prior['data'].get('author', prior['data'].get('reviewer')))
                parties.add(self.store.get(prior_cases[prior_id])['data'].get('author'))
            for challenge in evidence_challenges:
                data = self.store.get(challenge)['data']
                parties.add(data.get('author', data.get('reviewer')))
            report_fields = {}
            if report_source(record):
                from .finalization import report_basis
                report_fields = {'report_disposition': report_disposition,
                    'counterexample_report_basis': report_basis(self, finding),
                    'report_duty': 'Assess this exact retained witness/argument substantively. Withdrawal, format or provenance failure alone is not mathematical clearance; do not claim absence of all possible counterexamples.'}
            return self.store.put('adjudication', {'finding': finding, 'finding_hash': record['hash'],
                **report_fields,
                'subject': subject['id'], 'subject_hash': subject['hash'],
                'finding_status': self.store.status(finding),
                'scope_manifest': self._statement_manifest(subject['id']) if disposition == 'scope-classified' else None,
                'finding_evidence': evidence, 'scope_evidence_challenges': evidence_challenges,
                'challenge': record['data']['artifact'], 'response': response,
                'disposition': disposition, 'impact': impact, 'author': author, 'parties': sorted(p for p in parties if p),
                'prior_findings': prior_findings, 'prior_cases': prior_cases})

    def _subject_parties(self, identifier: str, seen: frozenset = frozenset()) -> set[str]:
        if identifier in seen:
            return set()
        record = self.store.get(identifier)
        kind, data = record['kind'], record['data']
        parties = {data[k] for k in ('author', 'reviewer', 'conversation_id') if isinstance(data.get(k), str)}
        links = []
        if data.get('native_origin'):
            origin = data['native_origin']
            parties.add(origin['conversation_id'])
            links += [origin['run'], origin['source_record']]
        if kind == 'release':
            links = [data['candidate']]
        elif kind == 'candidate':
            links = [data['proof'], *data['manifest']]
        elif kind in {'formal_receipt', 'execution'}:
            links = [data['plan'], data['source']]
        elif kind in {'result', 'exposure', 'native_failure'}:
            links = [data['run']]
        elif kind == 'artifact' and data.get('source_result'):
            links = [data['source_result']]
        elif kind == 'adjudication':
            parties.update(data['parties'])
        for link in links:
            parties.update(self._subject_parties(link, seen | {identifier}))
        return parties

    def adjudicate(self, case: str, *, expected: int) -> str:
        data = self.store.get(case, 'adjudication')['data']
        with self.store.transaction(expected):
            if self.store.status(case) != 'proposed' or not self._adjudication_current(case):
                raise StateError('A new current adjudication case is required')
            reviews = self._reviews(case, self._adjudication_checks(data))
            resolution = self.store.put('resolution', {'case': case, 'finding': data['finding'],
                'disposition': data['disposition'], 'reviews': reviews})
            if data['disposition'] == 'scope-classified':
                self.store.event('finding-impact-certified', data['finding'], {'resolution': resolution,
                    'impact': 'unconditional-truth', 'substantive_acceptance': False})
            elif self.store.get(data['finding'])['kind'] == 'result':
                self.store.event('counterexample-report-disposed', data['finding'], {'resolution': resolution})
            else:
                self.store.decide(data['finding'], data['disposition'], {'resolution': resolution})
            self.store.decide(case, 'resolved', {'resolution': resolution})
            return resolution

    def resolve_objection(self, objection: str, disposition: str, *, expected: int, case: str | None = None) -> str:
        self.store.get(objection, "objection")
        if case is None:
            raise StateError('Resolution requires an exact reviewed adjudication case and counterargument')
        data = self.store.get(case, 'adjudication')['data']
        if data['finding'] != objection or data['disposition'] != disposition:
            raise StateError('Adjudication case addresses a different finding or disposition')
        return self.adjudicate(case, expected=expected)

    def _counterexample_dependencies(self, dependencies) -> list[str]:
        """Revalidate exact dependency records at construction and use boundaries."""
        if (not isinstance(dependencies, list)
                or any(not isinstance(d, str) or not d.strip() for d in dependencies)
                or len(set(dependencies)) != len(dependencies)):
            raise InputContractError('Counterexample dependencies must be an exact list of distinct claim IDs')
        for dependency in dependencies:
            self.store.get(dependency, 'claim')
        return dependencies

    def counterexample(self, target: str, artifact: str, author: str, *, formal_receipt: str | None = None,
                       dependencies: list[str] | None = None) -> str:
        self.store.get(target, "claim")
        self.store.get(artifact, "artifact")
        dependencies = self._counterexample_dependencies([] if dependencies is None else dependencies)
        if formal_receipt:
            data = self.store.get(formal_receipt, 'formal_receipt')['data']
            if data['target'] != target or data.get('outcome') != 'disproof' or data['assumptions']:
                raise StateError('Formal disproof receipt must establish this exact negation without extra assumptions')
        with self.store.transaction():
            return self.store.put("counterexample", {"target": target, "artifact": artifact,
                "author": nonempty(author, "author"), 'formal_receipt': formal_receipt,
                'dependencies': list(dependencies or [])})

    def validate_counterexample(self, identifier: str, *, expected: int) -> None:
        example = self.store.get(identifier, "counterexample")
        with self.store.transaction(expected):
            self._counterexample_dependencies(example['data'].get('dependencies', []))
            if self.store.status(identifier) != 'proposed' or not self._scope_current(identifier):
                raise StateError('Counterexample must be proposed with current target and evidence')
            checks = {'domain', 'negation', 'scope'}
            if example['data'].get('dependencies'):
                checks.add('dependencies')
            reviews = self._reviews(identifier, checks)
            if example['data'].get('formal_receipt') and not self._formal_current(example['data']['formal_receipt']):
                raise StateError('Formal disproof receipt is not currently eligible')
            if self._blocked(identifier):
                raise StateError("Counterexample has a blocking objection")
            from .evaluation import Evaluation
            preview = Evaluation(self, proposed_counterexample=identifier)
            if identifier not in preview.bounds()['certain']:
                raise StateError('Counterexample lacks unconditional independent dependency grounding or has unresolved circular evidence')
            self.store.decide(identifier, "validated", {"reviews": reviews})

    def _refutations(self, identifier: str) -> list[str]:
        from .evaluation import Evaluation
        with self.store.transaction():
            return Evaluation(self).refutations(identifier)

    def claim_state(self, identifier: str, assumptions: set[str] | None = None,
                    *, policy: str = "audited-informal") -> dict:
        self.store.get(identifier, "claim")
        if policy not in {'audited-informal', 'formal-only'}:
            raise StateError('Unknown assurance policy')
        from .evaluation import Evaluation
        with self.store.transaction():
            environment = self._environment(assumptions)
            result = Evaluation(self).view(identifier, environment, policy=policy)
            from .finalization import reports_for
            result['pending_counterexample_reports'] = reports_for(self, [identifier]) if not environment else []
            return result

    def counterexample_report_condition(self, identifier: str) -> dict:
        with self.store.transaction():
            from .finalization import report_subject
            return {'report': identifier, 'target': report_subject(self, identifier),
                'status': self.store.status(identifier), 'pending': self.finding_blocking(identifier),
                'authority': 'Retained allegation for finalization; not a proved negation'}
