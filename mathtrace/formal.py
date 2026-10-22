"""Exact checked-semantic records and deterministic mathematical views.

This validates the evidence protocol. It is not a second theorem prover.
Only the recorder-owned pinned verifier can establish the checking observation.
"""
from __future__ import annotations

import base64
import hashlib
import json

from .store import StateError, canonical, digest

RECEIPT_VERSION = 'checked-compiled-evidence-v1'
MODE_RECEIPT_VERSION = 'checked-compiled-evidence-v2'
RECEIPT_VERSIONS = (RECEIPT_VERSION, MODE_RECEIPT_VERSION)
PROFILE = 'lean-4.30.0-reserved-primitives-v1'
REPORT_FORMAT = 'lean-checked-target-profile-v2'
GRAPH_FORMAT = 'lean-compiled-semantics-prototype-v1'
VIEW_FORMAT = 'exact-compiled-semantic-view-v1'
CAPSULE_MEDIA = 'application/vnd.mathtrace.checked-semantics+json'
VIEW_MEDIA = 'application/vnd.mathtrace.semantic-view+json'
MEANING_PROOFS = 'theorem bodies omitted from meaning view; retained in checked capsule'
SUPPLIED_PROOFS = 'theorem bodies supplied for exact investigation; proof dependencies may require additional selectors'
COMPILED_FILES = ('Main.olean', 'Main.olean.server', 'Main.olean.private', 'Main.ir')
FOUNDATIONS = ('propext', 'Classical.choice', 'Quot.sound')
NAMESPACE_FIELDS = ('child-pid', 'cgroup-namespace', 'ipc-namespace', 'mnt-namespace',
                    'net-namespace', 'pid-namespace', 'uts-namespace')


def exact_name(text: str) -> list:
    if not isinstance(text, str) or not text:
        raise StateError('An exact nonempty Lean name string is required')
    result = []
    for part in text.split('.'):
        result = ['str', result, part]
    return result


def name_key(name) -> str:
    pending, depth = name, 0
    while pending != []:
        if (not isinstance(pending, list) or len(pending) != 3
                or pending[0] not in {'str', 'num'}):
            raise StateError('Malformed exact Lean name')
        if pending[0] == 'str' and not isinstance(pending[2], str):
            raise StateError('Malformed exact Lean string name')
        if pending[0] == 'num' and (type(pending[2]) is not int or pending[2] < 0):
            raise StateError('Malformed exact Lean numeric name')
        pending = pending[1]
        depth += 1
        if depth > 256:
            raise StateError('Exact name exceeds the supported serialization depth')
    try:
        return canonical(name)
    except RecursionError as error:
        raise StateError('Exact name exceeds the serialization budget') from error


def blob_bytes(blob, *, limit=16 * 1024 * 1024) -> bytes:
    if not isinstance(blob, dict) or blob.get('encoding') != 'base64' or not isinstance(blob.get('content'), str):
        raise StateError('Missing retained artifact bytes')
    try:
        raw = base64.b64decode(blob['content'], validate=True)
    except (ValueError, TypeError) as error:
        raise StateError('Invalid retained artifact encoding') from error
    if (len(raw) > limit or type(blob.get('size')) is not int or blob['size'] != len(raw)
            or hashlib.sha256(raw).hexdigest() != blob.get('sha256')):
        raise StateError('Retained artifact bytes do not match their size/hash')
    return raw


def compiled_bundle(execution: dict) -> tuple[dict, dict]:
    supplemental = execution.get('compiled_parts')
    if not isinstance(supplemental, dict) or set(supplemental) - set(COMPILED_FILES[1:]):
        raise StateError('Unknown or malformed compiled object parts')
    blobs = {'Main.olean': execution.get('compiled_output'), **supplemental}
    if blobs['Main.olean'] is None:
        raise StateError('Compiled exported object is absent')
    manifest = {name: None for name in COMPILED_FILES}
    for name, blob in blobs.items():
        raw = blob_bytes(blob)
        manifest[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
    if sum(item['size'] for item in manifest.values() if item) > 64 * 1024 * 1024:
        raise StateError('Compiled bundle exceeds its aggregate retention limit')
    if execution.get('compiled_file_set') != manifest:
        raise StateError('Compiled object presence/absence manifest does not match retained bytes')
    return blobs, manifest


def process_passed(value, execution_mode='bubblewrap') -> bool:
    if execution_mode == 'direct':
        return (isinstance(value, dict) and type(value.get('exit_code')) is int
                and value['exit_code'] == 0 and value.get('timed_out') is False
                and value.get('output_limited') is False and value.get('namespace_setup') is None
                and value.get('isolation_established') is False
                and value.get('execution_environment', {}).get('backend') == 'direct-native-v1')
    namespace = value.get('namespace_setup') if isinstance(value, dict) else None
    return (isinstance(value, dict) and type(value.get('exit_code')) is int
            and value['exit_code'] == 0 and value.get('timed_out') is False
            and value.get('output_limited') is False and isinstance(namespace, dict)
            and all(type(namespace.get(k)) is int and namespace[k] > 0 for k in NAMESPACE_FIELDS))


def validate_resolution(report_resolution, resolved, toolchain, libraries, file_set, *, roots=None):
    """Validate retained resolution against committed manifests, without live files.

    Sizes of imported files were observed by the recorder. Their manifests bind
    hashes, not sizes. Retained Main files additionally bind observed sizes.
    """
    if roots is not None:
        from .resolution import normalized_resolution
        report_resolution, resolved = normalized_resolution(report_resolution, resolved, roots, len(libraries))
    from pathlib import PurePosixPath
    library_roots = [f'/libraries/{i}' for i in range(len(libraries))]
    # Keep the exact staging convention shared with the recorder.
    expected_roots = ['/replay', *library_roots, '/toolchain/lib/lean']
    if (not isinstance(report_resolution, dict) or not isinstance(resolved, dict)
            or report_resolution.get('reference_search_roots') != ['/toolchain/lib/lean']
            or report_resolution.get('candidate_search_roots') != expected_roots
            or report_resolution.get('explicit_candidate_roots') != ['/replay', *library_roots]
            or report_resolution.get('channel') != 'resolution reconstructed under immutable roots; not an open-file trace'
            or resolved.get('reference_search_roots') != ['/toolchain/lib/lean']
            or resolved.get('candidate_search_roots') != expected_roots
            or resolved.get('import_mode') != report_resolution.get('import_mode')
            or resolved.get('import_mode') != 'withImportModules; private information; loadExts=false; no plugins'
            or resolved.get('channel') != 'Lean resolution reconstructed under immutable roots and checked against staged bytes'
            or resolved.get('imported_bytes_retained_in_canonical_state') is not False):
        raise StateError('Retained resolution does not bind the exact checking input order/mode')
    manifests = {'/toolchain': toolchain['files'],
        '/replay': {name: value['sha256'] for name, value in file_set.items() if value}}
    manifests.update({root: lib['files'] for root, lib in zip(library_roots, libraries)})

    def part(path, binding, reference):
        if path is None:
            if binding is not None:
                raise StateError('Absent resolved part has a byte binding')
            return
        if not isinstance(path, str) or not isinstance(binding, dict):
            raise StateError('Missing exact resolved module part binding')
        parsed = PurePosixPath(path)
        if not parsed.is_absolute() or '..' in parsed.parts or parsed.as_posix() != path or '\\' in path:
            raise StateError('Unbound resolved path')
        root = binding.get('root')
        relative = binding.get('relative')
        if (root not in manifests or not isinstance(relative, str) or path != root + '/' + relative
                or reference and root != '/toolchain'
                or manifests[root].get(relative) != binding.get('sha256')
                or type(binding.get('size')) is not int or binding['size'] < 0
                or set(binding) != {'root', 'relative', 'sha256', 'size'}):
            raise StateError('Resolved module part differs from its committed byte manifest')
        if root == '/replay' and file_set.get(relative) != {'sha256': binding['sha256'], 'size': binding['size']}:
            raise StateError('Resolved target part differs from its retained bytes')

    main_present = False
    for scope in ('reference', 'candidate'):
        reported, bound = report_resolution.get(scope), resolved.get(scope)
        if not isinstance(reported, list) or not reported or not isinstance(bound, list) or len(reported) != len(bound):
            raise StateError('Incomplete resolved module manifest')
        seen = set()
        for entry, actual in zip(reported, bound):
            if not isinstance(entry, dict) or not isinstance(actual, dict):
                raise StateError('Malformed resolved module')
            key = name_key(entry.get('module'))
            if key in seen or actual.get('module') != entry['module']:
                raise StateError('Duplicate or mismatched resolved module identity')
            seen.add(key)
            paths, parts = entry.get('parts'), actual.get('parts')
            base = entry.get('base')
            if (not isinstance(base, str) or not base.endswith('.olean')
                    or not isinstance(paths, dict) or not isinstance(parts, dict)
                    or set(paths) != {'olean', 'server', 'private', 'ir'} or set(parts) != set(paths)
                    or paths['olean'] != base):
                raise StateError('Malformed resolved module parts')
            prefix = next((root for root in manifests if base.startswith(root + '/')), None)
            if prefix is None:
                raise StateError('Resolved module is outside committed input roots')
            relative = base[len(prefix) + 1:]
            files = manifests[prefix]
            expected = {'olean': base, 'server': base + '.server' if relative + '.server' in files else None,
                'ir': base[:-6] + '.ir' if relative[:-6] + '.ir' in files else None}
            expected['private'] = base + '.private' if expected['server'] and relative + '.private' in files else None
            if paths != expected:
                raise StateError('Resolved presence/absence differs from the committed input family')
            for kind, path in paths.items():
                part(path, parts[kind], scope == 'reference')
            main_present |= scope == 'candidate' and base == '/replay/Main.olean'
    if not main_present:
        raise StateError('Resolved target object is absent')


def receipt_evidence(store, identifier):
    """Reconstruct exact modern evidence; dispositions are checked by Research.

    This reads the immutable terminal event directly and never follows output
    artifacts from the execution scope, avoiding a causal dependency cycle.
    """
    record = store.get(identifier, 'formal_receipt')
    data = record['data']
    if data.get('receipt_version') not in RECEIPT_VERSIONS or data.get('checking_profile') != PROFILE:
        raise StateError('Legacy formal evidence requires a new modern plan/check, binding and audit')
    plan = store.get(data['plan'], 'formal_plan')
    p = plan['data']
    if p.get('receipt_version') not in RECEIPT_VERSIONS:
        raise StateError('Legacy plan cannot qualify modern checking evidence')
    protocol = data['receipt_version']
    if protocol == RECEIPT_VERSION and p['receipt_version'] != RECEIPT_VERSION:
        raise StateError('Historical receipt differs from its original plan protocol')
    selected = data.get('execution_mode', 'bubblewrap')
    if selected not in ('direct', 'bubblewrap') or (protocol == RECEIPT_VERSION and selected != 'bubblewrap'):
        raise StateError('Invalid execution mode for receipt protocol')
    source = store.get(p['check_source'], 'artifact')
    helper = store.get(p['helper_artifact'], 'artifact')
    toolchain = store.get(data['toolchain'], 'toolchain')
    attempt = store.get(data['execution'], 'execution')
    a, metadata = attempt['data'], attempt['data']['metadata']
    contract = store.get(store.get(p['target'], 'claim')['data']['contract'], 'contract')['data']
    if (set(p['allowed_axioms']) - set(contract['allowed_axioms'])
            or data.get('checker_hash') != toolchain['data']['files'].get(toolchain['data']['executable'])):
        raise StateError('Checking binary or narrowed foundation policy differs from the pinned records')
    if (data.get('plan_hash') != plan['hash'] or data.get('toolchain_hash') != toolchain['hash']
            or toolchain['data'].get('version') != 'v4.30.0'
            or data.get('source') != source['id'] or data.get('source_reviews') != a['source_reviews']
            or any(data.get(k) != p.get(k) for k in ('checking_profile', 'target',
                'symbol', 'check_symbol', 'expected_type', 'assumptions', 'outcome', 'allowed_axioms', 'libraries',
                'helper_artifact', 'helper_sha256'))
            or data.get('helper_hash') != helper['hash']
            or hashlib.sha256(helper['data']['text'].encode()).hexdigest() != p['helper_sha256']
            or a['plan'] != plan['id'] or a['plan_hash'] != plan['hash']
            or a['operation'] != 'formal' or a['source'] != source['id'] or a['source_hash'] != source['hash']
            or a['target_hash'] != store.get(p['target'], 'claim')['hash']
            or any(metadata.get(k) != data.get(k) for k in ('receipt_version', 'checking_profile',
                'helper_artifact', 'helper_hash', 'helper_sha256', 'check_symbol', 'toolchain', 'toolchain_hash',
                'checker_path', 'checker_hash'))):
        raise StateError('Formal receipt does not bind its exact plan/helper/source/execution/toolchain')
    verification = {'protocol': protocol, 'profile': PROFILE,
                    'check_symbol': p['check_symbol'], 'helper_source': helper['data']['text']}
    request = {'operation': 'formal', 'source': source['data']['text'], 'toolchain': toolchain['data'],
               'libraries': p['libraries'], 'timeout': a['timeout'], 'verification': verification}
    if protocol == MODE_RECEIPT_VERSION:
        from .backend import EXECUTION_PROTOCOL
        request.update(execution_mode=selected, execution_protocol=EXECUTION_PROTOCOL)
        if metadata.get('execution_mode') != selected:
            raise StateError('Mode differs from committed attempt')
    if digest(request) != a['request_hash']:
        raise StateError('Formal execution request does not match the pinned inputs')
    row = store.db.execute("SELECT payload FROM events WHERE type='execution-terminal' AND target=? "
                           'ORDER BY seq DESC LIMIT 1', (attempt['id'],)).fetchone()
    if not row:
        raise StateError('Formal execution has no terminal observation')
    terminal = json.loads(row['payload'])
    observation = store.get(terminal['observation'], 'artifact')
    envelope = json.loads(observation['data']['text'])
    producer = envelope.get('producer')
    if (terminal.get('receipt') != identifier or digest(envelope) != terminal.get('observation_hash')
            or observation['data'].get('content_hash') != digest(envelope) or envelope.get('ok') is not True
            or envelope.get('execution') != attempt['id'] or envelope.get('request_hash') != a['request_hash']
            or envelope.get('teardown') != 'recorder-owned-processes-waited'
            or not isinstance(producer, dict) or producer.get('execution') != attempt['id']
            or producer.get('request_hash') != a['request_hash'] or digest(producer) != envelope.get('producer_hash')):
        raise StateError('Terminal observation does not attribute this exact receipt/execution')
    observed = envelope['result']
    if protocol == MODE_RECEIPT_VERSION:
        from .execution import validate_mode_observation
        validate_mode_observation(a, envelope)
        if data.get('execution_assurance') != execution_assurance(observed, selected):
            raise StateError('Receipt environment assurance differs from observation')
    if (digest(observed) != data.get('observation_result_hash') or data.get('failures') != []
            or data.get('kernel_replay') != 'same-kernel-pinned-primitive-target'
            or any(data.get(k) != observed.get(k) for k in ('result', 'replay', 'version', 'verification_binding'))
            or not all(process_passed(observed.get(k), selected) for k in ('result', 'replay', 'version'))
            or observed.get('verification_error') is not None or observed.get('artifact_collection_error') is not None):
        raise StateError('Formal receipt differs from the successful terminal checking observation')
    blobs, file_set = compiled_bundle(observed)
    expected_binding = {'protocol': protocol, 'profile': PROFILE, 'check_symbol': p['check_symbol'],
        'helper_sha256': p['helper_sha256'], 'source_sha256': hashlib.sha256(source['data']['text'].encode()).hexdigest(),
        'compiled_file_set_hash': digest(file_set)}
    if (data.get('verification_binding') != expected_binding or data.get('compiled_file_set') != file_set
            or data.get('replay_input_hash') != file_set['Main.olean']['sha256']
            or not isinstance(data.get('compiled_parts'), dict) or set(data['compiled_parts']) != set(blobs)
            or data.get('compiled_artifact') != data['compiled_parts']['Main.olean']):
        raise StateError('Receipt does not bind the exact compiled file family')
    records = {r['id']: r['hash'] for r in (plan, source, helper, toolchain, attempt)}
    for name, blob in blobs.items():
        artifact = store.get(data['compiled_parts'][name], 'artifact')
        d = artifact['data']
        if (d.get('filename') != name or d.get('source_execution') != attempt['id']
                or blob_bytes({**d, 'content': d['text']}) != blob_bytes(blob)
                or d.get('content_hash') != digest(d['text'])):
            raise StateError('Retained compiled part does not match the terminal bytes')
        records[artifact['id']] = artifact['hash']
    raw = blob_bytes(observed.get('semantic_output'), limit=64 * 1024 * 1024)
    semantic = store.get(data['semantic_artifact'], 'artifact')
    if (semantic['data'].get('media_type') != CAPSULE_MEDIA or semantic['data']['text'].encode() != raw
            or semantic['data'].get('source_execution') != attempt['id']
            or semantic['data'].get('sha256') != hashlib.sha256(raw).hexdigest()):
        raise StateError('Retained semantic capsule differs from the terminal bytes')
    report = json.loads(raw)
    validate_report(report, p['check_symbol'], p['allowed_axioms'])
    if data.get('axioms') != report['semantics']['axioms']:
        raise StateError('Receipt axiom closure differs from the checked capsule')
    for field, expected in (('reference_artifact', report['reference_profile']),
                            ('resolution_artifact', observed.get('resolved_inputs'))):
        artifact = store.get(data[field], 'artifact')
        if json.loads(artifact['data']['text']) != expected or artifact['data'].get('source_execution') != attempt['id']:
            raise StateError('Retained reference/resolution differs from its checking observation')
        records[artifact['id']] = artifact['hash']
    validate_resolution(report.get('resolution'), observed.get('resolved_inputs'),
                        toolchain['data'], p['libraries'], file_set,
                        roots=observed.get('staged_roots') if selected == 'direct' else None)
    records[semantic['id']] = semantic['hash']
    manifest = {'records': records, 'compiled_file_set': file_set, 'execution_request_hash': a['request_hash'],
                'protocol': protocol, 'checking_profile': PROFILE}
    if data.get('evidence_manifest') != manifest or data.get('evidence_manifest_hash') != digest(manifest):
        raise StateError('Formal evidence manifest is incomplete or inconsistent')
    return {'records': {**records, observation['id']: observation['hash'], identifier: record['hash'],
                        p['source']: store.get(p['source'], 'artifact')['hash']},
            'report': report, 'observation': observation['id']}


class SemanticGraph:
    def __init__(self, data):
        if (not isinstance(data, dict) or data.get('format') != GRAPH_FORMAT
                or data.get('complete') is not True
                or not isinstance(data.get('expressions'), list)
                or not isinstance(data.get('declarations'), list)):
            raise StateError('Incomplete or unsupported exact semantic graph')
        self.data, self.expressions, self.declarations = data, data['expressions'], {}
        if len(self.expressions) > 500000 or len(data['declarations']) > 50000:
            raise StateError('Semantic graph exceeds its declared protocol budget')
        self.children, self.references, self.node_hashes = [], [], []
        for index, node in enumerate(self.expressions):
            children, references = self._expression(node)
            if any(type(i) is not int or not 0 <= i < index for i in children):
                raise StateError('Expression graph is not a complete ordered DAG')
            self.children.append(children)
            self.references.append(references)
            normalized = list(node)
            for position in self._child_positions(node):
                normalized[position] = self.node_hashes[node[position]]
            self.node_hashes.append(digest(normalized))
        for declaration in data['declarations']:
            if not isinstance(declaration, dict):
                raise StateError('Malformed exact declaration')
            key = name_key(declaration.get('name'))
            if key in {name_key(exact_name(n)) for n in ['Lean.reduceBool', 'Lean.reduceNat']}:
                raise StateError('Native reduction is outside this checking profile')
            if key in self.declarations:
                raise StateError('Duplicate semantic declaration identity')
            self._declaration(declaration)
            self.declarations[key] = declaration
        actual_axioms = {k for k, d in self.declarations.items() if d['detail']['kind'] == 'axiom'}
        if not isinstance(data.get('axioms'), list):
            raise StateError('Missing exact axiom closure')
        self.axioms = [name_key(n) for n in data['axioms']]
        if len(set(self.axioms)) != len(self.axioms) or set(self.axioms) != actual_axioms:
            raise StateError('Axiom closure does not match actual declarations')
        # Every exported semantic reference must have its own exact record.
        for declaration in self.declarations.values():
            if self.dependencies(declaration, proofs=True) - self.declarations.keys():
                raise StateError('Semantic declaration closure has missing dependencies')
        self._relationships()

    def _relationships(self):
        for key, declaration in self.declarations.items():
            detail, kind = declaration['detail'], declaration['detail']['kind']
            if kind == 'inductive':
                group = [name_key(n) for n in detail['mutual']]
                if key not in group:
                    raise StateError('Inductive is absent from its own mutual group')
                for member in group:
                    other = self.declarations[member]['detail']
                    if other['kind'] != 'inductive' or other['mutual'] != detail['mutual']:
                        raise StateError('Inductive mutual groups are not reciprocal')
                for index, name in enumerate(detail['constructors']):
                    constructor = self.declarations[name_key(name)]['detail']
                    if (constructor['kind'] != 'constructor' or name_key(constructor['inductive']) != key
                            or constructor['index'] != index or constructor['parameters'] != detail['parameters']):
                        raise StateError('Inductive constructor relationship is inconsistent')
            elif kind == 'constructor':
                parent = self.declarations[name_key(detail['inductive'])]['detail']
                if parent['kind'] != 'inductive' or declaration['name'] not in parent['constructors']:
                    raise StateError('Constructor is absent from its parent inductive')
            elif kind == 'recursor':
                group = {name_key(n) for n in detail['mutual']}
                if not group or any(self.declarations[n]['detail']['kind'] != 'inductive' for n in group):
                    raise StateError('Recursor has no valid inductive group')
                for rule in detail['rules']:
                    constructor = self.declarations[name_key(rule['constructor'])]['detail']
                    if constructor['kind'] != 'constructor':
                        raise StateError('Recursor rule does not reference a retained constructor')
                    # Restored auxiliary recursors may eliminate external
                    # containers. Kernel reconstruction/correspondence checks
                    # rule validity; this reader does not invent extra arity or
                    # parent-membership constraints for those generated records.

    @staticmethod
    def _level(level):
        pending = [level]
        while pending:
            value = pending.pop()
            if not isinstance(value, list) or not value:
                raise StateError('Malformed universe level')
            tag = value[0]
            if tag == 'zero' and len(value) == 1:
                continue
            if tag == 'succ' and len(value) == 2:
                pending.append(value[1])
            elif tag in {'max', 'imax'} and len(value) == 3:
                pending.extend(value[1:])
            elif tag == 'param' and len(value) == 2:
                name_key(value[1])
            else:
                raise StateError('Unsupported or unclosed universe level')

    @staticmethod
    def _child_positions(node):
        return {'app': (1, 2), 'lam': (2, 3), 'forall': (2, 3),
                'let': (2, 3, 4), 'proj': (3,)}.get(node[0], ())

    def _expression(self, node):
        if not isinstance(node, list) or not node or not isinstance(node[0], str):
            raise StateError('Malformed exact expression')
        tag, refs = node[0], set()
        arities = {'bvar': 2, 'sort': 2, 'const': 3, 'app': 3, 'lam': 5,
                   'forall': 5, 'let': 6, 'nat': 2, 'string': 2, 'proj': 4}
        if tag not in arities or len(node) != arities[tag]:
            raise StateError('Unsupported expression kind or shape')
        if tag in {'bvar', 'nat'} and (type(node[1]) is not int or node[1] < 0):
            raise StateError('Malformed natural expression value')
        if tag == 'string' and not isinstance(node[1], str):
            raise StateError('Malformed string literal')
        if tag == 'sort':
            self._level(node[1])
        if tag == 'const':
            refs.add(name_key(node[1]))
            if not isinstance(node[2], list):
                raise StateError('Malformed universe arguments')
            for level in node[2]:
                self._level(level)
        if tag in {'lam', 'forall', 'let'}:
            name_key(node[1])
        if tag in {'lam', 'forall'} and node[4] not in {'default', 'implicit', 'strictImplicit', 'instImplicit'}:
            raise StateError('Unknown binder annotation')
        if tag == 'let' and type(node[5]) is not bool:
            raise StateError('Malformed let annotation')
        if tag == 'proj':
            refs.add(name_key(node[1]))
            if type(node[2]) is not int or node[2] < 0:
                raise StateError('Malformed projection index')
        if tag in {'nat', 'string'}:
            implicit = ['Nat', 'Nat.zero', 'Nat.succ']
            if tag == 'string':
                implicit += ['String', 'String.ofList', 'Char', 'Char.ofNat', 'List', 'List.nil', 'List.cons']
            refs.update(name_key(exact_name(n)) for n in implicit)
        return [node[p] for p in self._child_positions(node)], refs

    def _declaration(self, declaration):
        if set(declaration) != {'name', 'display_name', 'universe_parameters', 'type', 'values',
                                'detail', 'unsafe', 'partial', 'module'}:
            raise StateError('Unknown or missing declaration fields')
        if not isinstance(declaration['display_name'], str) or not (declaration['module'] is None or isinstance(declaration['module'], str)):
            raise StateError('Malformed declaration presentation/provenance')
        parameters = declaration.get('universe_parameters')
        if not isinstance(parameters, list) or len({name_key(n) for n in parameters}) != len(parameters):
            raise StateError('Malformed universe parameter identities')
        if declaration.get('unsafe') is not False or declaration.get('partial') is not False:
            raise StateError('Unsafe or partial semantic declaration')
        values = declaration.get('values')
        if not isinstance(values, list):
            raise StateError('Missing declaration values')
        for identifier in [declaration.get('type'), *values]:
            if type(identifier) is not int or not 0 <= identifier < len(self.expressions):
                raise StateError('Missing declaration expression')
        detail = declaration.get('detail')
        if not isinstance(detail, dict) or detail.get('kind') not in {
                'axiom', 'definition', 'theorem', 'opaque', 'inductive', 'constructor', 'recursor', 'quotient'}:
            raise StateError('Unknown exact declaration kind')
        kind = detail['kind']
        fields = {'axiom': set(), 'definition': {'safety', 'hints', 'mutual'},
            'theorem': {'mutual'}, 'opaque': {'mutual'},
            'inductive': {'parameters', 'indices', 'mutual', 'constructors', 'nested', 'recursive', 'reflexive'},
            'constructor': {'inductive', 'index', 'parameters', 'fields'},
            'recursor': {'mutual', 'parameters', 'indices', 'motives', 'minors', 'k', 'rules'},
            'quotient': {'quotient_kind'}}
        if set(detail) != fields[kind] | {'kind'}:
            raise StateError('Unknown or missing declaration semantic fields')
        for field in {'parameters', 'indices', 'nested', 'index', 'fields', 'motives', 'minors'} & detail.keys():
            if type(detail[field]) is not int or detail[field] < 0:
                raise StateError('Malformed declaration arity/count')
        for field in {'recursive', 'reflexive', 'k'} & detail.keys():
            if type(detail[field]) is not bool:
                raise StateError('Malformed inductive/recursor flag')
        for field in {'mutual', 'constructors'} & detail.keys():
            if not isinstance(detail[field], list) or len({name_key(n) for n in detail[field]}) != len(detail[field]):
                raise StateError('Malformed exact declaration name group')
        if kind == 'constructor':
            name_key(detail['inductive'])
        if kind == 'quotient' and detail['quotient_kind'] not in {'type', 'constructor', 'lift', 'induction'}:
            raise StateError('Unknown quotient primitive kind')
        if kind == 'definition':
            hints = detail['hints']
            if (detail['safety'] != 'Lean.DefinitionSafety.safe' or not isinstance(hints, list)
                    or not (hints in [['opaque'], ['abbrev']] or len(hints) == 2
                            and hints[0] == 'regular' and type(hints[1]) is int and 0 <= hints[1] < 2**32)):
                raise StateError('Unsupported definition safety/reduction hints')
        if kind in {'definition', 'theorem', 'opaque'} and len(values) != 1:
            raise StateError('Declaration body is absent or duplicated')
        if kind in {'axiom', 'inductive', 'constructor', 'quotient'} and values:
            raise StateError('Unexpected declaration body')
        if kind == 'recursor' and (not isinstance(detail.get('rules'), list) or len(values) != len(detail['rules'])):
            raise StateError('Recursor rule bodies are incomplete')
        if kind == 'recursor':
            for rule in detail['rules']:
                if (not isinstance(rule, dict) or set(rule) != {'constructor', 'fields'}
                        or type(rule['fields']) is not int or rule['fields'] < 0):
                    raise StateError('Malformed exact recursor rule')
                name_key(rule['constructor'])

    def expression_ids(self, initial):
        pending, seen = list(initial), set()
        while pending:
            identifier = pending.pop()
            if type(identifier) is not int or not 0 <= identifier < len(self.expressions):
                raise StateError('Requested expression is absent')
            if identifier not in seen:
                seen.add(identifier)
                pending.extend(self.children[identifier])
        return seen

    def dependencies(self, declaration, *, proofs):
        initial = [declaration['type']]
        if proofs or declaration['detail']['kind'] != 'theorem':
            initial += declaration['values']
        used = set().union(*(self.references[i] for i in self.expression_ids(initial)))
        detail, kind = declaration['detail'], declaration['detail']['kind']
        related = detail.get('mutual', [])
        if kind == 'inductive':
            related = related + detail.get('constructors', []) + [['str', n, 'rec'] for n in related]
        elif kind == 'constructor':
            related = [detail.get('inductive')]
        elif kind == 'recursor':
            related = related + [r.get('constructor') for r in detail['rules']]
        elif kind == 'quotient':
            related = [exact_name(n) for n in ['Eq', 'Quot', 'Quot.mk', 'Quot.lift', 'Quot.ind']]
        return used | {name_key(n) for n in related}

    def signature(self, key):
        declaration = self.declarations[key]
        result = {k: v for k, v in declaration.items() if k not in {'display_name', 'module'}}
        result['type'] = self.node_hashes[result['type']]
        result['values'] = [self.node_hashes[i] for i in result['values']]
        return digest(result)

    def statement_keys(self):
        target = name_key(self.data.get('target'))
        if target not in self.declarations or self.declarations[target]['detail']['kind'] != 'theorem':
            raise StateError('Exact checked target is not a theorem')
        if type(self.data.get('root_type')) is not int or self.data['root_type'] != self.declarations[target]['type']:
            raise StateError('Root type does not match the exact theorem')
        return self.meaning_keys([target])

    def foundation_keys(self):
        return self.meaning_keys(self.axioms)

    def meaning_keys(self, initial):
        pending, seen = list(initial), set()
        while pending:
            key = pending.pop()
            if key not in seen:
                if key not in self.declarations:
                    raise StateError('Statement meaning closure is incomplete')
                seen.add(key)
                pending.extend(self.dependencies(self.declarations[key], proofs=False))
        return seen


def validate_report(report, symbol: str, allowed_axioms: list[str]):
    expected_name = exact_name(symbol)
    if (not isinstance(allowed_axioms, list) or any(not isinstance(n, str) for n in allowed_axioms)
            or len(set(allowed_axioms)) != len(allowed_axioms)):
        raise StateError('Permitted foundations must be exact distinct names')
    if (not isinstance(report, dict) or report.get('format') != REPORT_FORMAT
            or report.get('verification_mode') != 'checked-target' or report.get('complete') is not True
            or report.get('primitive_profile') != PROFILE or report.get('lean_version') != '4.30.0'):
        raise StateError('Required supported checked-target verification report is absent')
    graph, reference = SemanticGraph(report.get('semantics')), SemanticGraph(report.get('reference_profile'))
    count, matches = report.get('primitive_reference_count'), report.get('primitive_imported_matches')
    if (type(count) is not int or count != len(reference.declarations) or type(matches) is not int
            or not 0 <= matches <= count):
        raise StateError('Primitive profile counts are inconsistent')
    if graph.data.get('target') != expected_name:
        raise StateError('Checked semantic report addresses a different exact theorem')
    graph.statement_keys()
    if set(allowed_axioms) - set(FOUNDATIONS):
        raise StateError('This profile does not admit custom axiom names without exact schemas')
    allowed = {name_key(exact_name(n)) for n in allowed_axioms}
    if set(graph.axioms) - allowed:
        raise StateError('Actual checked axiom closure exceeds the permitted foundation')
    for key in graph.axioms:
        if key not in reference.declarations or graph.signature(key) != reference.signature(key):
            raise StateError('Actual axiom schema differs from the pinned reference')
    return graph, reference


def semantic_view(report, *, selectors=None, max_chars=32000, include_theorem_proofs=False):
    """Exact complete declaration units; every omitted unit remains explicit."""
    graph = SemanticGraph(report['semantics'])
    if type(include_theorem_proofs) is not bool:
        raise StateError('Theorem-proof exposure must be an exact boolean')
    statement, foundation = graph.statement_keys(), graph.foundation_keys()
    required = statement | foundation
    target = name_key(graph.data['target'])
    if selectors is None:
        ordered = [target, *sorted(foundation - {target}), *sorted(required - foundation - {target})]
    else:
        if not isinstance(selectors, list) or any(not isinstance(k, str) or k not in graph.declarations for k in selectors):
            raise StateError('Semantic selectors must name exact declarations of this capsule')
        if len(set(selectors)) != len(selectors):
            raise StateError('Semantic selectors must be distinct')
        ordered = selectors
    if max_chars is not None and (type(max_chars) is not int or max_chars < 1000):
        raise StateError('Specify a semantic context budget of at least 1000 characters')
    declarations, expressions, included = {}, {}, set()
    report_hash, owner_hash = digest(report), digest(graph.data)
    statement_hash, foundation_hash = digest(sorted(statement)), digest(sorted(foundation))

    def render(decls, nodes, exposed):
        missing = sorted(required - exposed)
        result = {'format': VIEW_FORMAT, 'target': graph.data['target'], 'root_type': graph.data['root_type'],
            'report_digest': report_hash, 'expression_owner_digest': owner_hash,
            'declarations': decls, 'expressions': nodes,
            'statement_required_hash': statement_hash, 'foundation_required_hash': foundation_hash,
            'statement_complete': statement.issubset(exposed), 'foundations_complete': foundation.issubset(exposed),
            'missing_count': len(missing), 'missing_selectors': missing[:128],
            'missing_selectors_omitted': max(0, len(missing) - 128),
            'proof_body_policy': SUPPLIED_PROOFS if include_theorem_proofs else MEANING_PROOFS,
            'checking_profile': report.get('primitive_profile'),
            'checking_restrictions': 'safe, nonpartial declarations; native reduceBool/reduceNat excluded; reserved primitive compatibility checked',
            'authority': 'Exact supplied mathematics; not a fidelity verdict'}
        while max_chars is not None and result['missing_selectors'] and len(canonical(result)) > max_chars:
            result['missing_selectors'].pop()
            result['missing_selectors_omitted'] += 1
        if max_chars is not None and len(canonical(result)) > max_chars:
            raise StateError('Semantic context budget cannot hold its exact header')
        return result

    render(declarations, expressions, included)
    for key in ordered:
        entry = dict(graph.declarations[key])
        if entry['detail']['kind'] == 'theorem' and not include_theorem_proofs:
            entry['values'] = []
            entry['proof_body_omitted'] = True
        nodes = graph.expression_ids([entry['type'], *entry['values']])
        new_nodes = {str(i): graph.expressions[i] for i in sorted(nodes) if str(i) not in expressions}
        next_declarations, next_expressions = {**declarations, key: entry}, {**expressions, **new_nodes}
        try:
            render(next_declarations, next_expressions, included | {key})
        except StateError:
            continue
        included.add(key)
        declarations, expressions = next_declarations, next_expressions
    return render(declarations, expressions, included)


def validate_view(report, view):
    if not isinstance(view, dict) or not isinstance(view.get('declarations'), dict):
        raise StateError('Malformed semantic view')
    expected = semantic_view(report, selectors=list(view['declarations']), max_chars=None,
                             include_theorem_proofs=view.get('proof_body_policy') == SUPPLIED_PROOFS)
    # A bounded view may abbreviate the selector index, but cannot change any
    # mathematics, owner identity, coverage fact or actual omitted count.
    for key in ('missing_selectors', 'missing_selectors_omitted'):
        expected[key] = view.get(key)
    graph = SemanticGraph(report['semantics'])
    missing = sorted((graph.statement_keys() | graph.foundation_keys()) - view['declarations'].keys())
    index = view.get('missing_selectors')
    if (not isinstance(index, list) or index != missing[:len(index)]
            or view.get('missing_selectors_omitted') != len(missing) - len(index)
            or view != expected):
        raise StateError('Semantic view is not the exact slice of this capsule')
    return set(view['declarations'])


def execution_assurance(observed, selected):
    processes = {k: observed.get(k) for k in ('version', 'result', 'replay')}
    isolated = selected == 'bubblewrap' and all(
        isinstance(v, dict) and isinstance(v.get('namespace_setup'), dict)
        and all(type(v['namespace_setup'].get(k)) is int and v['namespace_setup'][k] > 0
                for k in NAMESPACE_FIELDS) for v in processes.values())
    return {'execution_mode': selected, 'isolation_established': isolated,
        'process_environments': {k: (v.get('execution_environment') if isinstance(v, dict) else None)
                                 for k, v in processes.items()},
        'process_limits': {k: (v.get('resource_limits') if isinstance(v, dict) else None)
                          for k, v in processes.items()},
        'trust_boundary': ('reviewed code and trusted local host account; no sandbox isolation'
                           if selected == 'direct' else 'existing Linux Bubblewrap isolation')}
