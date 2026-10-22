"""Durable root execution intent and exact recorder recovery.

Missing observations never establish termination. This ledger is not an OS
process supervisor; only a terminal trusted-recorder envelope closes an attempt.
"""
from __future__ import annotations

import json
import math

from .research import nonempty
from .store import StateError, digest, ZERO_HASH


def validate_mode_observation(attempt, envelope):
    """New protocol is explicit; absent mode metadata retains historical rules."""
    metadata = attempt.get('metadata', {})
    if 'execution_protocol' not in metadata:
        return
    from .backend import EXECUTION_PROTOCOL
    selected = metadata.get('execution_mode')
    if (metadata['execution_protocol'] != EXECUTION_PROTOCOL
            or selected not in ('direct', 'bubblewrap')
            or envelope.get('execution_mode') != selected
            or envelope.get('execution_protocol') != EXECUTION_PROTOCOL
            or envelope.get('producer', {}).get('execution_mode') != selected
            or envelope.get('producer', {}).get('execution_protocol') != EXECUTION_PROTOCOL):
        raise StateError('Recorder mode/protocol differs from committed execution')
    result = envelope.get('result', {})
    if selected == 'direct' and envelope.get('ok'):
        if attempt.get('operation') == 'formal':
            roots = result.get('staged_roots')
            if not isinstance(roots, dict) or roots.get('stage') != envelope['producer'].get('stage'):
                raise StateError('Native staging roots are not bound to the recorded producer')


def execution_timeout(value):
    if type(value) not in {int, float} or not math.isfinite(value) or not 0 < value <= 86400:
        raise StateError('Execution timeout must be a finite positive number, at most one day')
    return float(value)


class Executions:
    def __init__(self, research):
        self.r, self.store = research, research.store

    def directory(self, identifier):
        self.store.get(identifier, 'execution')
        return self.store.path.parent / 'executions' / identifier

    def begin(self, plan, operation, request, *, metadata=None, rerun_of=None, reason=None):
        if self.store.db.in_transaction:
            raise StateError('Execution intent must commit outside any enclosing transaction')
        with self.store.transaction():
            record = self.store.get(plan, 'formal_plan' if operation == 'formal' else 'experiment')
            if operation == 'compute' and record['data'].get('evidence_class') != 'computation-proposal':
                raise StateError('Select an experiment proposal, not a receipt')
            if not self.r._scope_current(plan):
                raise StateError('Execution plan/source scope is not current')
            checks = ({'formal-source-integrity', 'formal-target-fidelity', 'foundations'}
                      if operation == 'formal' else {'execution-scope', 'source-integrity'})
            reviews = self.r._reviews(plan, checks)
            attempts = [e for e in self.store.records('execution') if e['data']['plan'] == plan]
            fingerprint = digest({'operation': operation, 'request': request, 'reason': reason})
            for attempt in attempts:
                if attempt['data']['rerun_of'] == rerun_of:
                    if attempt['data']['fingerprint'] != fingerprint:
                        raise StateError('Existing attempt has different parameters; request an explicit rerun')
                    return attempt['id'], False
            if rerun_of is not None:
                nonempty(reason, 'deliberate rerun reason')
                previous = self.store.get(rerun_of)
                if previous['kind'] == 'execution':
                    if previous['data']['plan'] != plan or self.store.status(rerun_of) not in {'completed', 'failed'}:
                        raise StateError('Rerun requires a terminal attempt of this exact plan')
                    if not attempts or attempts[-1]['id'] != rerun_of:
                        raise StateError('Rerun must extend the latest attempt')
                    terminal = self._terminal_response(rerun_of)
                    if not terminal['attribution_current']:
                        raise StateError('Rerun requires currently attributable termination evidence')
                elif (previous['kind'] not in {'experiment', 'formal_receipt'}
                      or previous['data'].get('plan') != plan or attempts):
                    raise StateError('Legacy rerun must name an exact prior receipt before new attempts exist')
                elif self.store.status(rerun_of) not in {'checked', 'failed', 'observed', 'withdrawn'}:
                    raise StateError('Legacy receipt does not establish a terminal execution')
            elif reason is not None:
                raise StateError('A rerun reason requires rerun_of')
            else:
                legacy = [r for kind in ('experiment', 'formal_receipt') for r in self.store.records(kind)
                          if r['data'].get('plan') == plan]
                if legacy:
                    raise StateError('Plan has historical receipts; name one in rerun_of with a reason')
            if operation == 'formal':
                toolchain = self.store.get(metadata['toolchain'], 'toolchain')
                if self.store.status(toolchain['id']) != 'installed' or not self.r._scope_current(toolchain['id']):
                    raise StateError('Execution toolchain is not current')
            head = self.store.db.execute('SELECT hash FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            identifier = self.store.put('execution', {
                'plan': plan, 'plan_hash': record['hash'], 'operation': operation,
                'request_hash': digest(request), 'fingerprint': fingerprint,
                'source': record['data'].get('check_source', record['data']['source']),
                'source_hash': self.store.get(record['data'].get('check_source', record['data']['source']))['hash'],
                'target_hash': self.store.get(record['data']['target'])['hash'],
                'timeout': request['timeout'], 'metadata': metadata or {}, 'source_reviews': reviews,
                'base_revision': self.store.revision, 'event_head': head['hash'] if head else ZERO_HASH,
                'rerun_of': rerun_of, 'reason': reason})
            self.store.decide(identifier, 'pending', {'reason': 'Committed launch intent; execution is not yet observed'})
            return identifier, True

    def journal(self, identifier):
        data = self.store.get(identifier, 'execution')['data']
        return {'directory': str(self.directory(identifier)), 'execution': identifier,
                'request_hash': data['request_hash']}

    def selection(self, plan, selected, rerun_of):
        from .backend import mode
        for attempt in self.store.records('execution'):
            data = attempt['data']
            if data['plan'] == plan and data['rerun_of'] == rerun_of:
                recorded = data['metadata'].get('execution_mode', 'bubblewrap')
                if selected is not None and mode(selected) != recorded:
                    raise StateError('Existing attempt has a different execution mode')
                return recorded, data['metadata'].get('execution_protocol')
        from .backend import EXECUTION_PROTOCOL
        return mode(selected), EXECUTION_PROTOCOL

    def uncertain(self, identifier, error):
        with self.store.transaction():
            if self.store.status(identifier) in {'pending', 'uncertain'}:
                self.store.decide(identifier, 'uncertain', {'reason': str(error), 'retry_authorized': False})

    def terminal(self, identifier, envelope, writer):
        """Retain terminal evidence even when mathematical scope changed mid-run."""
        with self.store.transaction():
            record = self.store.get(identifier, 'execution')
            data = record['data']
            validate_mode_observation(data, envelope)
            if (not isinstance(envelope, dict) or envelope.get('execution') != identifier
                    or envelope.get('request_hash') != data['request_hash']
                    or envelope.get('teardown') != 'recorder-owned-processes-waited'
                    or type(envelope.get('ok')) is not bool):
                raise StateError('Terminal recorder observation does not bind this exact execution')
            producer = envelope.get('producer')
            if (not isinstance(producer, dict) or producer.get('execution') != identifier
                    or producer.get('request_hash') != data['request_hash']
                    or digest(producer) != envelope.get('producer_hash')):
                raise StateError('Terminal observation lacks its exact producer attribution')
            fingerprint = digest(envelope)
            previous = self._terminal_response(identifier)
            if previous is not None:
                if self.store.get(previous['observation'])['data']['content_hash'] != fingerprint:
                    raise StateError('Conflicting terminal observations for one attempt')
                return previous
            if self.store.status(identifier) not in {'pending', 'uncertain', 'withdrawn'}:
                raise StateError('Attempt cannot accept another terminal observation')
            observation = self.store.put('artifact', {'text': json.dumps(envelope, sort_keys=True),
                'media_type': 'application/vnd.mathtrace.process-observation+json', 'content_hash': fingerprint})
            receipt = writer(data, envelope['result']) if envelope['ok'] else None
            reason = {
                'observation': observation, 'observation_hash': fingerprint, 'receipt': receipt,
                'scope_current_at_import': self.r._scope_current(data['plan']),
                'finish_revision': self.store.revision + 1, 'reason': 'Observed recorder termination and retained output'}
            self.store.event('execution-terminal', identifier, reason)
            if self.store.status(identifier) != 'withdrawn':
                self.store.decide(identifier, 'completed' if envelope['ok'] else 'failed', reason)
            return self._terminal_response(identifier)

    def _terminal_response(self, identifier):
        row = self.store.db.execute("SELECT payload FROM events WHERE type='execution-terminal' "
                                    'AND target=? ORDER BY seq DESC LIMIT 1', (identifier,)).fetchone()
        if row is None:
            return None
        reason = json.loads(row['payload'])
        observation = self.store.get(reason['observation'], 'artifact')
        envelope = json.loads(observation['data']['text'])
        data = self.store.get(identifier, 'execution')['data']
        if (digest(envelope) != reason['observation_hash']
                or observation['data']['content_hash'] != reason['observation_hash']
                or envelope['execution'] != identifier or envelope['request_hash'] != data['request_hash']):
            raise StateError('Recorded terminal observation is not intact')
        if reason['receipt'] is not None:
            receipt = self.store.get(reason['receipt'])
            if receipt['data'].get('execution') != identifier or receipt['data'].get('plan') != data['plan']:
                raise StateError('Terminal receipt does not bind this exact attempt')
        return {'execution': identifier, 'receipt': reason['receipt'], 'observation': observation['id'],
                'ok': envelope['ok'], 'error': envelope.get('error'),
                'attribution_current': (self.store.status(identifier) in {'completed', 'failed'}
                    and self.r._scope_current(observation['id']) and not self.r._blocked(identifier))}

    def inspect(self, identifier):
        data = self.store.get(identifier, 'execution')['data']
        status = self.store.status(identifier)
        result = {'execution': identifier, 'plan': data['plan'], 'status': status,
                  'retry_authorized': False, 'liveness': 'not-established', 'terminal_available': False}
        directory = self.directory(identifier)
        if (directory / 'started.json').is_file():
            started = json.loads((directory / 'started.json').read_text(encoding='utf-8'))
            if started.get('execution') != identifier or started.get('request_hash') != data['request_hash']:
                raise StateError('Recorder start identity does not match the exact attempt')
            result['recorded_producer'] = started
        result['terminal_available'] = (directory / 'terminal.json').is_file()
        terminal = self._terminal_response(identifier)
        if terminal is not None:
            result['terminal'] = terminal
        return result

    def recover(self, identifier, writer):
        state = self.inspect(identifier)
        if 'terminal' in state:
            return state['terminal']
        if not state['terminal_available']:
            raise StateError('Execution termination is unobserved; inspect the attempt, do not retry')
        directory = self.directory(identifier)
        envelope = json.loads((directory / 'terminal.json').read_text(encoding='utf-8'))
        started = state.get('recorded_producer')
        if not started or envelope.get('producer') != started or envelope.get('producer_hash') != digest(started):
            raise StateError('Terminal observation is not bound to the recorded producer')
        return self.terminal(identifier, envelope, writer)
