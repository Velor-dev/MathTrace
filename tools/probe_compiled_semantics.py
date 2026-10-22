"""Unmocked prototype probe, outside canonical mathematical acceptance.

The Windows driver invokes this same file in WSL. All Lean code runs through
the existing isolated runner; the trusted helper elaborates without extra roots.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def guest(request):
    from mathtrace.sandbox_runtime import run, stage_tree
    observed = {'helper_sha256': hashlib.sha256(request['helper'].encode()).hexdigest(),
                'purpose': 'compiled semantic channel prototype; not canonical proof acceptance', 'cases': {}}
    with tempfile.TemporaryDirectory(prefix='mathtrace-semantic-probe-') as directory:
        stage = Path(directory)
        toolchain = stage_tree(request['toolchain'], stage / 'toolchain')
        mounts = [(toolchain, '/toolchain', True)]
        trusted_env = {'LEAN_SYSROOT': '/toolchain', 'LEAN_PATH': '', 'LEAN_NUM_THREADS': '2'}

        def execute(source, command, more_mounts=(), *, retain=False, environment=None, cwd='/inputs', retained_kind='compiled'):
            return run({'source': source, 'timeout': 180}, mounts=[*mounts, *more_mounts],
                guest_command=command, extra_environment=environment or trusted_env,
                address_space_bytes=8 * 1024**3, working_directory=cwd, retain_output=retain, retained_kind=retained_kind)

        observed['helper_compile'] = execute(request['helper'], ['/toolchain/bin/lean', '-j2', '/inputs/Main.lean'])
        if observed['helper_compile']['exit_code'] or observed['helper_compile']['timed_out']:
            return observed
        observed['comparison_selftest'] = execute(request['helper'],
            ['/toolchain/bin/lean', '-j2', '--run', '/inputs/Main.lean', '--self-test'])
        if request.get('comparison_only'):
            return observed

        reuse_cases = request.get('reuse_cases', {})
        fixtures = {'true': 'theorem original : True := True.intro\ntheorem exactReceipt : True := original\n',
            'actual-library-source-disagreement': 'import Foo\ntheorem original : ActualProblem := True.intro\ntheorem exactReceipt : ActualProblem := original\n',
            'shadowed-foundation-name': 'prelude\ninductive False : Prop\naxiom Classical.choice : False\ntheorem exactReceipt : False := Classical.choice\n',
            'projection-literal-recursion': 'structure PairFixture where\n  n : Nat\n  s : String\ndef datum : PairFixture := ⟨3, "x"⟩\ndef twist : Nat → Nat\n  | 0 => 0\n  | Nat.succ n => Nat.succ (twist n)\ntheorem exactReceipt : twist datum.n = 3 := rfl\n'}
        fixtures['module-private-bridge'] = 'module\npublic theorem original : True := True.intro\ntheorem exactReceipt : True := original\n'
        fixtures['plain-public-bridge'] = 'theorem original : True := True.intro\npublic theorem _root_.exactReceipt : True := original\n'
        fixtures['module-public-bridge'] = 'module\npublic theorem original : True := True.intro\npublic theorem _root_.exactReceipt : True := original\n'
        fixtures['counterfeit-literal-type'] = 'prelude\ninductive Nat : Type\ninductive False : Prop\ndef impossible : Nat := nat_lit 0\ntheorem exactReceipt : False := Nat.rec (motive := fun _ => False) impossible\n'
        if request.get('cases'):
            fixtures = {label: source for label, source in fixtures.items() if label in request['cases']}
        for label, source in fixtures.items():
            print('probing ' + label, file=sys.stderr, flush=True)
            case = {'compiled_source': source}
            reuse = reuse_cases.get(label)
            if reuse and reuse.get('compiled_source') != source:
                raise RuntimeError('Retained fixture source differs from this probe')
            more_mounts, roots = [], ['/replay']
            environment = trusted_env
            if label == 'actual-library-source-disagreement':
                library_source = stage / 'library-source'
                library_source.mkdir()
                real_source = 'def ActualProblem : Prop := True\n'
                (library_source / 'Foo.lean').write_text(real_source)
                built = reuse['library_compile'] if reuse else execute('',
                    ['/toolchain/bin/lean', '-j2', '-o', '/outputs/Main.olean', '/build/Foo.lean'],
                    [(library_source, '/build', True)], retain=True, cwd='/build')
                case['library_compile'] = built
                if built['exit_code'] or not built.get('compiled_output'):
                    observed['cases'][label] = case
                    continue
                library = stage / 'library'
                library.mkdir()
                source_claim = 'def ActualProblem : Prop := False\n'
                (library / 'Foo.lean').write_text(source_claim)
                (library / 'Foo.olean').write_bytes(base64.b64decode(built['compiled_output']['content'], validate=True))
                case['library_compiled_source'] = real_source
                case['library_retained_source'] = source_claim
                case['library_files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in library.iterdir()}
                if reuse and case['library_files'] != reuse['library_files']:
                    raise RuntimeError('Retained library file set/bytes differ')
                more_mounts.append((library, '/library', True))
                roots.append('/library')
                environment = {**trusted_env, 'LEAN_PATH': '/library'}
            if reuse:
                compiled = reuse['compile']
                case['retained_basis'] = request['reuse_path']
            else:
                compiled = execute(source, ['/toolchain/bin/lean', '-j2', '-o', '/outputs/Main.olean', '/inputs/Main.lean'],
                                   more_mounts, retain=True, environment=environment)
            case['compile'] = compiled
            blob = compiled.get('compiled_output')
            if not blob or compiled['exit_code'] or compiled['timed_out']:
                observed['cases'][label] = case
                continue
            objects = stage / label
            objects.mkdir()
            (objects / 'Main.olean').write_bytes(base64.b64decode(blob['content'], validate=True))
            for name, part in compiled.get('compiled_parts', {}).items():
                (objects / name).write_bytes(base64.b64decode(part['content'], validate=True))
            case['compiled_sha256'] = blob['sha256']
            if reuse:
                case['replay'] = reuse['replay']
            else:
                case['replay'] = run({'source': '', 'timeout': 180}, mounts=[*mounts, *more_mounts, (objects, '/replay', True)],
                    guest_command=['/toolchain/bin/leanchecker', '--fresh', 'Main'],
                    extra_environment={**trusted_env, 'LEAN_PATH': ':'.join(roots)}, address_space_bytes=8 * 1024**3)
            retained_report = request.get('retained_report', False)
            inspection = execute(request['helper'], ['/toolchain/bin/lean', '-j2', '--run', '/inputs/Main.lean',
                *(['--verify-retained'] if retained_report else []), 'Main', 'exactReceipt', *roots],
                [*more_mounts, (objects, '/replay', True)], retain=retained_report, retained_kind='semantics' if retained_report else 'compiled')
            case['inspection_process'] = inspection
            if not inspection['exit_code'] and not inspection['timed_out'] and not inspection['output_limited']:
                output = base64.b64decode(inspection['semantic_output']['content'], validate=True).decode() if retained_report else inspection['stdout']
                case['verification'] = json.loads(output)
                case['semantics'] = case['verification'].get('semantics', case['verification'])
            observed['cases'][label] = case
            if label == 'true':
                case['absent_symbol'] = execute(request['helper'], ['/toolchain/bin/lean', '-j2', '--run',
                    '/inputs/Main.lean', 'Main', 'missingExactReceipt', '/replay'], [(objects, '/replay', True)])
        observed['official_choice'] = execute(request['helper'], ['/toolchain/bin/lean', '-j2', '--run',
                                             '/inputs/Main.lean', '--inspect', 'Init.Prelude', 'Classical.choice'])
        observed['official_quotient'] = execute(request['helper'], ['/toolchain/bin/lean', '-j2', '--run',
                                                '/inputs/Main.lean', '--inspect', 'Init.Core', 'Quot'])
    return observed


def driver():
    from mathtrace.store import Store
    from mathtrace.toolchain import verify_toolchain
    with Store(ROOT / 'work/validation/formal/state.sqlite') as store:
        toolchain = store.records('toolchain')[0]
        verify_toolchain(toolchain)
    request = {'toolchain': toolchain['data'], 'helper': (ROOT / 'mathtrace/lean_inspector.lean').read_text()}
    if '--ordinary' in sys.argv:
        request['cases'] = ['true', 'projection-literal-recursion']
    if '--cases' in sys.argv:
        request['cases'] = sys.argv[sys.argv.index('--cases') + 1].split(',')
    if '--comparison-only' in sys.argv:
        request['comparison_only'] = True
    if '--retained-report' in sys.argv:
        request['retained_report'] = True
    if '--reuse' in sys.argv:
        previous = Path(sys.argv[sys.argv.index('--reuse') + 1]).resolve()
        evidence = json.loads(previous.read_text())
        if evidence['toolchain_record_hash'] != toolchain['hash']:
            raise RuntimeError('Retained baseline uses another toolchain')
        reusable = {}
        for label, basis in evidence['cases'].items():
            if label not in {'true', 'actual-library-source-disagreement', 'shadowed-foundation-name',
                              'projection-literal-recursion', 'module-public-bridge', 'plain-public-bridge'}:
                continue
            compiled, replay = basis['compile'], basis['replay']
            blob = compiled['compiled_output']
            if (compiled['exit_code'] or compiled['timed_out'] or compiled.get('output_limited')
                    or not compiled.get('namespace_setup') or replay['exit_code'] or replay['timed_out']
                    or replay.get('output_limited') or not replay.get('namespace_setup')
                    or hashlib.sha256(base64.b64decode(blob['content'], validate=True)).hexdigest() != blob['sha256']):
                raise RuntimeError('Retained baseline is not exact successful evidence for this toolchain')
            if 'library_compile' in basis:
                library_blob = basis['library_compile']['compiled_output']
                if hashlib.sha256(base64.b64decode(library_blob['content'], validate=True)).hexdigest() != library_blob['sha256']:
                    raise RuntimeError('Retained library object bytes differ')
            for part in compiled.get('compiled_parts', {}).values():
                raw = base64.b64decode(part['content'], validate=True)
                if hashlib.sha256(raw).hexdigest() != part['sha256'] or len(raw) != part['size']:
                    raise RuntimeError('Retained supplementary object bytes differ')
            reusable[label] = basis
        request.update(reuse_cases=reusable, reuse_path=str(previous), reuse_sha256=hashlib.sha256(previous.read_bytes()).hexdigest())
    prefix = [str(Path(os.environ['SystemRoot']) / 'System32/wsl.exe'), '-d', 'Ubuntu', '--exec']
    script = subprocess.check_output(prefix + ['/usr/bin/wslpath', '-a', str(Path(__file__).resolve())], text=True).strip()
    process = subprocess.run(prefix + ['/usr/bin/python3', '-I', script, '--guest'],
        input=json.dumps(request), text=True, capture_output=True, encoding='utf-8', timeout=1200)
    if process.returncode:
        raise RuntimeError(process.stderr)
    observed = json.loads(process.stdout)
    observed['toolchain_record_hash'] = toolchain['hash']
    if 'reuse_path' in request:
        observed['retained_basis'] = {'path': request['reuse_path'], 'sha256': request['reuse_sha256']}
    verify_toolchain(toolchain)
    destination = ROOT / 'work/validation/formal' / ('semantic-probe-' + uuid.uuid4().hex + '.json')
    destination.write_text(json.dumps(observed, indent=2), encoding='utf-8')
    print(str(destination))
    if observed.get('helper_compile', {}).get('exit_code'):
        print(observed['helper_compile']['stdout'][:6000])
    for label, case in observed['cases'].items():
        semantics = case.get('semantics', {})
        print(json.dumps({'case': label, 'compile': case.get('compile', case.get('library_compile'))['exit_code'],
            'replay': case.get('replay', {}).get('exit_code'),
            'inspection': case.get('inspection_process', {}).get('exit_code'),
            'declarations': len(semantics.get('declarations', [])),
            'expressions': len(semantics.get('expressions', [])),
            'inspection_error': case.get('inspection_process', {}).get('stdout', '')[:1500]
                if not semantics else None}))


if __name__ == '__main__':
    if '--guest' in sys.argv:
        print(json.dumps(guest(json.load(sys.stdin))))
    else:
        driver()
