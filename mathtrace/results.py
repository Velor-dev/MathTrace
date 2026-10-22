"""Pure worker-result syntax/contract checking, separate from producer evidence."""
import json
import math

from .store import StateError

RESULT_CONTRACT_V1 = 'exact-worker-result-contract-v1'
RESULT_CONTRACT_PROFILE = 'exact-worker-result-contract-v2'
REVIEW_ROLES_V1 = frozenset({'referee', 'theorem-checker', 'fidelity-auditor', 'adjudicator', 'falsifier'})


class ResultProtocolError(StateError):
    """An attributed response does not satisfy its exact result contract."""


def worker_result(packet, task_id, packet_hash, text, *, profile=RESULT_CONTRACT_PROFILE):
    if profile not in {RESULT_CONTRACT_V1, RESULT_CONTRACT_PROFILE}:
        raise StateError('Unsupported worker-result validation profile')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ResultProtocolError('Worker result has duplicate JSON keys')
            result[key] = value
        return result

    def invalid(value):
        raise ResultProtocolError('Worker result contains a non-finite JSON number')

    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            invalid(value)
        return result

    try:
        output = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid, parse_float=finite)
    except (ValueError, TypeError, RecursionError) as error:
        raise ResultProtocolError('Worker response must be one exact structured result object') from error
    if (not isinstance(output, dict) or output.get('task_id') != task_id
            or output.get('packet_hash') != packet_hash):
        raise ResultProtocolError('Worker result addresses a different task or packet')
    if profile == RESULT_CONTRACT_PROFILE:
        allowed = {'task_id', 'packet_hash', 'outcome', 'reasoning', 'verdict', 'checks', 'requested_context', 'proposals'}
        if set(output) - allowed:
            raise ResultProtocolError('Worker result contains unassigned fields; substance requires examination')
        if 'requested_context' in output and (not isinstance(output['requested_context'], list)
                or any(not isinstance(s, str) or not s.strip() for s in output['requested_context'])):
            raise ResultProtocolError('Requested context must be exact information-request strings')
        if 'proposals' in output and not isinstance(output['proposals'], list):
            raise ResultProtocolError('Worker proposal container must be an exact list')
    reasoning = output.get('reasoning')
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ResultProtocolError('Worker result lacks reasoning/evidence')
    outcome = output.get('outcome')
    if (not isinstance(outcome, str) or outcome not in
            {'proposal', 'review', 'context-request', 'inconclusive', 'counterexample'}
            or outcome not in packet['outcomes']):
        raise ResultProtocolError('Outcome is not permitted by the exact task contract')
    checks = output.get('checks', [])
    if (not isinstance(checks, list) or any(not isinstance(c, str) or not c.strip() for c in checks)
            or not set(checks).issubset(packet['checks'])):
        raise ResultProtocolError('Worker checks are malformed or outside its task contract')
    verdict = output.get('verdict')
    if outcome == 'review':
        if (packet['role'] not in REVIEW_ROLES_V1 or not isinstance(verdict, str)
                or verdict not in {'pass', 'fail', 'inconclusive'} or not checks):
            raise ResultProtocolError('This task/result cannot issue the declared review')
        if profile == RESULT_CONTRACT_PROFILE and (output.get('proposals') or output.get('requested_context')):
            raise ResultProtocolError('A scoped review cannot conceal proposals or context requests in another field')
    elif verdict is not None:
        raise ResultProtocolError('Non-review result must not carry a review verdict')
    if profile == RESULT_CONTRACT_PROFILE:
        if outcome != 'context-request' and output.get('requested_context'):
            raise ResultProtocolError('Only a context-request outcome consumes requested context')
        if outcome == 'context-request' and output.get('proposals'):
            raise ResultProtocolError('A context request cannot conceal mathematical proposals')
    # Proposal and context-request contents are retained before ingestion checks.
    # Invalid proposals are a separate root-assessment frontier, not a fabricated
    # failed host response or a reason to discard substantive negative evidence.
    return output
