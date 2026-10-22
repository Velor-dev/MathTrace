"""Explicit, unmocked Lean boundary validation; never promotes mathematics."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathtrace.backend import invoke, EXECUTION_PROTOCOL
from mathtrace.store import Store
from mathtrace.toolchain import verify_toolchain
from mathtrace.formal import MODE_RECEIPT_VERSION, PROFILE, blob_bytes, validate_report, process_passed, compiled_bundle

SOURCES = {
    'proof': 'theorem t : True := by trivial\n#print axioms t\n',
    'module-proof': 'module\npublic theorem t : True := True.intro\n#print axioms t\n',
    'sorry': 'theorem t : False := by sorry\n#print axioms t\n',
    'invalid': 'theorem t : False := by trivial\n#print axioms t\n',
    'kernel-bypass': '''import Lean
open Lean Elab Command
set_option debug.skipKernelTC true
run_cmd liftCoreM do
  addDecl (.thmDecl {name := `t, levelParams := [], type := mkConst ``False, value := mkConst ``True.intro})
#print axioms t
''',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=SOURCES)
    parser.add_argument('--db', type=Path, default=Path('work/validation/formal/state.sqlite'))
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--profile', action='store_true', help='Exercise the checked compiled-evidence channel')
    parser.add_argument('--execution-mode', choices=['direct', 'bubblewrap'], default='direct')
    args = parser.parse_args()
    with Store(args.db) as store:
        toolchains = store.records('toolchain')
        if len(toolchains) != 1:
            raise RuntimeError('Validation fixture requires one explicitly provisioned toolchain')
        record = toolchains[0]
        verify_toolchain(record)
        verification = None
        if args.profile:
            verification = {'protocol': MODE_RECEIPT_VERSION, 'profile': PROFILE, 'check_symbol': 't',
                            'helper_source': (Path(__file__).resolve().parents[1] / 'mathtrace/lean_inspector.lean').read_text(encoding='utf-8')}
        request = {'operation':'formal', 'source':SOURCES[args.case], 'toolchain':record['data'],
                   'libraries':[], 'timeout':args.timeout, 'execution_mode':args.execution_mode,
                   'execution_protocol':EXECUTION_PROTOCOL}
        if verification:
            request['verification'] = verification
        execution = invoke(request)
        verify_toolchain(record)
    result = execution['result']
    compiled = execution.get('compiled_output')
    if args.case in {'proof', 'module-proof'}:
        passed = result['exit_code'] == 0 and bool(compiled) and "'t' does not depend on any axioms" in result['stdout']
    elif args.case == 'sorry':
        passed = result['exit_code'] == 0 and bool(compiled) and 'sorryAx' in result['stdout']
    elif args.case == 'invalid':
        passed = result['exit_code'] is not None and result['exit_code'] != 0
    else:
        passed = result['exit_code'] == 0 and bool(compiled)
    replay = execution.get('replay')
    replay_passed = bool(replay and replay['exit_code'] == 0 and not replay['timed_out'] and not replay['output_limited'])
    replay_rejected = bool(replay and replay['exit_code'] is not None and replay['exit_code'] != 0
                           and not replay['timed_out'] and not replay['output_limited'])
    passed = bool(passed and not result['timed_out'] and not result['output_limited']
                  and (replay_rejected if args.case == 'kernel-bypass' else args.case == 'invalid' or replay_passed))
    if args.profile and args.case in {'proof', 'module-proof'}:
        compiled_bundle(execution)
        report = json.loads(blob_bytes(execution['semantic_output'], limit=64 * 1024 * 1024))
        validate_report(report, 't', ['propext', 'Classical.choice', 'Quot.sound'])
        passed = passed and process_passed(replay, args.execution_mode) and execution['resolved_inputs'] is not None and not execution['verification_error']
    profile_accepted = None
    if args.profile and execution.get('semantic_output'):
        report = json.loads(blob_bytes(execution['semantic_output'], limit=64 * 1024 * 1024))
        try:
            validate_report(report, 't', ['propext', 'Classical.choice', 'Quot.sound'])
            profile_accepted = True
        except ValueError:
            profile_accepted = False
        if args.case == 'sorry':
            passed = passed and profile_accepted is False
    output = args.db.parent / ('validation-' + args.case + ('-profile' if args.profile else '') + '.json')
    output.write_text(json.dumps({'case': args.case, 'source': SOURCES[args.case],
        'toolchain_hash': record['hash'], 'passed': passed, 'profile_accepted':profile_accepted, 'execution': execution}, indent=2), encoding='utf-8')
    print(json.dumps({'case': args.case, 'passed': passed, 'exit_code': result['exit_code'],
                      'compiled_bytes': compiled['size'] if compiled else None, 'replay_passed': replay_passed,
                      'evidence': str(output.resolve())}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
