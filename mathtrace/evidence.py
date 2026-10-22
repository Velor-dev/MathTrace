"""Root-executed computation and reviewed Lean checking with immutable receipts.

No program is executed automatically from an agent response. Root registers exact
source and checks it before invoking these explicit operations. Tool-free workers
cannot reach this module through native tool calls.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from .research import Research, nonempty
from .store import StateError, InputContractError, digest
from .toolchain import verify_toolchain
from .backend import invoke, EXECUTION_PROTOCOL
from .sandbox import compute, check_lean
from .execution import Executions, execution_timeout
from .formal import (RECEIPT_VERSION, PROFILE, FOUNDATIONS, CAPSULE_MEDIA, blob_bytes,
                     compiled_bundle, process_passed, validate_report, validate_resolution,
                     MODE_RECEIPT_VERSION, RECEIPT_VERSIONS, execution_assurance)


def file_hash(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def library_manifest(path: str) -> dict:
    root = Path(path).resolve()
    if not root.is_dir():
        raise StateError('Library root does not exist')
    files = {}
    for item in sorted(root.rglob('*')):
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise StateError('Redirected path in formal library')
        if item.is_file():
            files[item.relative_to(root).as_posix()] = file_hash(item)
    return {'root': str(root), 'files': files}


class Evidence:
    def __init__(self, research: Research):
        self.r = research
        self.store = research.store

    def experiment(self, target: str, source: str, scope: str, *, author: str,
                   inputs: dict | None = None) -> str:
        self.store.get(target, 'claim')
        self.store.get(source, 'artifact')
        if inputs is not None and not isinstance(inputs, dict):
            raise StateError('Experiment inputs must be an exact JSON object')
        with self.store.transaction():
            return self.store.put('experiment', {'target': target, 'source': source,
                'scope': nonempty(scope, 'finite/experimental scope'), 'inputs': inputs or {},
                'author': nonempty(author, 'author'), 'evidence_class': 'computation-proposal'})

    def _complete_execution(self, identifier: str, result: dict) -> str:
        executions = Executions(self.r)
        directory = executions.directory(identifier)
        producer = result.get('_producer')
        if not isinstance(producer, dict):
            raise StateError('Execution result lacks an attributable recorder envelope')
        envelope = {**producer, 'result': {k: v for k, v in result.items() if k != '_producer'}}
        if (directory / 'terminal.json').is_file():
            import json
            if digest(json.loads((directory / 'terminal.json').read_text(encoding='utf-8'))) != digest(envelope):
                raise StateError('Recorder journal and returned observation disagree')
            response = executions.recover(identifier, self._execution_writer(identifier))
        else:
            response = executions.terminal(identifier, envelope, self._execution_writer(identifier))
        if not response['ok']:
            raise StateError(response['error'])
        return response['receipt']

    def _execution_writer(self, identifier):
        operation = self.store.get(identifier, 'execution')['data']['operation']
        return lambda data, result: (self._write_formal(identifier, result) if operation == 'formal'
                                    else self._write_experiment(identifier, result))

    def inspect_execution(self, identifier: str) -> dict:
        return Executions(self.r).inspect(identifier)

    def recover_execution(self, identifier: str) -> dict:
        return Executions(self.r).recover(identifier, self._execution_writer(identifier))

    def _execution_error(self, identifier, error):
        executions = Executions(self.r)
        executions.uncertain(identifier, error)
        # Do not infer termination from an exception. A retained producer
        # observation can separately establish it, even after transport failure.
        if (executions.directory(identifier) / 'terminal.json').is_file():
            executions.recover(identifier, self._execution_writer(identifier))

    def run_experiment(self, identifier: str, *, timeout: float = 60,
                       rerun_of: str | None = None, reason: str | None = None,
                       execution_mode: str | None = None) -> str:
        timeout = execution_timeout(timeout)
        plan = self.store.get(identifier, 'experiment')
        data = plan['data']
        if data.get('evidence_class') != 'computation-proposal':
            raise StateError('Select an experiment proposal, not a prior receipt')
        source = self.store.get(data['source'], 'artifact')['data']['text']
        executions = Executions(self.r)
        selected, protocol = executions.selection(identifier, execution_mode, rerun_of)
        request = {'source': source, 'inputs': data['inputs'], 'timeout': timeout}
        metadata = {}
        if protocol:
            request.update(execution_mode=selected, execution_protocol=protocol)
            metadata = {'execution_mode': selected, 'execution_protocol': protocol}
        attempt, new = executions.begin(identifier, 'compute', request, metadata=metadata,
                                        rerun_of=rerun_of, reason=reason)
        if not new:
            response = self.recover_execution(attempt)
            if not response['ok']:
                raise StateError(response['error'])
            return response['receipt']
        try:
            result = (invoke(request, journal=executions.journal(attempt)) if protocol else
                      compute(source, data['inputs'], timeout, journal=executions.journal(attempt)))
            return self._complete_execution(attempt, result)
        except Exception as error:
            self._execution_error(attempt, error)
            raise

    def _write_experiment(self, execution: str, result: dict) -> str:
        attempt = self.store.get(execution, 'execution')['data']
        plan = self.store.get(attempt['plan'], 'experiment')
        data = plan['data']
        selected = attempt['metadata'].get('execution_mode', 'bubblewrap')
        isolated = bool(result.get('namespace_setup'))
        if selected == 'direct' and (isolated or result.get('isolation_established') is not False):
            raise StateError('Direct computation cannot claim sandbox isolation')
        observed = isolated or selected == 'direct'
        receipt = self.store.put('experiment', {'target': data['target'], 'plan': plan['id'],
            'plan_hash': plan['hash'], 'source': data['source'], 'scope': data['scope'],
            'inputs_hash': digest(data['inputs']), 'result': result, 'execution': execution,
            'execution_environment': result['execution_environment'],
            'evidence_class': 'computational-observation' if observed else 'execution-failure',
            'execution_mode': selected, 'isolation_established': isolated, 'author': 'root-execution'})
        self.store.decide(receipt, 'observed' if observed else 'failed', {
            'reason': 'Actual process result; not mathematical proof', 'isolation_established': isolated})
        return receipt

    def formal_plan(self, target: str, source: str, symbol: str, expected_type: str, *,
                    author: str, assumptions: list[str] | None = None,
                    allowed_axioms: list[str] | None = None, outcome: str = 'proof',
                    library_paths: list[str] | None = None) -> str:
        claim = self.store.get(target, 'claim')
        contract = self.store.get(claim['data']['contract'], 'contract')['data']
        if outcome not in {'proof', 'disproof'} or (outcome == 'disproof' and not contract['allow_disproof']):
            raise InputContractError('Formal outcome is not permitted by this contract')
        text = self.store.get(source, 'artifact')['data']['text']
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_'.]*", symbol):
            raise InputContractError('Use an explicit ASCII Lean declaration alias for checking')
        nonempty(expected_type, 'formal target type')
        if assumptions is not None:
            if not isinstance(assumptions, list):
                raise StateError('assumptions must be an exact list of assumption IDs or None')
            for assumption in assumptions:
                if not isinstance(assumption, str) or not assumption.strip():
                    raise StateError('assumption entries must be nonempty strings')
                self.store.get(assumption, 'assumption')
        if library_paths is not None:
            if not isinstance(library_paths, list):
                raise StateError('library_paths must be an exact list of paths or None')
            for path in library_paths:
                if not isinstance(path, str) or not path.strip():
                    raise StateError('library_paths entries must be nonempty strings')
        if allowed_axioms is not None:
            if not isinstance(allowed_axioms, list):
                raise StateError('allowed_axioms must be an exact list of strings or None')
            for axiom in allowed_axioms:
                if not isinstance(axiom, str) or not axiom.strip():
                    raise InputContractError('allowed_axioms entries must be nonempty strings')
            if len(allowed_axioms) != len(set(allowed_axioms)):
                raise InputContractError('allowed_axioms must not contain duplicate entries')
            if 'sorryAx' in allowed_axioms:
                raise InputContractError('Invalid axiom policy; sorryAx cannot be admitted')
        axioms = contract.get('allowed_axioms', []) if allowed_axioms is None else allowed_axioms
        if not set(axioms).issubset(contract.get('allowed_axioms', [])):
            raise InputContractError('Formal plan cannot enlarge the contract foundation')
        if 'sorryAx' in axioms:
            raise InputContractError('Invalid axiom policy; sorryAx cannot be admitted')
        if set(axioms) - set(FOUNDATIONS):
            raise InputContractError('This checking profile requires exact schemas for unsupported custom axiom names')
        nonce = 'mathTraceReceipt_' + uuid.uuid4().hex
        libraries = [library_manifest(path) for path in library_paths or []]
        # Reviewers inspect the actual generated source, including this type bridge.
        generated = (text + '\n\n' + f'public theorem _root_.{nonce} : ({expected_type}) := {symbol}\n'
                     + f'#print axioms {nonce}\n')
        with self.store.transaction():
            helper_text = Path(__file__).with_name('lean_inspector.lean').read_text(encoding='utf-8')
            helper_sha256 = hashlib.sha256(helper_text.encode()).hexdigest()
            helper = self.store.put('artifact', {'text': helper_text, 'media_type': 'text/x-lean',
                'content_hash': digest(helper_text), 'sha256': helper_sha256, 'artifact_role': 'formal-helper'})
            check_source = self.store.put('artifact', {'text': generated, 'media_type': 'text/x-lean',
                                                       'content_hash': digest(generated)})
            return self.store.put('formal_plan', {'target': target, 'source': source,
                'receipt_version': RECEIPT_VERSION, 'checking_profile': PROFILE,
                'helper_artifact': helper, 'helper_sha256': helper_sha256,
                'check_source': check_source, 'symbol': symbol, 'check_symbol': nonce,
                'expected_type': expected_type, 'assumptions': assumptions or [],
                'libraries': libraries,
                'library_origin': 'operator-selected exact local trees; publisher identity not verified',
                'allowed_axioms': sorted(set(axioms)), 'author': nonempty(author, 'author'), 'outcome': outcome})

    def run_lean(self, identifier: str, *, toolchain: str, timeout: float = 120,
                 library_paths: list[str] | None = None,
                 rerun_of: str | None = None, reason: str | None = None,
                       execution_mode: str | None = None) -> str:
        timeout = execution_timeout(timeout)
        plan = self.store.get(identifier, 'formal_plan')
        data = plan['data']
        if data.get('receipt_version') not in RECEIPT_VERSIONS or data.get('checking_profile') != PROFILE:
            raise StateError('Legacy formal plan requires a new modern plan/check; recover old attempts explicitly')
        helper = self.store.get(data['helper_artifact'], 'artifact')
        helper_source = helper['data']['text']
        if (hashlib.sha256(helper_source.encode()).hexdigest() != data['helper_sha256']
                or not self.r._scope_current(helper['id'])):
            raise StateError('Pinned formal helper evidence is not current')
        source_reviews = self.r._reviews(identifier, {'formal-source-integrity', 'formal-target-fidelity', 'foundations'})
        if self.r._blocked(identifier) or not self.r._scope_current(identifier):
            raise StateError('Formal plan or target has an open objection or invalid scope')
        toolchain_record = self.store.get(toolchain, 'toolchain')
        if toolchain_record['data'].get('version') != 'v4.30.0':
            raise StateError('This checking profile supports only the pinned Lean v4.30.0 release')
        if self.store.status(toolchain) != 'installed' or not self.r._scope_current(toolchain):
            raise StateError('Toolchain is not an installed trusted distribution with current scope')
        executions = Executions(self.r)
        selected, protocol = executions.selection(identifier, execution_mode, rerun_of)
        receipt_protocol = MODE_RECEIPT_VERSION if protocol else data['receipt_version']
        pinned = verify_toolchain(toolchain_record)
        binary = pinned['executable']
        libraries = data.get('libraries', [])
        if library_paths is not None:
            if not isinstance(library_paths, list):
                raise StateError('library_paths must be an exact list of paths or None')
            for path in library_paths:
                if not isinstance(path, str) or not path.strip():
                    raise StateError('library_paths entries must be nonempty strings')
            if [str(Path(path).resolve()) for path in library_paths] != [item['root'] for item in libraries]:
                raise StateError('Execution cannot change reviewed library roots; create and review a new formal plan')
        if any(library_manifest(item['root']) != item for item in libraries):
            raise StateError('Formal library bytes changed after plan preparation; create and review a new plan')
        if protocol:
            from .toolchain import execution_target
            if toolchain_record['data'].get('platform') != execution_target(selected)[1]:
                raise StateError('Toolchain does not match selected execution target')
        executable_hash = file_hash(Path(binary))
        source = self.store.get(data['check_source'], 'artifact')['data']['text']
        verification = {'protocol': receipt_protocol, 'profile': PROFILE,
                        'check_symbol': data['check_symbol'], 'helper_source': helper_source}
        executions = Executions(self.r)
        request = {'operation': 'formal', 'source': source,
            'toolchain': toolchain_record['data'], 'libraries': libraries, 'timeout': timeout,
            'verification': verification}
        metadata = {'toolchain': toolchain, 'toolchain_hash': toolchain_record['hash'],
                    'receipt_version': receipt_protocol, 'checking_profile': PROFILE,
                    'helper_artifact': helper['id'], 'helper_hash': helper['hash'],
                    'helper_sha256': data['helper_sha256'], 'check_symbol': data['check_symbol'],
                    'checker_path': binary, 'checker_hash': executable_hash}
        if protocol:
            request.update(execution_mode=selected, execution_protocol=protocol)
            metadata.update(execution_mode=selected, execution_protocol=protocol)
        attempt, new = executions.begin(identifier, 'formal', request, metadata=metadata,
                                        rerun_of=rerun_of, reason=reason)
        if not new:
            response = self.recover_execution(attempt)
            if not response['ok']:
                raise StateError(response['error'])
            return response['receipt']
        try:
            result = (invoke(request, journal=executions.journal(attempt)) if protocol else
                      check_lean(source, toolchain_record['data'], libraries, timeout,
                                 journal=executions.journal(attempt), verification=verification))
            return self._complete_execution(attempt, result)
        except Exception as error:
            self._execution_error(attempt, error)
            raise

    def _write_formal(self, execution_id: str, execution: dict) -> str:
        attempt = self.store.get(execution_id, 'execution')['data']
        if attempt['metadata'].get('receipt_version') not in RECEIPT_VERSIONS:
            return self._write_legacy_formal(execution_id, execution)
        plan = self.store.get(attempt['plan'], 'formal_plan')
        data, metadata = plan['data'], attempt['metadata']
        receipt_protocol = metadata['receipt_version']
        selected = metadata.get('execution_mode', 'bubblewrap')
        toolchain = self.store.get(metadata['toolchain'], 'toolchain')
        source = self.store.get(data['check_source'], 'artifact')
        helper = self.store.get(data['helper_artifact'], 'artifact')
        issues, report, compiled, file_set = [], None, {}, None
        def failure(reason):
            issues.append(str(reason))
        try:
            compiled, file_set = compiled_bundle(execution)
            if selected == 'direct' and not isinstance(execution.get('staged_roots'), dict):
                raise StateError('Native staged root descriptor is absent')
            if not all(process_passed(execution.get(k), selected) for k in ('result', 'replay', 'version')):
                raise StateError('Compilation/checked-target process did not complete successfully under the recorded backend')
            if execution.get('artifact_collection_error') is not None:
                raise StateError('Compiled output collection did not complete without error')
            if execution.get('verification_error') is not None or not execution.get('resolved_inputs'):
                raise StateError(execution.get('verification_error') or 'Actual resolved input binding is absent')
            raw_report = blob_bytes(execution.get('semantic_output'), limit=64 * 1024 * 1024)
            parsed = json.loads(raw_report)
            validate_report(parsed, data['check_symbol'], data['allowed_axioms'])
            report = parsed
            expected_binding = {'protocol': receipt_protocol, 'profile': PROFILE,
                'check_symbol': data['check_symbol'], 'helper_sha256': data['helper_sha256'],
                'source_sha256': hashlib.sha256(source['data']['text'].encode()).hexdigest(),
                'compiled_file_set_hash': digest(file_set)}
            if execution.get('verification_binding') != expected_binding:
                raise StateError('Verification observation does not bind exact source/helper/object parts')
            validate_resolution(report.get('resolution'), execution.get('resolved_inputs'),
                                toolchain['data'], data['libraries'], file_set,
                                roots=execution.get('staged_roots') if selected == 'direct' else None)
            verify_toolchain(toolchain)
            if any(library_manifest(item['root']) != item for item in data['libraries']):
                raise StateError('Reviewed library bytes changed during execution')
        except (StateError, ValueError, TypeError, KeyError, RecursionError, OSError) as error:
            failure(error)
        artifacts = {}
        with self.store.transaction():
            def retain(role, text, media_type, **extra):
                identifier = self.store.put('artifact', {'text': text, 'media_type': media_type,
                    'content_hash': digest(text), 'source_execution': execution_id,
                    'artifact_role': role, **extra})
                artifacts[identifier] = self.store.get(identifier)['hash']
                return identifier
            parts = {}
            supplemental = execution.get('compiled_parts')
            supplemental = supplemental if isinstance(supplemental, dict) else {}
            for name in ('Main.olean', 'Main.olean.server', 'Main.olean.private', 'Main.ir'):
                blob = execution.get('compiled_output') if name == 'Main.olean' else supplemental.get(name)
                if blob is not None:
                    try:
                        blob_bytes(blob)
                        parts[name] = retain('compiled-part', blob['content'], 'application/x-lean-olean',
                            encoding='base64', sha256=blob['sha256'], size=blob['size'], filename=name)
                    except (StateError, TypeError, KeyError) as error:
                        failure(error)
            semantic = reference = resolution = None
            if execution.get('semantic_output'):
                try:
                    raw = blob_bytes(execution['semantic_output'], limit=64 * 1024 * 1024)
                    semantic = retain('checked-semantics', raw.decode('utf-8'), CAPSULE_MEDIA,
                                      sha256=hashlib.sha256(raw).hexdigest())
                    if report is not None:
                        reference = retain('primitive-reference', json.dumps(report['reference_profile'], sort_keys=True),
                                           'application/vnd.mathtrace.primitive-reference+json')
                except (StateError, UnicodeError, KeyError, TypeError) as error:
                    failure(error)
            if execution.get('resolved_inputs'):
                try:
                    resolution = retain('resolved-inputs', json.dumps(execution['resolved_inputs'], sort_keys=True),
                                        'application/vnd.mathtrace.resolved-inputs+json')
                except (TypeError, ValueError, RecursionError) as error:
                    failure(error)
            for identifier in (plan['id'], source['id'], helper['id'], toolchain['id'], execution_id):
                artifacts[identifier] = self.store.get(identifier)['hash']
            manifest = {'records': artifacts, 'compiled_file_set': file_set,
                        'execution_request_hash': attempt['request_hash'], 'protocol': receipt_protocol,
                        'checking_profile': PROFILE}
            receipt = self.store.put('formal_receipt', {
                **({'execution_mode': selected, 'execution_assurance': execution_assurance(execution, selected)}
                   if receipt_protocol == MODE_RECEIPT_VERSION else {}),
                'receipt_version': receipt_protocol, 'checking_profile': PROFILE,
                'target': data['target'], 'plan': plan['id'], 'plan_hash': plan['hash'],
                'source': source['id'], 'source_reviews': attempt['source_reviews'], 'execution': execution_id,
                'symbol': data['symbol'], 'check_symbol': data['check_symbol'], 'expected_type': data['expected_type'],
                'assumptions': data['assumptions'], 'outcome': data['outcome'], 'allowed_axioms': data['allowed_axioms'],
                'toolchain': toolchain['id'], 'toolchain_hash': toolchain['hash'], 'libraries': data['libraries'],
                'helper_artifact': helper['id'], 'helper_hash': helper['hash'], 'helper_sha256': data['helper_sha256'],
                'checker_path': metadata['checker_path'], 'checker_hash': metadata['checker_hash'],
                'checker': 'pinned-Lean-checked-compiled-target',
                'compiled_artifact': parts.get('Main.olean'), 'compiled_parts': parts, 'compiled_file_set': file_set,
                'semantic_artifact': semantic, 'reference_artifact': reference, 'resolution_artifact': resolution,
                'evidence_manifest': manifest, 'evidence_manifest_hash': digest(manifest),
                'observation_result_hash': digest(execution), 'verification_binding': execution.get('verification_binding'),
                'kernel_replay': 'same-kernel-pinned-primitive-target', 'replay': execution.get('replay'),
                'replay_input_hash': file_set['Main.olean']['sha256'] if file_set else None,
                'result': execution.get('result'), 'version': execution.get('version'),
                'axioms': report['semantics']['axioms'] if report else None,
                'failures': issues, 'source_to_object_correspondence': 'unverified',
                'compilation_association': 'exact reviewed source supplied; outputs collected from terminated compilation',
                'library_origin': data['library_origin'], 'imported_bytes_retained_in_canonical_state': False,
                'assurance_limitations': 'same-kernel checking; original-target fidelity requires separate complete-context review',
                'author': 'root-checker-execution'})
            self.store.decide(receipt, 'failed' if issues else 'checked', {
                'reason': 'Retained compiled-target verification evidence', 'passed': not issues, 'failures': issues})
            return receipt

    def _write_legacy_formal(self, execution_id: str, execution: dict) -> str:
        attempt = self.store.get(execution_id, 'execution')['data']
        identifier, source_reviews = attempt['plan'], attempt['source_reviews']
        plan = self.store.get(identifier, 'formal_plan')
        data = plan['data']
        toolchain = attempt['metadata']['toolchain']
        toolchain_record = self.store.get(toolchain, 'toolchain')
        binary, executable_hash = attempt['metadata']['checker_path'], attempt['metadata']['checker_hash']
        libraries = data.get('libraries', [])
        version, result = execution['version'], execution['result']
        compiled = execution.get('compiled_output')
        replay = execution.get('replay')
        changed_environment = False
        try:
            verify_toolchain(toolchain_record)
            changed_environment = any(library_manifest(item['root']) != item for item in libraries)
        except (StateError, OSError):
            changed_environment = True
        symbol = re.escape(data['check_symbol'])
        no_axioms = re.findall(r"'" + symbol + r"' does not depend on any axioms", result['stdout'])
        with_axioms = re.findall(r"'" + symbol + r"' depends on axioms:\s*\[([^\]]*)\]", result['stdout'])
        axioms = []
        report_count = len(no_axioms) + len(with_axioms)
        if with_axioms:
            axioms = [a.strip() for a in with_axioms[0].split(',') if a.strip()]
        accepted = bool(result['exit_code'] == 0 and not result['timed_out'] and not changed_environment
                        and report_count == 1 and set(axioms).issubset(data['allowed_axioms'])
                        and 'sorryAx' not in axioms and compiled is not None
                        and not result.get('output_limited') and result.get('namespace_setup') is not None
                        and replay and replay['exit_code'] == 0 and not replay['timed_out']
                        and not replay.get('output_limited') and replay.get('namespace_setup') is not None
                        and version['exit_code'] == 0 and re.search(r'Lean \(version 4\.', version['stdout']))
        with self.store.transaction():
            compiled_artifact = self.store.put('artifact', {
                'text': compiled['content'], 'encoding': 'base64', 'media_type': 'application/x-lean-olean',
                'content_hash': digest(compiled['content']), 'sha256': compiled['sha256'],
                'size': compiled['size']}) if compiled else None
            receipt = self.store.put('formal_receipt', {'target': data['target'], 'plan': identifier,
                'plan_hash': plan['hash'], 'source': data['check_source'], 'source_reviews': source_reviews,
                'execution': execution_id,
                'symbol': data['symbol'], 'expected_type': data['expected_type'], 'assumptions': data['assumptions'],
                'outcome': data['outcome'],
                'checker': 'lean4-reviewed-source', 'checker_path': binary, 'checker_hash': executable_hash,
                'toolchain': toolchain, 'toolchain_hash': toolchain_record['hash'],
                'version': version, 'libraries': libraries, 'result': result, 'axioms': axioms,
                'allowed_axioms': data['allowed_axioms'], 'environment_changed': changed_environment,
                'axiom_report_count': report_count, 'compiled_artifact': compiled_artifact,
                'artifact_collection_error': execution.get('artifact_collection_error'),
                'kernel_replay': 'same-kernel-fresh-environment' if replay else 'not-performed',
                'replay': replay, 'replay_input_hash': compiled['sha256'] if replay and compiled else None,
                'axiom_channel': 'reviewed-source stdout, not an authenticated kernel channel',
                'trust_boundary': 'Isolated execution; formal validity still trusts Lean and independently reviewed source/imports, not arbitrary hostile elaborator output',
                'author': 'root-checker-execution'})
            self.store.decide(receipt, 'checked' if accepted else 'failed',
                              {'reason': 'Actual Lean execution, exact type bridge and axiom inspection',
                               'passed': accepted})
            return receipt
