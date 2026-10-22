"""Exact packets and auditable native execution/result provenance.

Workers receive exported packet data, never database handles. This module enforces
record/exposure rules; actual host enforcement is verified separately.
"""

from __future__ import annotations

import hashlib
import json

from .research import Research, nonempty
from .store import StateError, digest
from .evaluation import Evaluation
from .witness import merge, nodes, roots
from .formal import (RECEIPT_VERSION, RECEIPT_VERSIONS, CAPSULE_MEDIA, SUPPLIED_PROOFS, semantic_view, validate_view)
from .results import worker_result, REVIEW_ROLES_V1, RESULT_CONTRACT_PROFILE

ROLES = {"scout", "prover", "falsifier", "referee", "reproducer", "theorem-checker",
         "fidelity-auditor", "adjudicator", "formalizer", "computationalist", "strategist"}
REVIEW_ROLES = REVIEW_ROLES_V1
BLIND_ROLES = {"scout", "reproducer"}
HISTORY_KINDS = {"review", "result", "native_failure", "native_conflict", "ingestion_failure", "work_intent", "fulfillment_certificate", "run", "task", "dispatch", "exposure", "learning", "route", "release", "checkpoint", "resolution", "route_decision", "boundary_certificate", "learning_candidate", "learning_admission"}


class Tasks:
    def __init__(self, research: Research):
        self.r = research
        self.store = research.store

    def _claim_for(self, identifier: str) -> str | None:
        visited = set()
        while identifier not in visited:
            visited.add(identifier)
            record = self.store.get(identifier)
            if record["kind"] == "claim":
                return identifier
            data = record["data"]
            if record["kind"] == "inference" or record["kind"] == "application":
                identifier = data["conclusion"]
            elif record["kind"] in {"candidate", "counterexample", "objection", "review", "release", "route", "experiment", "formal_plan", "formal_receipt", "background", "native_failure", "native_conflict", "ingestion_failure"}:
                identifier = data["target"]
            elif record['kind'] == 'adjudication':
                identifier = data['subject']
            elif record['kind'] == 'execution':
                identifier = data['plan']
            elif record['kind'] == 'completion_request':
                identifier = data['outputs'][0]['target']
            elif record['kind'] == 'completion_evidence':
                identifier = data['target']
            elif record['kind'] in {'learning_candidate', 'learning_admission', 'route_decision'}:
                identifier = data['target']
            elif record['kind'] == 'fulfillment_certificate':
                identifier = data['request']
            elif record['kind'] in {'run', 'result'}:
                identifier = data['task']
            elif record['kind'] == 'task':
                identifier = data['packet']['target']
            elif record["kind"] == "obligation":
                identifier = data.get("claim") or data["route"]
            else:
                return None
        raise StateError("Cyclic task context")

    def _bound_stream(self, text: str, limit: int = 2048) -> str | dict:
        if not isinstance(text, str) or len(text) <= limit:
            return text
        return {
            "preview": text[:limit],
            "length": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "truncated": True,
        }

    def _bound_process(self, process_data: dict, limit: int = 2048) -> dict:
        bounded = dict(process_data)
        for stream in ("stdout", "stderr"):
            if stream in bounded and isinstance(bounded[stream], str) and len(bounded[stream]) > limit:
                bounded[stream] = self._bound_stream(bounded[stream], limit=limit)
        return bounded

    def _project_data(self, kind: str, data: dict) -> dict:
        projected = {k: v for k, v in data.items() if k not in {"author", "base_snapshot"}}
        if kind == "artifact":
            media_type = data.get("media_type", "")
            if media_type == CAPSULE_MEDIA:
                try:
                    view = semantic_view(json.loads(data['text']))
                except (StateError, ValueError, TypeError, KeyError, RecursionError):
                    view = None
                return {'media_type': media_type, 'content_hash': data['content_hash'],
                        'sha256': data.get('sha256'), 'source_execution': data.get('source_execution'),
                        'semantic_view': view, 'content_omitted': True,
                        'semantic_data_complete': view is not None,
                        'expansion_policy': 'Exact selectors from this already admitted capsule may preserve blindness'}
            if (data.get('artifact_role') in {'formal-helper', 'primitive-reference', 'resolved-inputs'}
                    or media_type == 'application/vnd.mathtrace.process-observation+json'):
                return {k: data[k] for k in ('media_type', 'content_hash', 'sha256', 'artifact_role',
                                            'source_execution') if k in data} | {'content_omitted': True}
            is_binary = (
                data.get("encoding") == "base64"
                or media_type in {"application/octet-stream", "application/x-lean-olean"}
            )
            if is_binary:
                projected = {k: v for k, v in projected.items() if k != "text"}
                projected["content_omitted"] = True
        elif kind == "toolchain":
            if "files" in projected:
                files = projected.pop("files")
                projected["files_hash"] = digest(files)
                projected["file_count"] = len(files)
                projected["manifest_omitted"] = True
            projected.pop("root", None)
            projected.pop("archive", None)
        elif kind in {"formal_receipt", "formal_plan"}:
            if kind == 'formal_receipt' and data.get('receipt_version') in RECEIPT_VERSIONS:
                keys = {'execution_mode', 'execution_assurance', 'receipt_version', 'checking_profile', 'target', 'plan', 'plan_hash', 'source', 'execution',
                    'symbol', 'check_symbol', 'expected_type', 'assumptions', 'outcome', 'allowed_axioms',
                    'toolchain', 'toolchain_hash', 'helper_artifact', 'helper_hash', 'helper_sha256',
                    'checker', 'checker_hash', 'compiled_artifact', 'compiled_parts', 'compiled_file_set',
                    'semantic_artifact', 'reference_artifact', 'resolution_artifact', 'evidence_manifest_hash',
                    'observation_result_hash', 'verification_binding', 'kernel_replay', 'replay_input_hash', 'axioms',
                    'source_to_object_correspondence', 'compilation_association', 'library_origin',
                    'imported_bytes_retained_in_canonical_state', 'assurance_limitations'}
                projected = {k: data[k] for k in keys if k in data}
                projected['process_text_omitted'] = True
            projected.pop("checker_path", None)
            projected.pop('source_reviews', None)
            if "libraries" in projected and isinstance(projected["libraries"], list):
                compacted_libs = []
                for lib in projected["libraries"]:
                    if isinstance(lib, dict):
                        compact_lib = {k: v for k, v in lib.items() if k not in {"files", "root"}}
                        if "files" in lib and isinstance(lib["files"], dict):
                            compact_lib["files_hash"] = digest(lib["files"])
                            compact_lib["file_count"] = len(lib["files"])
                            compact_lib["manifest_omitted"] = True
                        compacted_libs.append(compact_lib)
                    else:
                        compacted_libs.append(lib)
                projected["libraries"] = compacted_libs
            for proc_key in ("result", "version", "replay"):
                if proc_key in projected and isinstance(projected[proc_key], dict):
                    projected[proc_key] = self._bound_process(projected[proc_key])
        elif kind == 'execution':
            projected = {k: data[k] for k in ('plan', 'plan_hash', 'operation', 'request_hash', 'source',
                                            'source_hash', 'target_hash', 'timeout') if k in data}
            projected['metadata'] = {k: v for k, v in data.get('metadata', {}).items()
                if k in {'receipt_version', 'checking_profile', 'helper_artifact', 'helper_hash', 'helper_sha256',
                         'check_symbol', 'toolchain', 'toolchain_hash', 'checker_hash'}}
        elif kind == 'experiment' and isinstance(projected.get('result'), dict):
            projected['result'] = self._bound_process(projected['result'])
        return projected

    def _closure(self, identifier: str, records: dict, *, evidence: bool, admission_rationale: bool = True):
        record = self.store.get(identifier)
        kind, data = record["kind"], record["data"]
        if kind == 'counterexample':
            self.r._counterexample_dependencies(data.get('dependencies', []))
        if identifier in records:
            return
        if kind in HISTORY_KINDS:
            raise StateError(f"History/other verdict cannot enter mathematical closure: {kind}")
        records[identifier] = {"id": identifier, "kind": kind, "hash": record["hash"],
                               "data": self._project_data(kind, data)}
        links = []
        if kind == "claim":
            links = [data["contract"], *data["definitions"]]
        elif kind == 'completion_request':
            links = [data['contract'], data['mapping_artifact'], *[o['target'] for o in data['outputs']]]
        elif kind == 'completion_evidence':
            links = [data['request'], data['candidate'], data['artifact'], *data['additional_evidence']]
        elif kind == "contract":
            links = list(data["definitions"])
        elif kind == "definition":
            links = list(data.get("dependencies", []))
        elif kind == "inference":
            links = [data["conclusion"], *data["premises"], *data["assumptions"], *data["discharge"]]
            if evidence:
                links += [data["artifact"], *data.get("applications", [])]
                if data.get('formal_receipt'):
                    links.append(data['formal_receipt'])
        elif kind == "candidate":
            links = [data["target"], data["proof"], *data["manifest"]] if evidence else [data["target"]]
        elif kind == "application":
            links = [data["theorem"], data["conclusion"], data["artifact"], *data["mapping"].values()]
        elif kind == "external_theorem":
            links = [data["source_artifact"], *data["definitions"]]
        elif kind in {"counterexample", "objection"}:
            links = [data["target"], data["artifact"]]
            if kind == 'counterexample':
                links += data.get('dependencies', [])
            if data.get('formal_receipt'):
                links.append(data['formal_receipt'])
        elif kind == 'adjudication':
            # This informed lane intentionally includes one exact negative verdict.
            # Other mathematical review packets retain the history exclusion.
            finding = self.store.get(data['finding'])
            records[finding['id']] = {'id': finding['id'], 'kind': finding['kind'],
                'hash': finding['hash'], 'data': self._project_data(finding['kind'], finding['data']),
                'stored_status': self.store.status(finding['id']), 'authority': 'finding under adjudication'}
            subject = self.store.get(data['subject'])
            if subject['kind'] in HISTORY_KINDS:
                records[subject['id']] = {'id': subject['id'], 'kind': subject['kind'],
                    'hash': subject['hash'], 'data': self._project_data(subject['kind'], subject['data']),
                    'stored_status': self.store.status(subject['id'])}
                if subject['kind'] == 'release':
                    links.append(subject['data']['candidate'])
            else:
                links.append(subject['id'])
            records[identifier]['finding_status'] = self.store.status(finding['id'])
            records[identifier]['subject_status'] = self.store.status(subject['id'])
            records[identifier]['challenge_status'] = self.store.status(data['challenge'])
            links += [data['challenge'], data['response']]
            if data.get('report_disposition'):
                links += finding['data'].get('dependencies', [])
                if finding['data'].get('formal_receipt'):
                    links.append(finding['data']['formal_receipt'])
                records[identifier]['counterexample_report_limitations'] = {
                    'source_status': self.store.status(finding['id']),
                    'duty': data['report_duty'], 'authority': 'Retained source under substantive review; no refutation is presumed'}
            origin = finding['data'].get('native_origin')
            if origin:
                for ref in [origin['source_record'], *origin['producer_records']]:
                    observed = self.store.get(ref)
                    records[ref] = {'id': ref, 'kind': observed['kind'], 'hash': observed['hash'],
                        'data': self._project_data(observed['kind'], observed['data']),
                        'stored_status': self.store.status(ref),
                        'authority': 'Exact producer context under informed substance/scope adjudication'}
            for challenge in data.get('scope_evidence_challenges', {}):
                item = self.store.get(challenge)
                records[challenge] = {'id': challenge, 'kind': item['kind'], 'hash': item['hash'],
                    'data': self._project_data(item['kind'], item['data']),
                    'stored_status': self.store.status(challenge), 'authority': 'Exact challenge to scope evidence; not a mathematical premise'}
                links.append(item['data']['artifact'])
            for prior_id in data.get('prior_findings', []):
                prior = self.store.get(prior_id)
                previous_case = self.store.get(data.get('prior_cases', {}).get(prior_id, prior['data']['target']), 'adjudication')
                records[prior_id] = {'id': prior_id, 'kind': prior['kind'], 'hash': prior['hash'],
                    'data': self._project_data(prior['kind'], prior['data']),
                    'stored_status': self.store.status(prior_id), 'authority': 'prior counterargument challenge'}
                records[previous_case['id']] = {'id': previous_case['id'], 'kind': 'adjudication',
                    'hash': previous_case['hash'], 'data': self._project_data('adjudication', previous_case['data']),
                    'stored_status': self.store.status(previous_case['id'])}
                affected = self.store.get(prior['data']['target'])
                if affected['kind'] == 'artifact':
                    self._closure(affected['id'], records, evidence=True)
                elif affected['id'] not in records:
                    records[affected['id']] = {'id': affected['id'], 'kind': affected['kind'],
                        'hash': affected['hash'], 'stored_status': self.store.status(affected['id']),
                        'data_omitted': True, 'reason': 'Prior evidence under challenge; request exact context if needed'}
                links += [prior['data']['artifact'], previous_case['data']['response']]
        elif kind == 'formal_plan':
            links = [data['target'], data['source'], data['check_source'], *data['assumptions']]
            if data.get('helper_artifact'):
                links.append(data['helper_artifact'])
        elif kind == 'formal_receipt':
            links = [data['target'], data['plan'], data['source'], data['toolchain'], *data['assumptions']]
            links += list(data.get('compiled_parts', {}).values())
            links += [data[k] for k in ('helper_artifact', 'semantic_artifact', 'reference_artifact',
                                       'resolution_artifact') if data.get(k)]
            if data.get('compiled_artifact'):
                links.append(data['compiled_artifact'])
            if data.get('execution'):
                links.append(data['execution'])
        elif kind == 'execution':
            links = [data['plan'], data['source']]
            if data.get('metadata', {}).get('toolchain'):
                links.append(data['metadata']['toolchain'])
            terminal = self.store.db.execute("SELECT payload FROM events WHERE type='execution-terminal' "
                                            'AND target=? ORDER BY seq DESC LIMIT 1', (identifier,)).fetchone()
            if terminal:
                links.append(json.loads(terminal['payload'])['observation'])
        elif kind == 'experiment':
            links = [data['target'], data['source']]
            if data.get('plan'):
                links.append(data['plan'])
            if data.get('execution'):
                links.append(data['execution'])
        elif kind == 'background':
            links = [data['source'], data['target']]
            if admission_rationale:
                links.append(data['rationale'])
            else:
                records[identifier]['data'].pop('rationale', None)
                records[identifier]['data']['admission_rationale_omitted'] = True
        elif kind == "obligation":
            links = [data["claim"]] if data.get("claim") else []
            if data.get('route_target'):
                links.append(data['route_target'])
            if data.get('relation_artifact'):
                links.append(data['relation_artifact'])
        for link in links:
            self._closure(link, records, evidence=evidence, admission_rationale=admission_rationale)

    def create(self, role: str, target: str, *, checks: list[str], mandate: str,
               independence: str = "blind", background: list[str] | None = None,
               literature: str = "background-only") -> str:
        if role not in ROLES or independence not in {"blind", "informed"}:
            raise StateError("Invalid task role or independence policy")
        if literature not in {"blind", "background-only", "full-prior-art"}:
            raise StateError("Invalid literature lane")
        if independence == "blind" and literature == "full-prior-art" and role in BLIND_ROLES:
            raise StateError("Blind discovery cannot include full target prior art")
        if not isinstance(checks, list) or not checks or any(not isinstance(c, str) or not c.strip() for c in checks):
            raise StateError("Task must identify exact assessment obligations")
        if background is not None and (not isinstance(background, list) or any(not isinstance(b, str) or not b.strip() for b in background)):
            raise StateError("background must be an exact list of record IDs or None")
        record = self.store.get(target)
        if record['kind'] == 'counterexample':
            self.r._counterexample_dependencies(record['data'].get('dependencies', []))
        claim = self._claim_for(target)
        if record['kind'] == 'adjudication' and (role != 'adjudicator' or independence != 'informed'):
            raise StateError('Adjudication needs a fresh informed adjudicator with both sides of the exact case')
        if claim is None and not (record['kind'] == 'adjudication'
                or (record['kind'] == 'toolchain' and role in REVIEW_ROLES)):
            raise StateError('Task requires an explicit mathematical claim context or a scoped infrastructure review')
        with self.store.transaction():
            records = {}
            if claim is not None:
                self._closure(claim, records, evidence=False)
            if role not in BLIND_ROLES:
                self._closure(target, records, evidence=True)
            dependency_evidence = None
            if record['kind'] == 'counterexample' and role not in BLIND_ROLES:
                evaluation = Evaluation(self.r)
                forbidden = evaluation.bounds()['forbidden'] | {record['data']['target']}
                selected = []
                dependency_evidence = {'missing': [],
                    'authority': 'selected mathematical arguments for assessment; no peer verdicts'}
                for dependency in record['data'].get('dependencies', []):
                    options = evaluation.witnesses(dependency, forbidden=forbidden)
                    if options:
                        selected.append(options[0])
                    else:
                        dependency_evidence['missing'].append(dependency)
                dependency_evidence['selected'] = merge(selected)
                for node in nodes(dependency_evidence['selected']).values():
                    self._closure(node['inference'], records, evidence=True)
            for extra in background or []:
                source = self.store.get(extra)
                self._scope_extra(record, source)
                self._allow_extra(source, independence, literature, claim)
                if source["kind"] == "learning":
                    records[extra] = self._learning_record(extra)
                else:
                    self._closure(extra, records, evidence=True, admission_rationale=independence != 'blind')
            packet = {"role": role, "target": target, "target_hash": record["hash"],
                      "claim": claim, "records": records, "checks": sorted(set(checks)),
                      'context_type': 'mathematical' if claim else 'infrastructure',
                      "mandate": nonempty(mandate, "task mandate"),
                      "independence": independence, "literature": literature,
                      'admitted_sources': list(dict.fromkeys(background or [])),
                      "context_limitations": [], "model_policy": "inherit",
                      "worker_permissions": "tool-free; return structured proposals only",
                      "outcomes": ["proposal", "review", "context-request", "inconclusive", "counterexample"],
                      "snapshot": self.store.revision}
            if dependency_evidence is not None:
                packet['dependency_evidence'] = dependency_evidence
            if record['kind'] == 'application':
                packet['application_contract'] = {
                    'qualification': 'exact conditional instantiation only; no conclusion or antecedent is thereby proved',
                    'hypotheses_check': 'every source antecedent/side condition faithfully maps to an exact claim',
                    'mapped_premises': list(record['data']['mapping'].values()),
                    'support_gate': 'each consuming inference needs finite current arguments in its declared scope'}
            if record['kind'] == 'adjudication' or claim is None:
                packet['outcomes'] = ['review', 'context-request', 'inconclusive']
                packet['context_limitations'].append('This is an exact-subject review. An informed adjudicator sees the challenge and response; that exposure cannot qualify ordinary mathematical proof review. No mathematical proposals or fake claim context are permitted.')
            if role == 'strategist' and independence == 'informed':
                if not hasattr(self.r, 'portfolio'):
                    raise StateError('Informed strategy requires a campaign portfolio')
                portfolio = self.r.portfolio(claim)
                dispositions = portfolio['dispositions']
                portfolio['dispositions'] = [
                    {**item, 'reason': self._bound_stream(item['reason']),
                     'reopen_condition': self._bound_stream(item['reopen_condition']),
                     'followups': item['followups'][:16],
                     'followups_omitted': max(0, len(item['followups']) - 16)}
                    for item in dispositions[-32:]]
                portfolio['dispositions_omitted'] = max(0, len(dispositions) - 32)
                for identifier in portfolio['records']:
                    item = self.store.get(identifier)
                    if item['kind'] in {'route', 'route_decision'}:
                        projected = self._project_data(item['kind'], item['data'])
                        if item['kind'] == 'route_decision':
                            projected = {**projected, 'basis': {'omitted': True,
                                'hash': item['data']['basis_hash'], 'source_count': len(item['data']['sources'])}}
                            for field in ('rationale', 'reopen_condition'):
                                projected[field] = self._bound_stream(projected[field])
                        records[identifier] = {'id': identifier, 'kind': item['kind'], 'hash': item['hash'], 'data': projected}
                    else:
                        self._closure(identifier, records, evidence=True)
                        if item['kind'] == 'artifact':
                            projected = records[identifier]['data']
                            if isinstance(projected.get('text'), str):
                                projected['text'] = self._bound_stream(projected['text'])
                packet['research_state'] = portfolio
                from .curation import Curation
                selection = Curation(self.r).selection(claim)
                packet['advisory_learning'] = selection
                for selected in selection['selected']:
                    identifier = selected['learning']
                    records[identifier] = self._learning_record(identifier)
                    packet['admitted_sources'].append(identifier)
                packet['context_limitations'].append('Historical route certificates are advisory; long certificates use marked previews. Request exact evidence before relying on omitted details.')
                packet['context_limitations'].append('Result dispositions are advisory history, including retracted sources. At most 32 recent dispositions and 16 followups per entry are included; omitted counts and marked text previews are explicit. Request exact evidence when needed.')
            task = self.store.put("task", {"packet": packet, "packet_hash": digest(packet)})
            self.store.decide(task, "ready", {"reason": "Exact task packet compiled"})
            return task

    def packet(self, task: str) -> dict:
        data = self.store.get(task, "task")["data"]
        if not isinstance(data.get('packet'), dict) or data.get('packet_hash') != digest(data['packet']):
            raise StateError('Task packet does not match its exact recorded digest')
        return {"task_id": task, "packet_hash": data["packet_hash"], **data["packet"]}

    def background(self, target: str, source: str, classification: str, rationale: str) -> str:
        self.store.get(target, 'claim')
        record = self.store.get(source)
        self.store.get(rationale, 'artifact')
        if classification not in {'foundation', 'prior-art'} or record['kind'] not in {'artifact', 'definition', 'external_theorem'}:
            raise StateError('Background requires a classified exact mathematical source')
        with self.store.transaction():
            return self.store.put('background', {'target': target, 'source': source,
                'classification': classification, 'rationale': rationale})

    def _allow_extra(self, source: dict, independence: str, literature: str, claim: str):
        if source['kind'] == 'definition':
            return
        if source['kind'] == 'background':
            data = source['data']
            if literature == 'blind' or data['target'] != claim:
                raise StateError('Literature source not admitted for this lane and exact target')
            if data['classification'] != 'foundation' and (independence == 'blind' or literature != 'full-prior-art'):
                raise StateError('Prior-art exposure requires an informed full-prior-art lane')
            if not self.r._scope_current(source['id']):
                raise StateError('Background source, rationale or admission scope is not current')
            self.r._reviews(source['id'], {'background-scope', 'source-fidelity'})
            return
        if independence == 'blind':
            raise StateError('Blind additions require exact definitions or independently reviewed background; raw artifacts may carry verdicts')
        if literature == 'blind' and source['kind'] in {'artifact', 'external_theorem', 'application'}:
            raise StateError('Blind literature lane does not allow additional unclassified sources')

    def _learning_record(self, identifier: str) -> dict:
        if not hasattr(self.r, 'learning_current') or not self.r.learning_current(identifier):
            raise StateError('Local learning is stale or cannot be assessed')
        record = self.store.get(identifier, 'learning')
        data = {**record['data'], 'source_semantics': {'omitted': True,
            'hash': digest(record['data']['source_semantics']), 'source_count': len(record['data']['sources'])}}
        for field in ('summary', 'applicability', 'reopen_condition'):
            if isinstance(data.get(field), str):
                data[field] = self._bound_stream(data[field])
        return {**record, 'data': data, 'advisory': {
            'basis_unchanged_at_snapshot': self.store.revision,
            'authority': 'Historical advice only; never proof or permission to accept a claim'}}

    def _scope_extra(self, target: dict, extra: dict) -> None:
        if target['kind'] == 'adjudication' and target['data']['disposition'] == 'scope-classified':
            if extra['kind'] != 'definition' or extra['id'] not in target['data']['scope_manifest']:
                raise StateError('Scope certification uses the exact self-contained case, not support/history additions; revise its response for missing context')

    def extend(self, task: str, added: list[str], reason: str, *, becomes_informed: bool = False) -> str:
        if not isinstance(added, list) or not added or any(not isinstance(i, str) or not i.strip() for i in added):
            raise StateError("added must be a nonempty list of record IDs")
        if type(becomes_informed) is not bool:
            raise StateError("becomes_informed must be an exact boolean")
        original = self.store.get(task, "task")["data"]
        packet = original["packet"]
        # Produce a new task identity, not a mutation that pretends the old worker
        # saw the new inputs. Parent decides whether to continue informed or restart.
        with self.store.transaction():
            records = dict(packet["records"])
            if packet.get('advisory_learning'):
                from .curation import Curation
                if any(not Curation(self.r).admission_current(s['admission']) for s in packet['advisory_learning']['selected']):
                    raise StateError('Carried target learning admission is stale; restart with deliberate current advice')
            for identifier, record in list(records.items()):
                if record['kind'] == 'counterexample':
                    self.r._counterexample_dependencies(record['data'].get('dependencies', []))
                if record['kind'] == 'learning':
                    records[identifier] = self._learning_record(identifier)
            informed = packet["independence"] == "informed" or becomes_informed
            for identifier in added:
                record = self.store.get(identifier)
                self._scope_extra(self.store.get(packet['target']), record)
                self._allow_extra(record, 'informed' if informed else 'blind', packet['literature'], packet['claim'])
                if record['kind'] == 'learning':
                    if not informed:
                        raise StateError('Expansion changes blindness; explicitly transition to informed')
                    records[identifier] = self._learning_record(identifier)
                elif record["kind"] in HISTORY_KINDS or record["kind"] in {"candidate", "inference", "objection"}:
                    if not informed:
                        raise StateError("Expansion changes blindness; explicitly transition to informed")
                    records[identifier] = record
                else:
                    self._closure(identifier, records, evidence=True, admission_rationale=informed)
            new_packet = {**packet, "records": records, "independence": "informed" if informed else "blind",
                          'admitted_sources': list(dict.fromkeys([*packet.get('admitted_sources', []), *added])),
                          "snapshot": self.store.revision, "extension_of": task,
                          "extension_reason": nonempty(reason, "expansion reason")}
            revised = self.store.put("task", {"packet": new_packet, "packet_hash": digest(new_packet)})
            self.store.decide(revised, "ready", {"previous": task})
            return revised

    def expand_semantics(self, task: str, capsule: str, selectors: list[str], reason: str,
                         *, max_chars: int = 128000, include_theorem_proofs: bool = False) -> str:
        """A new exact packet, restricted to one capsule already supplied.

        No new record, verdict, receipt or arbitrary text can enter this seam.
        Expansion cannot repair the exposure of an earlier native run.
        """
        original = self.store.get(task, 'task')['data']['packet']
        if type(max_chars) is not int or not 1000 <= max_chars <= 8 * 1024 * 1024:
            raise StateError('Semantic expansion requires an explicit budget from 1000 to 8388608 characters')
        if type(include_theorem_proofs) is not bool:
            raise StateError('Theorem-proof exposure must be an exact boolean')
        rationale = nonempty(reason, 'expansion reason')
        projected = original['records'].get(capsule)
        artifact = self.store.get(capsule, 'artifact')
        authoritative = {}
        self._closure(original['target'], authoritative, evidence=True)
        if (projected is None or projected.get('hash') != artifact['hash']
                or capsule not in authoritative
                or authoritative[capsule]['hash'] != artifact['hash']
                or original.get('target_hash') != self.store.get(original['target'])['hash']
                or artifact['data'].get('media_type') != CAPSULE_MEDIA
                or 'semantic_view' not in projected.get('data', {})):
            raise StateError('Semantic expansion requires this already admitted exact capsule')
        if not self.r._scope_current(capsule):
            raise StateError('Semantic capsule provenance is not current')
        report = json.loads(artifact['data']['text'])
        old_view = projected['data']['semantic_view']
        admitted = validate_view(report, old_view)
        if not isinstance(selectors, list) or not selectors:
            raise StateError('Expansion requires exact declaration selectors')
        union = sorted(admitted | set(selectors)) if all(isinstance(s, str) for s in selectors) else selectors
        include_theorem_proofs |= old_view.get('proof_body_policy') == SUPPLIED_PROOFS
        view = semantic_view(report, selectors=union, max_chars=max_chars,
                             include_theorem_proofs=include_theorem_proofs)
        if set(view['declarations']) != set(union):
            raise StateError('Requested exact semantic units exceed the expansion budget; increase the explicit budget')
        with self.store.transaction():
            records = dict(original['records'])
            records[capsule] = {**projected, 'data': {**projected['data'], 'semantic_view': view}}
            packet = {**original, 'records': records, 'snapshot': self.store.revision, 'extension_of': task,
                'extension_reason': 'Mechanically expanded exact units of an already admitted semantic capsule',
                'semantic_expansion': {
                    'capsule': capsule, 'capsule_hash': artifact['hash'], 'selectors': sorted(view['declarations']),
                    'max_chars': max_chars,
                    'include_theorem_proofs': include_theorem_proofs,
                    'parent_packet_hash': self.store.get(task)['data']['packet_hash']}}
            revised = self.store.put('task', {'packet': packet, 'packet_hash': digest(packet)})
            self.store.decide(revised, 'ready', {'previous': task, 'reason': rationale})
            return revised

    def _formal_coverage(self, packet, checks):
        relevant = {'formal-target-fidelity', 'formal-environment', 'foundations', 'formal-receipt'} & set(checks)
        if not relevant:
            return
        required_records = {}
        self._closure(packet['target'], required_records, evidence=True)
        admissions = packet.get('admitted_sources', [])
        if not isinstance(admissions, list) or any(not isinstance(i, str) for i in admissions):
            raise StateError('Formal packet admissions are malformed')
        for identifier in admissions:
            source = self.store.get(identifier)
            self._allow_extra(source, packet['independence'], packet['literature'], packet['claim'])
            if source['kind'] == 'learning':
                required_records[identifier] = self._learning_record(identifier)
            else:
                self._closure(identifier, required_records, evidence=True,
                              admission_rationale=packet['independence'] != 'blind')
        if packet.get('dependency_evidence'):
            subject = self.store.get(packet['target'], 'counterexample')['data']
            forest = packet['dependency_evidence']['selected']
            if any(root['claim'] not in subject['dependencies'] for root in roots(forest)):
                raise StateError('Formal packet dependency witness targets an unrelated claim')
            for node in nodes(forest).values():
                self._closure(node['inference'], required_records, evidence=True)
        if set(packet['records']) != set(required_records):
            raise StateError('Formal packet omits required evidence or injects unadmitted records')
        for identifier, required in required_records.items():
            if required['kind'] != 'artifact' or required['data'].get('media_type') != CAPSULE_MEDIA:
                if packet['records'][identifier] != required:
                    raise StateError('Formal packet changes an exact required evidence projection')
        for required in required_records.values():
            if required['kind'] != 'formal_receipt':
                continue
            receipt = self.store.get(required['id'], 'formal_receipt')['data']
            if receipt.get('receipt_version') not in RECEIPT_VERSIONS:
                continue
            item = packet['records'].get(required['id'])
            if item != required:
                raise StateError('Formal review receipt policy/identity header is incomplete or changed')
            capsule = receipt.get('semantic_artifact')
            exposed = packet['records'].get(capsule, {}).get('data', {}).get('semantic_view')
            if exposed is None:
                raise StateError('Positive formal review requires an exact compiled semantic view')
            artifact = self.store.get(capsule, 'artifact')
            expected_capsule = required_records[capsule]
            supplied_capsule = packet['records'][capsule]
            if ({k: v for k, v in supplied_capsule.items() if k != 'data'}
                    != {k: v for k, v in expected_capsule.items() if k != 'data'}
                    or {k: v for k, v in supplied_capsule['data'].items() if k != 'semantic_view'}
                    != {k: v for k, v in expected_capsule['data'].items() if k != 'semantic_view'}):
                raise StateError('Formal semantic view header differs from its exact safe capsule projection')
            report = json.loads(artifact['data']['text'])
            for key in ('helper_artifact', 'reference_artifact', 'resolution_artifact', 'toolchain'):
                identifier = receipt[key]
                canonical_record = self.store.get(identifier)
                expected = {'id': identifier, 'kind': canonical_record['kind'], 'hash': canonical_record['hash'],
                            'data': self._project_data(canonical_record['kind'], canonical_record['data'])}
                if packet['records'].get(identifier) != expected:
                    raise StateError('Formal review lacks the exact helper/profile/resolution/toolchain identities')
            validate_view(report, exposed)
            if relevant & {'formal-target-fidelity', 'formal-environment'} and exposed.get('statement_complete') is not True:
                raise StateError('Positive fidelity review requires complete compiled statement coverage; expand the packet')
            if relevant & {'foundations', 'formal-receipt', 'formal-environment'} and exposed.get('foundations_complete') is not True:
                raise StateError('Positive foundations review requires complete actual foundation coverage; expand the packet')
            original = {}
            self._closure(receipt['target'], original, evidence=False)
            for assumption in receipt['assumptions']:
                self._closure(assumption, original, evidence=False)
            for identifier, required in original.items():
                if packet['records'].get(identifier) != required:
                    raise StateError('Positive formal review lacks the exact original target/definitions/assumptions')

    def start(self, task: str, conversation_id: str, *, host: str,
              dispatch_evidence: str, tools: list[str], inherited_history: bool) -> str:
        """Import an operator report; it cannot qualify an independent review."""
        return self._start(task, conversation_id, host=host, dispatch_evidence=dispatch_evidence,
                           tools=tools, inherited_history=inherited_history, captured=False)

    def _start_captured(self, task: str, conversation_id: str, *, host: str,
                        dispatch_evidence: str, tools: list[str], inherited_history: bool) -> str:
        """Trusted recorder seam. Not exposed as a JSON/CLI operation."""
        data = self.store.get(dispatch_evidence, 'artifact')['data']['text']
        try:
            capture = json.loads(data)
        except ValueError as error:
            raise StateError('Captured dispatch requires structured transport evidence') from error
        packet = self.packet(task)
        if (capture.get('kind') != 'native-dispatch-capture' or capture.get('task_id') != task
                or capture.get('packet_hash') != packet['packet_hash'] or capture.get('conversation_id') != conversation_id
                or capture.get('host') != host or capture.get('declared_tools') != tools
                or capture.get('declared_inherited_history') is not inherited_history):
            raise StateError('Captured dispatch does not match task and declared isolation policy')
        return self._start(task, conversation_id, host=host, dispatch_evidence=dispatch_evidence,
                           tools=tools, inherited_history=inherited_history, captured=True)

    def _start(self, task: str, conversation_id: str, *, host: str,
               dispatch_evidence: str, tools: list[str], inherited_history: bool, captured: bool) -> str:
        data = self.store.get(task, "task")["data"]
        self.store.get(dispatch_evidence, "artifact")
        nonempty(conversation_id, "native conversation ID")
        if host != "antigravity":
            raise StateError("This workflow requires native Antigravity dispatch")
        if not isinstance(tools, list) or tools or inherited_history is not False:
            raise StateError("Mathematical worker policy requires no tools and no inherited history")
        with self.store.transaction():
            if self.store.status(task) not in ({'ready', 'awaiting-native'} if captured else {'ready'}):
                raise StateError("Task is not ready for a new independent run")
            if any(r["data"]["conversation_id"] == conversation_id for r in self.store.records("run")):
                raise StateError("Native conversation already used; cannot relabel reused context as fresh")
            run = self.store.put("run", {"task": task, "conversation_id": conversation_id, "host": host,
                "dispatch_evidence": dispatch_evidence, "declared_tools": tools, "declared_inherited_history": False,
                "packet_hash": data["packet_hash"], "model_policy": "inherit",
                **({key: value for key, value in json.loads(self.store.get(dispatch_evidence)['data']['text']).items()
                    if key in {'native_context_profile', 'native_context_admission'}} if captured else {})})
            self.store.event('capture-qualification', run, {'captured': captured})
            self.store.decide(run, "running", {"task": task})
            self.store.decide(task, "running", {"run": run})
            return run

    def expose(self, run: str, category: str, evidence: str, description: str) -> str:
        self.store.get(run, "run")
        self.store.get(evidence, "artifact")
        if category not in {"other-verdict", "discovery-history", "uncontrolled-tool", "extra-mathematics", "unknown"}:
            raise StateError("Unknown exposure category")
        with self.store.transaction():
            return self.store.put("exposure", {"run": run, "category": category,
                "artifact": evidence, "description": nonempty(description, "exposure description")})

    def finish(self, run: str, artifact: str, host_receipt: str, *, outcome: str,
               verdict: str | None = None, checks: list[str] | None = None) -> str:
        return self._finish(run, artifact, host_receipt, outcome=outcome, verdict=verdict, checks=checks, captured=False)

    def _finish_captured(self, run: str, artifact: str, host_receipt: str, *, outcome: str,
                         verdict: str | None = None, checks: list[str] | None = None) -> str:
        return self._finish(run, artifact, host_receipt, outcome=outcome, verdict=verdict, checks=checks, captured=True)

    def _finish(self, run: str, artifact: str, host_receipt: str, *, outcome: str,
                verdict: str | None, checks: list[str] | None, captured: bool) -> str:
        execution = self.store.get(run, "run")["data"]
        output_text = self.store.get(artifact, "artifact")["data"]["text"]
        receipt = self.store.get(host_receipt, "artifact")["data"]["text"]
        try:
            envelope = json.loads(receipt)
        except ValueError as error:
            raise StateError("Native completion receipt must be a JSON object") from error
        if not isinstance(envelope, dict) or envelope.get("conversation_id") != execution["conversation_id"] or envelope.get("status") != "SUCCESS":
            raise StateError("Host completion does not match successful dispatched conversation")
        if envelope.get("response") != output_text:
            raise StateError("Result artifact differs from the host's actual response")
        task = self.store.get(execution["task"], "task")["data"]["packet"]
        output = worker_result(task, execution['task'], execution['packet_hash'], output_text)
        checks = [] if checks is None else checks
        if (not isinstance(checks, list) or any(not isinstance(c, str) or not c.strip() for c in checks)
                or output['outcome'] != outcome or output.get('verdict') != verdict
                or sorted(set(output.get('checks', []))) != sorted(set(checks))):
            raise StateError('Recorded result differs from the worker\'s declared assessment')
        with self.store.transaction():
            if self.store.status(run) != "running":
                raise StateError("Run already finished or not running")
            result = self.store.put("result", {"run": run, "task": execution["task"],
                "packet_hash": execution["packet_hash"], "target": task["target"],
                "target_hash": task["target_hash"], "artifact": artifact, "host_receipt": host_receipt,
                "result_contract_profile": RESULT_CONTRACT_PROFILE,
                "outcome": outcome, "verdict": verdict, "checks": sorted(set(checks))})
            self.store.decide(run, "completed", {"result": result})
            self.store.decide(execution["task"], "completed", {"result": result})
            self.store.event('completion-qualification', run, {'captured': captured, 'result': result})
            return result

    def review_provenance(self, run: str, target: str, verdict: str, artifact: str, checks: list[str]) -> dict:
        if not isinstance(checks, list) or not checks or any(not isinstance(c, str) or not c.strip() for c in checks):
            raise StateError("Review checks must be an exact nonempty list of strings")
        execution = self.store.get(run, "run")
        if self.store.status(run) != "completed":
            raise StateError("Review requires completed native run")
        task = self.store.get(execution["data"]["task"], "task")["data"]["packet"]
        target_record = self.store.get(target)
        if task.get('target') != target or task.get('target_hash') != target_record['hash']:
            raise StateError('Review task does not bind the exact canonical target')
        if self.store.status(execution["data"]["task"]) != "completed":
            raise StateError("Review task is no longer eligible")
        results = [r for r in self.store.records("result") if r["data"]["run"] == run]
        if len(results) != 1:
            raise StateError("Review requires one exact native result")
        data = results[0]["data"]
        if self.store.status(results[0]["id"]) == "withdrawn":
            raise StateError("Native result withdrawn")
        for evidence in [data["artifact"], data["host_receipt"], execution["data"]["dispatch_evidence"]]:
            if self.store.status(evidence) == "withdrawn":
                raise StateError("Native provenance evidence withdrawn")
        if (data["outcome"] != "review" or data["target"] != target or data["verdict"] != verdict
                or data.get('target_hash') != target_record['hash'] or task.get('role') not in REVIEW_ROLES
                or not set(checks).issubset(task['checks'])
                or data["artifact"] != artifact or data["checks"] != sorted(set(checks))):
            raise StateError("Review does not match the native result")
        if verdict == 'pass':
            worker_result(task, execution['data']['task'], execution['data']['packet_hash'],
                          self.store.get(artifact, 'artifact')['data']['text'])
            self._formal_coverage(task, checks)
        contaminated = any(e["data"]["run"] == run for e in self.store.records("exposure"))
        admission = execution['data'].get('native_context_admission')
        profile = execution['data'].get('native_context_profile')
        receipt_envelope = json.loads(self.store.get(data['host_receipt'], 'artifact')['data']['text'])
        if receipt_envelope.get('producer_evidence'):
            from .native_controls import retained_context
            profile = retained_context(self.r, execution).get('native_context_profile', profile)
        if profile:
            from .native_controls import retained_admission, retained_context
            qualified = retained_admission(self.r, execution)
            admission = retained_context(self.r, execution).get('native_context_admission')
            contaminated = contaminated or not qualified
        independent = task["independence"] == "blind" and not contaminated
        qualification = self.store.db.execute("SELECT payload FROM events WHERE type='capture-qualification' AND target=?", (run,)).fetchone()
        captured = qualification is not None and json.loads(qualification['payload']).get('captured') is True
        completion = self.store.db.execute("SELECT payload FROM events WHERE type='completion-qualification' AND target=?", (run,)).fetchone()
        captured = captured and completion is not None and json.loads(completion['payload']).get('captured') is True
        return {"result": results[0]["id"], "task": execution["data"]["task"],
                "conversation_id": execution["data"]["conversation_id"],
                'qualification_scope': 'observed-public-task-context' if captured else 'operator-report',
                'effective_host_isolation_verified_by_capture': False,
                **({'native_context_profile': profile,
                    'native_context_admission': admission,
                    'native_context_current': qualified,
                    'recorded_input_scope': 'producer-recorded-input-and-no-recorded-tool-use'}
                   if profile else {}),
                "exposure": ('independent' if captured else 'reported-independent') if independent else "informed"}
