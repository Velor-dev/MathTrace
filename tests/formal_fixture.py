"""Synthetic recorder evidence for bookkeeping tests, never Lean proof evidence."""
import base64
import hashlib
import json
import sys
from pathlib import Path

from mathtrace.formal import RECEIPT_VERSION, PROFILE, REPORT_FORMAT, GRAPH_FORMAT, exact_name, blob_bytes, NAMESPACE_FIELDS
from mathtrace.store import digest


def blob(raw):
    return {'encoding': 'base64', 'content': base64.b64encode(raw).decode(),
            'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def toolchain(research, extra_files=None):
    with research.store.transaction():
        identifier = research.store.put('toolchain', {'root': str(Path(sys.executable).parent),
            'version': 'v4.30.0', 'files': {**(extra_files or {}),
                'bin/lean': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(), 'lib/lean/Init.olean': '1' * 64},
            'executable': 'bin/lean', 'manifest_hash': '0' * 64})
        research.store.decide(identifier, 'installed', {'reason': 'synthetic process-boundary fixture'})
    return identifier


def graph(symbol):
    n = exact_name
    def declaration(name, ty, values, detail):
        return {'name': n(name), 'display_name': name, 'universe_parameters': [], 'type': ty,
                'values': values, 'detail': detail, 'unsafe': False, 'partial': False, 'module': 'Main'}
    return {'format': GRAPH_FORMAT, 'complete': True, 'target': n(symbol), 'root_type': 1,
        'expressions': [['sort', ['zero']], ['const', n('True'), []], ['const', n('True.intro'), []]],
        'declarations': [
            declaration('True', 0, [], {'kind': 'inductive', 'parameters': 0, 'indices': 0,
                'mutual': [n('True')], 'constructors': [n('True.intro')], 'nested': 0,
                'recursive': False, 'reflexive': False}),
            declaration('True.intro', 1, [], {'kind': 'constructor', 'inductive': n('True'),
                'index': 0, 'parameters': 0, 'fields': 0}),
            declaration('True.rec', 0, [2], {'kind': 'recursor', 'mutual': [n('True')],
                'parameters': 0, 'indices': 0, 'motives': 1, 'minors': 1, 'k': False,
                'rules': [{'constructor': n('True.intro'), 'fields': 0}]}),
            declaration(symbol, 1, [2], {'kind': 'theorem', 'mutual': []})], 'axioms': []}


def execution(research, plan, *, primary=b'synthetic compiled object'):
    p = research.store.get(plan)['data']
    source = research.store.get(p['check_source'])['data']['text']
    compiled = blob(primary)
    file_set = {'Main.olean': {'size': compiled['size'], 'sha256': compiled['sha256']},
                'Main.olean.server': None, 'Main.olean.private': None, 'Main.ir': None}
    ref_entry = {'module': exact_name('Init'), 'base': '/toolchain/lib/lean/Init.olean',
        'parts': {'olean': '/toolchain/lib/lean/Init.olean', 'server': None, 'private': None, 'ir': None}}
    main_entry = {'module': exact_name('Main'), 'base': '/replay/Main.olean',
        'parts': {'olean': '/replay/Main.olean', 'server': None, 'private': None, 'ir': None}}
    mode = 'withImportModules; private information; loadExts=false; no plugins'
    libraries = [f'/libraries/{i}' for i in range(len(p['libraries']))]
    roots = ['/replay', *libraries, '/toolchain/lib/lean']
    resolution = {'reference_search_roots': ['/toolchain/lib/lean'], 'candidate_search_roots': roots,
        'channel': 'resolution reconstructed under immutable roots; not an open-file trace',
        'explicit_candidate_roots': ['/replay', *libraries], 'import_mode': mode,
        'reference': [ref_entry], 'candidate': [ref_entry, main_entry]}
    ref_bound = {'module': exact_name('Init'), 'parts': {'olean': {'root': '/toolchain',
        'relative': 'lib/lean/Init.olean', 'sha256': '1' * 64, 'size': 100},
        'server': None, 'private': None, 'ir': None}}
    main_bound = {'module': exact_name('Main'), 'parts': {'olean': {'root': '/replay',
        'relative': 'Main.olean', **file_set['Main.olean']}, 'server': None, 'private': None, 'ir': None}}
    resolved = {'channel': 'Lean resolution reconstructed under immutable roots and checked against staged bytes',
        'reference_search_roots': ['/toolchain/lib/lean'], 'candidate_search_roots': roots,
        'import_mode': mode, 'reference': [ref_bound], 'candidate': [ref_bound, main_bound],
        'imported_bytes_retained_in_canonical_state': False}
    semantics = graph(p['check_symbol'])
    reference = graph('referenceFixture')
    reference['declarations'].pop()
    report = {'format': REPORT_FORMAT, 'complete': True, 'verification_mode': 'checked-target',
        'primitive_profile': PROFILE, 'lean_version': '4.30.0', 'primitive_reference_count': 3,
        'primitive_imported_matches': 3, 'semantics': semantics, 'reference_profile': reference,
        'resolution': resolution}
    process = {'exit_code': 0, 'stdout': '', 'stderr': '', 'timed_out': False,
               'output_limited': False, 'namespace_setup': {k: 1 for k in NAMESPACE_FIELDS}}
    return {'result': dict(process), 'replay': dict(process), 'version': dict(process, stdout='Lean (version 4.30.0)'),
        'compiled_output': compiled, 'compiled_parts': {}, 'compiled_file_set': file_set,
        'semantic_output': blob(json.dumps(report).encode()), 'resolved_inputs': resolved,
        'verification_error': None, 'artifact_collection_error': None,
        'verification_binding': {'protocol': RECEIPT_VERSION, 'profile': PROFILE,
            'check_symbol': p['check_symbol'], 'helper_sha256': p['helper_sha256'],
            'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'compiled_file_set_hash': digest(file_set)}}


PINNED = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}


def mode_execution(research, plan, selected='direct'):
    """Synthetic mode-aware evidence, separately testing the v2 admission contract."""
    from mathtrace.formal import MODE_RECEIPT_VERSION
    result = execution(research, plan)
    result['verification_binding']['protocol'] = MODE_RECEIPT_VERSION
    if selected == 'direct':
        roots = {'platform': 'windows' if sys.platform == 'win32' else sys.platform,
                 'stage': str(Path(research.store.path.parent / 'native stage').resolve())}
        stage = Path(roots['stage'])
        roots['paths'] = {'/toolchain': str(stage/'toolchain'), '/replay': str(stage/'replay')}
        result['staged_roots'] = roots
        report = json.loads(blob_bytes(result['semantic_output']))
        def physical(path):
            if path is None:
                return None
            for role, root in roots['paths'].items():
                if path == role or path.startswith(role + '/'):
                    return str(Path(root) / path[len(role):].lstrip('/'))
            return path
        for obj in (report['resolution'], result['resolved_inputs']):
            for key in ('reference_search_roots', 'candidate_search_roots', 'explicit_candidate_roots'):
                if key in obj:
                    obj[key] = [physical(p) for p in obj[key]]
        for scope in ('reference', 'candidate'):
            for entry in report['resolution'][scope]:
                entry['base'] = physical(entry['base'])
                entry['parts'] = {k: physical(v) for k,v in entry['parts'].items()}
        report['resolution']['channel'] = 'resolution reconstructed under byte-verified staged roots; not an open-file trace'
        result['resolved_inputs']['channel'] = 'Lean resolution reconstructed under byte-verified staged roots and checked against staged bytes'
        result['semantic_output'] = blob(json.dumps(report).encode())
        for key in ('version','result','replay'):
            result[key].update(namespace_setup=None, isolation_established=False,
                execution_environment={'backend':'direct-native-v1'}, resource_limits={'address_space_bytes':'not enforced'})
    return result
