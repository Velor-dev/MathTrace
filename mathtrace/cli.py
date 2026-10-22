"""Local root control surface. Worker agents return proposals instead of calling it."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .campaign import Campaign
from .context import Tasks
from .evidence import Evidence
from .toolchain import Toolchains
from .orchestration import Orchestration
from .native_capture import NativeCapture
from .coordination import Coordination
from .completion import Completion
from .advisory import Advisory
from .curation import Curation
from .store import Store, StateError

OPERATIONS = {
    'artifact', 'contract', 'definition', 'assumption', 'claim', 'inference',
    'review', 'promote', 'withdraw', 'objection', 'adjudication', 'adjudicate', 'resolve_objection', 'finding_blocking', 'finding_effects',
    'counterexample', 'validate_counterexample', 'counterexample_report_condition', 'claim_state',
    'route', 'obligation', 'close_obligation', 'route_status', 'external_theorem',
    'application', 'accept_application', 'freeze', 'candidate_current', 'candidate_audit_current', 'audit_candidate',
    'release', 'release_current', 'portfolio', 'learning', 'learning_current', 'progress',
}
TASK_OPERATIONS = {'task': 'create', 'packet': 'packet', 'extend_task': 'extend',
                   'expand_semantics': 'expand_semantics',
                   'background': 'background',
                   'start_run': 'start', 'record_exposure': 'expose', 'finish_run': 'finish'}
EVIDENCE_OPERATIONS = {'experiment', 'run_experiment', 'formal_plan', 'run_lean',
                       'inspect_execution', 'recover_execution', 'install_lean'}
ORCHESTRATION_OPERATIONS = {'ingest': 'ingest', 'resolve_context': 'resolve_context', 'capture_native': 'collect', 'reserve_native': 'reserve',
                            'resolve_semantic_context': 'resolve_semantic_context',
                            'strategize': 'strategize',
                            'inspect_record': 'inspect_record',
                            'dispose_result': 'dispose_result',
                            'assess_execution': 'assess_execution',
                            'assess_native_failure': 'assess_native_failure',
                            'assess_ingestion_failure': 'assess_ingestion_failure',
                            'dispose_formal_evidence': 'dispose_formal_evidence',
                            'inspect_native': 'inspect',
                            'inspect_native_context': 'inspect_native_context',
                            'admit_native_context': 'admit_native_context',
                            'recover_native': 'recover',
                            'checkpoint': 'checkpoint', 'checkpoint_snapshot': 'checkpoint_snapshot', 'next': 'next_actions'}
COORDINATION_OPERATIONS = {'frontier', 'prepare_work', 'inspect_work', 'continue_work'}
COMPLETION_OPERATIONS = {'completion_request': 'request', 'activate_completion': 'activate',
    'completion_evidence': 'evidence', 'fulfillment': 'fulfillment',
    'record_fulfillment': 'record_fulfillment', 'fulfillment_current': 'certificate_current'}
ADVISORY_OPERATIONS = {'route_transition': 'transition', 'route_condition': 'condition', 'advisory_boundary': 'boundary'}
CURATION_OPERATIONS = {'extract_learning': 'extract', 'curate_learning': 'curate',
    'learning_candidate_current': 'candidate_current', 'admit_learning': 'admit',
    'learning_admission_current': 'admission_current', 'select_learning': 'selection'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='MathTrace root research control', epilog='Execution operations accept JSON execution_mode: direct (default) or bubblewrap (explicit Linux/WSL).')
    parser.add_argument('operation', choices=sorted(OPERATIONS | EVIDENCE_OPERATIONS | COORDINATION_OPERATIONS | set(COMPLETION_OPERATIONS) | set(ADVISORY_OPERATIONS) | set(CURATION_OPERATIONS) | set(TASK_OPERATIONS) | set(ORCHESTRATION_OPERATIONS) | {'init', 'health', 'snapshot', 'identity'}))
    parser.add_argument('--db', type=Path, default=Path('.math/state.sqlite'))
    parser.add_argument('--input', type=Path, help='JSON argument object; omit to read standard input for operations')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'identity':
            result = {'name': 'mathtrace', 'version': __version__, 'module': str(Path(__file__).resolve())}
        else:
            with Store(args.db, create=args.operation == 'init') as store:
                if args.operation == 'init':
                    result = {'database': str(store.path), 'revision': store.revision}
                elif args.operation == 'health':
                    result = store.health()
                elif args.operation == 'snapshot':
                    result = store.export()
                else:
                    if args.input:
                        raw = args.input.read_text(encoding='utf-8-sig')
                    elif args.operation in {'progress', 'next'}:
                        raw = '{}'
                    elif sys.stdin.isatty():
                        raise StateError('Provide an argument object using --input path.json')
                    else:
                        raw = sys.stdin.read()
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise StateError('Operation input must be a JSON object')
                    campaign = Campaign(store)
                    if args.operation in TASK_OPERATIONS:
                        result = getattr(Tasks(campaign), TASK_OPERATIONS[args.operation])(**data)
                    elif args.operation in EVIDENCE_OPERATIONS:
                        result = (Toolchains(store).install_lean(**data) if args.operation == 'install_lean'
                                  else getattr(Evidence(campaign), args.operation)(**data))
                    elif args.operation in ORCHESTRATION_OPERATIONS:
                        controller = NativeCapture(campaign) if args.operation in {'capture_native', 'reserve_native', 'inspect_native', 'recover_native', 'inspect_native_context', 'admit_native_context'} else Orchestration(campaign)
                        result = getattr(controller, ORCHESTRATION_OPERATIONS[args.operation])(**data)
                    elif args.operation in COORDINATION_OPERATIONS:
                        result = getattr(Coordination(campaign), args.operation)(**data)
                    elif args.operation in COMPLETION_OPERATIONS:
                        result = getattr(Completion(campaign), COMPLETION_OPERATIONS[args.operation])(**data)
                    elif args.operation in ADVISORY_OPERATIONS:
                        result = getattr(Advisory(campaign), ADVISORY_OPERATIONS[args.operation])(**data)
                    elif args.operation in CURATION_OPERATIONS:
                        result = getattr(Curation(campaign), CURATION_OPERATIONS[args.operation])(**data)
                    else:
                        result = getattr(campaign, args.operation)(**data)
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False))
        return 2 if args.operation == 'health' and not result['ok'] else 0
    except (StateError, OSError, ValueError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
