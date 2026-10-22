"""Read-only adapter for observed Antigravity CLI producer records.

Schema profile: CLI JSONL public transcript plus SQLite protobuf fields observed
on 2026-09-08. Unknown layouts fail closed. This is local producer provenance,
not a cryptographic attestation or a claim of statistically independent errors.
No thought/hidden-reasoning fields are exported.
"""

from __future__ import annotations

import json
import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .context import Tasks
from .results import RESULT_CONTRACT_V1, RESULT_CONTRACT_PROFILE, ResultProtocolError, worker_result
from .native import runtime_files
from .store import StateError, canonical, digest

UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')


class NativeObservationUnavailable(StateError):
    """Current local host files are absent; retained evidence remains usable."""


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise StateError('Duplicate JSON keys are not exact packet evidence')
            result[key] = value
        return result
    def invalid(value):
        raise StateError(f'Non-finite JSON value: {value}')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


PARENT_MESSAGE = re.compile(
    r'The following is a <SYSTEM_MESSAGE> not actually sent by the user\. '
    r'It is provided by the system as important information to pay attention to\.\n\n'
    r'<SYSTEM_MESSAGE>\n\[Message\] timestamp=(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z) '
    r'sender=(?P<sender>[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}) '
    r'priority=(?P<priority>MESSAGE_PRIORITY_HIGH) content=(?P<content>\{.*\})\n</SYSTEM_MESSAGE>',
    re.DOTALL)


def task_input_observation(rows: list[dict], parent: str | None = None) -> dict:
    """Observe one whole input before the first terminal; no arbitrary JSON extraction."""
    terminal = next((i for i, row in enumerate(rows)
        if row.get('type') == 'PLANNER_RESPONSE' and row.get('status') == 'DONE'), None)
    prefix = rows[:terminal + 1] if terminal is not None else rows
    candidates = []
    for position, row in enumerate(prefix):
        if row.get('type') == 'USER_INPUT':
            if row.get('status') != 'DONE':
                raise StateError('Child task input is not completed')
            if not isinstance(row.get('content'), str):
                raise StateError('Child task input is not exact JSON text')
            packet = strict_json(row.get('content', ''))
            candidates.append({'position': position, 'row': row, 'packet': packet,
                'profile': 'raw-user-input-v1', 'header': None})
        elif row.get('type') == 'SYSTEM_MESSAGE' and isinstance(row.get('content'), str):
            envelope = PARENT_MESSAGE.fullmatch(row['content'])
            if envelope is None:
                continue  # Nonpacket context remains observable exposure.
            packet = strict_json(envelope['content'])
            if not isinstance(packet, dict) or not {'task_id', 'packet_hash'}.issubset(packet):
                continue
            if row.get('source') != 'SYSTEM' or row.get('status') != 'DONE':
                raise StateError('Native parent-message task input has unqualified source/status')
            try:
                datetime.fromisoformat(envelope['timestamp'].replace('Z', '+00:00'))
            except ValueError as error:
                raise StateError('Malformed native parent-message timestamp') from error
            candidates.append({'position': position, 'row': row, 'packet': packet,
                'profile': 'antigravity-parent-message-v1',
                'header': {key: envelope[key] for key in ('timestamp', 'sender', 'priority')}})
    if len(candidates) != 1:
        raise StateError('Child context does not contain one exact completed task input')
    observed = candidates[0]
    if parent is not None and observed['header'] and observed['header']['sender'] != parent:
        raise StateError('Native task message sender differs from the allocated parent')
    return observed


def native_failure_evidence(store, identifier):
    """Authenticate retained terminal failure, without consulting today's host."""
    record = store.get(identifier, 'native_failure')
    d = record['data']
    if d.get('profile') != 'attributed-terminal-result-failure-v1':
        raise StateError('Unsupported native failure evidence profile')
    task = store.get(d['task'], 'task')
    run = store.get(d['run'], 'run')
    capture = store.get(d['capture_artifact'], 'artifact')
    response = store.get(d['response_artifact'], 'artifact')
    observed, value = strict_json(capture['data']['text']), strict_json(response['data']['text'])
    row = store.db.execute("SELECT payload FROM events WHERE type='native-protocol-failure' AND target=? "
                           'ORDER BY seq DESC LIMIT 1', (run['id'],)).fetchone()
    packet = task['data']['packet']
    if (not row or json.loads(row['payload']).get('failure') != identifier
            or task['data']['packet_hash'] != digest(packet) or d['packet_hash'] != task['data']['packet_hash']
            or d['target'] != packet['target'] or d['target_hash'] != packet['target_hash']
            or run['data']['task'] != task['id'] or run['data']['packet_hash'] != d['packet_hash']
            or run['data']['conversation_id'] != d['conversation_id']
            or capture['hash'] != d['capture_hash'] or response['hash'] != d['response_hash']
            or observed.get('kind') != 'native-dispatch-capture' or observed.get('task_id') != task['id']
            or observed.get('packet_hash') != d['packet_hash'] or observed.get('conversation_id') != d['conversation_id']):
        raise StateError('Native failure does not bind its actual named observation/task/run/response')
    finals = [r for r in observed['public_transcript'] if r.get('type') == 'PLANNER_RESPONSE' and r.get('status') == 'DONE']
    final = finals[0] if finals else None
    if (not final or final.get('status') != 'DONE'
            or d['terminal_public_response'] != {'step_index': final['step_index'], 'status': 'DONE',
                                                  'created_at': final.get('created_at')}
            or value != {'content_present': 'content' in final, 'content': final.get('content')}):
        raise StateError('Retained response differs from the attributed terminal public observation')
    if 'raw_response_binding' in d:
        content = final.get('content')
        expected = ({'encoding': 'utf-8', 'size': len(content.encode('utf-8')),
                     'sha256': hashlib.sha256(content.encode('utf-8')).hexdigest()}
                    if isinstance(content, str) else None)
        if d['raw_response_binding'] != expected:
            raise StateError('Retained raw-response byte binding differs from its exact content')
    try:
        worker_result(packet, task['id'], d['packet_hash'], final.get('content'),
                      profile=d.get('result_contract_profile', RESULT_CONTRACT_V1))
    except ResultProtocolError:
        return {'failure': record, 'records': [task, run, capture, response], 'response': value}
    raise StateError('Native protocol failure cannot represent a valid result')


def native_substance_origin_evidence(store, origin):
    """Verify static selected public bytes, independently of target eligibility."""
    if origin.get('profile') != 'retained-native-substance-origin-v1':
        raise StateError('Unsupported retained substance origin')
    source = store.get(origin['source_record'])
    task, run = store.get(origin['task'], 'task'), store.get(origin['run'], 'run')
    packet = task['data']['packet']
    capture, response = store.get(origin['capture_artifact'], 'artifact'), store.get(origin['response_artifact'], 'artifact')
    if (source['hash'] != origin['source_hash'] or run['data']['task'] != task['id']
            or run['data']['conversation_id'] != origin['conversation_id']
            or task['data']['packet_hash'] != origin['packet_hash'] or digest(packet) != origin['packet_hash']
            or origin['assigned_target'] != packet['target'] or origin['assigned_target_hash'] != packet['target_hash']
            or any(store.get(ref)['hash'] != value for ref, value in origin['producer_records'].items())):
        raise StateError('Retained substance origin does not bind its exact producer records')
    if source['kind'] not in {'native_failure', 'native_conflict', 'ingestion_failure'}:
        raise StateError('Unsupported retained substance source')
    d = source['data']
    if d['task'] != task['id'] or d.get('run', d.get('previous_run')) != run['id']:
        raise StateError('Retained source belongs to another task/run')
    expected_refs = set([task['id'], run['id'], capture['id'], response['id'],
        *[d[k] for k in ('result', 'host_receipt', 'capture_artifact', 'response_artifact') if d.get(k)]])
    if set(origin['producer_records']) != expected_refs:
        raise StateError('Retained substance origin omits actual producer evidence')
    selection = origin.get('observation_selection', 'terminal-response')
    if selection == 'complete-result-text':
        result = store.get(d['result'], 'result')['data']
        host = strict_json(store.get(result['host_receipt'], 'artifact')['data']['text'])
        if (response['id'] != result['artifact'] or result['task'] != task['id'] or result['run'] != run['id']
                or capture['id'] != host.get('producer_evidence', run['data']['dispatch_evidence'])
                or host.get('response') != response['data']['text']):
            raise StateError('Quarantined result origin differs from actual result/receipt evidence')
        selected = response['data']['text']
    else:
        observed = strict_json(capture['data']['text'])
        rows = observed['public_transcript']
        pos = next((i for i, row in enumerate(rows) if row.get('type') == 'PLANNER_RESPONSE'
                    and row.get('status') == 'DONE'), None)
        if capture['id'] != d['capture_artifact'] or observed.get('task_id') != task['id']:
            raise StateError('Selected public content differs from the named observation')
        if selection == 'terminal-response':
            if source['kind'] != 'native_failure' or pos is None or response['id'] != d['response_artifact']:
                raise StateError('Invalid terminal response selection')
            native_failure_evidence(store, source['id'])
            selected = rows[pos].get('content')
        elif selection == 'earlier-public-responses':
            selected = [r for r in rows[:pos] if r.get('type') == 'PLANNER_RESPONSE' and 'content' in r
                and r['content'] is not None and (not isinstance(r['content'], str) or r['content'].strip())]
        elif selection == 'terminal-tail':
            if pos is None:
                raise StateError('Terminal tail lacks its exact completed prefix')
            selected = rows[pos + 1:]
        elif selection == 'changed-public-rows':
            old = store.get(d['previous_outcome'])
            old_capture = old['data']['capture_artifact'] if old['kind'] == 'native_failure' else strict_json(
                store.get(old['data']['host_receipt'], 'artifact')['data']['text'])['producer_evidence']
            prior_rows = strict_json(store.get(old_capture, 'artifact')['data']['text'])['public_transcript']
            selected = [r for r in rows if r not in prior_rows and 'content' in r and r['content'] is not None
                        and (not isinstance(r['content'], str) or r['content'].strip())]
        else:
            raise StateError('Unknown retained public-content selection')
        wrapper = strict_json(response['data']['text'])
        if wrapper.get('content') != selected:
            raise StateError('Supplemental retained bytes do not equal their selected public observation')
    if origin.get('selected_content_hash') is not None and digest(selected) != origin['selected_content_hash']:
        raise StateError('Retained selected content hash differs from actual public bytes')
    return {'source': source, 'selected': selected, 'records': [store.get(r) for r in expected_refs]}


def protobuf_fields(blob: bytes) -> dict[int, list]:
    """Minimal bounded protobuf wire reader, not speculative recursive decoding."""
    def varint(offset):
        value = 0
        for shift in range(0, 70, 7):
            if offset >= len(blob):
                raise StateError('Truncated native protobuf')
            byte = blob[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, offset
        raise StateError('Oversized native protobuf integer')
    fields, offset = {}, 0
    while offset < len(blob):
        tag, offset = varint(offset)
        number, wire = tag >> 3, tag & 7
        if number == 0:
            raise StateError('Invalid native protobuf field')
        if wire == 0:
            value, offset = varint(offset)
        elif wire in {1, 5}:
            width = 8 if wire == 1 else 4
            value, offset = blob[offset:offset + width], offset + width
        elif wire == 2:
            length, offset = varint(offset)
            value, offset = blob[offset:offset + length], offset + length
        else:
            raise StateError('Unsupported native protobuf wire type')
        if offset > len(blob):
            raise StateError('Truncated native protobuf field')
        fields.setdefault(number, []).append(value)
    return fields


class NativeLogs:
    def __init__(self):
        self.root = Path.home() / '.gemini/antigravity-cli'

    def _id(self, conversation: str) -> str:
        if not isinstance(conversation, str) or not UUID.fullmatch(conversation):
            raise StateError('Expected a native conversation UUID')
        return conversation

    def transcript(self, conversation: str) -> list[dict]:
        path = self.root / 'brain' / self._id(conversation) / '.system_generated/logs/transcript_full.jsonl'
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                row = strict_json(line)
            except ValueError as error:
                raise StateError('Native transcript is incomplete; re-observe, do not restart') from error
            if not isinstance(row, dict):
                raise StateError('Unknown native transcript schema')
            rows.append({k: row[k] for k in ('step_index', 'source', 'type', 'status', 'created_at', 'content') if k in row})
        return rows

    @contextmanager
    def database(self, conversation: str):
        path = self.root / 'conversations' / (self._id(conversation) + '.db')
        if not path.is_file():
            raise NativeObservationUnavailable('Native conversation database not yet available')
        connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            yield connection
        finally:
            connection.close()

    def parents(self, child: str) -> list[str]:
        with self.database(child) as db:
            row = db.execute('SELECT data FROM trajectory_metadata_blob WHERE id=?', ('main',)).fetchone()
        if not row:
            raise StateError('Native relationship metadata is unavailable')
        fields = protobuf_fields(row[0])
        candidates = []
        # Observed relationship fields are cross-checked against the parent's
        # actual child-creation event; their undocumented names are not assumed.
        for number in (5, 6):
            for raw in fields.get(number, []):
                value = raw.decode('utf-8')
                if UUID.fullmatch(value) and value not in candidates:
                    candidates.append(value)
        return candidates

    def dispatches(self, parent: str) -> list[dict]:
        calls = []
        with self.database(parent) as db:
            rows = db.execute('SELECT idx,step_payload FROM steps WHERE step_type=15 AND status=3').fetchall()
        for index, payload in rows:
            for planner in protobuf_fields(payload).get(20, []):
                for raw_call in protobuf_fields(planner).get(7, []):
                    fields = protobuf_fields(raw_call)
                    if fields.get(2) != [b'invoke_subagent']:
                        continue
                    if len(fields.get(3, [])) != 1 or len(fields.get(1, [])) != 1:
                        raise StateError('Ambiguous native subagent call encoding')
                    arguments = strict_json(fields[3][0].decode('utf-8'))
                    if not isinstance(arguments, dict) or not isinstance(arguments.get('Subagents'), list):
                        raise StateError('Unknown native subagent argument schema')
                    calls.append({'step_index': index, 'call_id': fields[1][0].decode('utf-8'),
                                  'subagents': arguments['Subagents']})
        return calls

    def allocations(self, parent: str) -> list[dict]:
        """Join creation output to its producer call ID, never by adjacency.

        Observed generic completion profile: metadata 5/4 contains the call;
        public output 140/2/1 contains the creation result. Unknown layouts
        cannot qualify a child by borrowing another call in the same parent.
        """
        allocations = []
        with self.database(parent) as db:
            rows = db.execute('SELECT idx,step_payload FROM steps WHERE step_type=132 AND status=3').fetchall()
        for index, payload in rows:
            fields = protobuf_fields(payload)
            calls = [protobuf_fields(call) for metadata in fields.get(5, [])
                     for call in protobuf_fields(metadata).get(4, [])]
            calls = [call for call in calls if call.get(2) == [b'invoke_subagent']]
            if not calls:
                continue
            if len(calls) != 1 or len(calls[0].get(1, [])) != 1:
                raise StateError('Ambiguous native allocation call identity')
            outputs = [text.decode('utf-8') for generic in fields.get(140, [])
                       for output in protobuf_fields(generic).get(2, [])
                       for text in protobuf_fields(output).get(1, [])]
            children = created_children([{'type': 'GENERIC', 'status': 'DONE', 'content': text}
                                         for text in outputs])
            for child in children:
                allocations.append({'child': child, 'step_index': index,
                                    'call_id': calls[0][1][0].decode('utf-8')})
        return allocations


def created_children(rows: list[dict]) -> set[str]:
    children = set()
    decoder = json.JSONDecoder()
    for row in rows:
        content = row.get('content', '')
        if (row.get('type') != 'GENERIC' or row.get('status') != 'DONE'
                or not isinstance(content, str) or 'Created the following subagents:' not in content):
            continue
        for match in re.finditer(r'\{', content):
            try:
                value, _ = decoder.raw_decode(content[match.start():])
            except ValueError:
                continue
            if isinstance(value, dict) and UUID.fullmatch(value.get('conversationId', '')):
                children.add(value['conversationId'])
    return children


class NativeCapture:
    def __init__(self, campaign):
        self.c = campaign
        self.store = campaign.store
        self.tasks = Tasks(campaign)
        self.logs = NativeLogs()
        self.workspace = Path.cwd().resolve()

    def inspect_native_context(self, task: str, child: str) -> dict:
        from .native_controls import observe
        try:
            return observe(self, task, child)
        except (sqlite3.DatabaseError, TypeError, KeyError, UnicodeDecodeError) as error:
            raise StateError('Recorded native input profile is unavailable: ' + str(error)) from error

    def admit_native_context(self, task: str, child: str, observation_hash: str,
                             reason: str, checks: list[str]) -> dict:
        from .native_controls import admit
        return admit(self, task, child, observation_hash, reason, checks)

    def _substance_concern(self, source, task, run, capture, response, content, *, present=True, selection='terminal-response'):
        if not present or content is None or isinstance(content, str) and not content.strip():
            return None
        packet = self.tasks.packet(task)
        subject = self.tasks._claim_for(packet['target']) or packet['target']
        source_record = self.store.get(source)
        origin_records = list(dict.fromkeys([task, run, capture, response,
            *[source_record['data'][key] for key in ('result', 'host_receipt', 'capture_artifact', 'response_artifact') if source_record['data'].get(key)]]))
        qualifications = {}
        for event_type in ('capture-qualification', 'completion-qualification'):
            row = self.store.db.execute('SELECT payload FROM events WHERE type=? AND target=?', (event_type, run)).fetchone()
            qualifications[event_type] = json.loads(row['payload']) if row else None
        origin = {'profile': 'retained-native-substance-origin-v1', 'source_record': source,
            'source_hash': self.store.get(source)['hash'], 'task': task, 'packet_hash': packet['packet_hash'],
            'source_profile': self.store.get(source)['data'].get('profile'),
            'result_contract_profile': self.store.get(source)['data'].get('result_contract_profile'),
            'rejecting_result_contract_profile': source_record['data'].get('rejecting_result_contract_profile'),
            'proposal_contract_profile': source_record['data'].get('proposal_contract_profile'),
            'observation_selection': selection, 'selected_content_hash': digest(content),
            'producer_qualifications': qualifications,
            'attribution_scope': 'producer-recorded-public-context' if qualifications['capture-qualification']
                and qualifications['capture-qualification'].get('captured') is True else 'operator-report',
            'run': run, 'conversation_id': self.store.get(run)['data']['conversation_id'],
            'producer_records': {r: self.store.get(r)['hash'] for r in origin_records},
            'assigned_target': packet['target'], 'assigned_target_hash': packet['target_hash'],
            'capture_artifact': capture, 'response_artifact': response}
        challenge = self.c.artifact(canonical({'kind': 'unclassified-retained-mathematical-substance',
            'allegation': 'Impact and scope of this attributed retained content require independent classification',
            'mathematical_refutation': False, 'origin': origin,
            'response': {'content_present': present, 'content': content},
            'observed_capture': self.store.get(capture, 'artifact')['data']['text']}))
        finding = self.store.put('objection', {'target': subject, 'target_hash': self.store.get(subject)['hash'],
            'artifact': challenge, 'author': 'root-native-recorder',
            'finding_class': 'unclassified-retained-substance', 'mathematical_refutation': False,
            'native_origin': origin})
        self.store.decide(finding, 'open', {'reason': 'Conservative unresolved-impact boundary; not a failing mathematical verdict',
                                          'source_record': source})
        self.store.event('native-substance-finding', source, {'finding': finding, 'target': subject})
        return finding

    def _retain_tail(self, task, run, child, outcome, capture, tail):
        """A terminal row does not account for later public context/substance."""
        response = self.c.artifact(canonical({'content_present': True, 'content': tail}),
                                   'application/vnd.mathtrace.native-response+json')
        comparison = self.c.artifact(canonical({'kind': 'attributed-post-terminal-public-observation',
            'terminal_outcome': outcome, 'capture_artifact': capture, 'terminal_tail': tail,
            'mathematical_claim': 'none; post-terminal context and substance require investigation'}))
        finding = self.c.objection(run, comparison, 'root-native-recorder')
        prior = self.store.get(outcome)
        conflict = self.store.put('native_conflict', {'profile': 'attributed-terminal-tail-v1',
            'task': task, 'previous_task': task, 'target': self.tasks.packet(task)['target'],
            'previous_run': run, 'previous_outcome': outcome, 'previous_outcome_hash': prior['hash'],
            'capture_artifact': capture, 'capture_hash': self.store.get(capture)['hash'],
            'response_artifact': response, 'response_hash': self.store.get(response)['hash'],
            'comparison_artifact': comparison, 'finding': finding, 'conversation_id': child,
            'retry_authorized': False, 'mathematical_acceptance': False})
        self.store.decide(conflict, 'observed', {'reason': 'Retained post-terminal public rows', 'finding': finding})
        nonempty = [r for r in tail if 'content' in r and r['content'] is not None
                    and (not isinstance(r['content'], str) or r['content'].strip())]
        substance = self._substance_concern(conflict, task, run, capture, response, tail,
                                            present=bool(nonempty), selection='terminal-tail')
        return {'conflict': conflict, 'finding': finding, 'substance_finding': substance}

    def _retained_terminal(self, task, child):
        row = self.store.db.execute('SELECT response FROM requests WHERE id=?', ('native-capture:' + child,)).fetchone()
        if not row:
            return None
        response = json.loads(row['response'])
        if response.get('task') != task or response.get('child') != child:
            raise StateError('Retained terminal observation belongs to another task/child')
        if response['observation'] == 'terminal-protocol-failure':
            native_failure_evidence(self.store, response['failure'])
        elif response['observation'] == 'captured':
            result = self.store.get(response['result'], 'result')['data']
            run = self.store.get(result['run'], 'run')['data']
            host = strict_json(self.store.get(result['host_receipt'], 'artifact')['data']['text'])
            artifact = self.store.get(result['artifact'], 'artifact')['data']['text']
            if (result['task'] != task or run['conversation_id'] != child or response['run'] != result['run']
                    or host.get('conversation_id') != child or host.get('response') != artifact):
                raise StateError('Retained captured result does not bind the exact task/child/response')
            packet = self.store.get(task, 'task')['data']['packet']
            capture = strict_json(self.store.get(host['producer_evidence'], 'artifact')['data']['text'])
            first = next((r for r in capture['public_transcript']
                if r.get('type') == 'PLANNER_RESPONSE' and r.get('status') == 'DONE'), None)
            output = worker_result(packet, task, result['packet_hash'], artifact,
                                   profile=result.get('result_contract_profile', RESULT_CONTRACT_V1))
            qualification = self.store.db.execute("SELECT payload FROM events WHERE type='completion-qualification' "
                                                  'AND target=?', (result['run'],)).fetchone()
            if (not first or first.get('content') != artifact or host.get('status') != 'SUCCESS'
                    or capture.get('kind') != 'native-dispatch-capture'
                    or capture.get('task_id') != task or capture.get('conversation_id') != child
                    or capture.get('packet_hash') != result['packet_hash']
                    or run['task'] != task or run['packet_hash'] != result['packet_hash']
                    or self.store.get(task)['data']['packet_hash'] != digest(packet)
                    or result['target'] != packet['target'] or result['target_hash'] != packet['target_hash']
                    or not qualification or json.loads(qualification['payload']) != {'captured': True, 'result': response['result']}
                    or output['outcome'] != result['outcome'] or output.get('verdict') != result['verdict']
                    or sorted(set(output.get('checks', []))) != result['checks']):
                raise StateError('Retained captured result does not bind its actual named terminal observation')
        else:
            raise StateError('Unknown retained native terminal outcome')
        return response

    def recover(self, task: str, child: str) -> dict:
        self.store.get(task, 'task')
        response = self._retained_terminal(task, child)
        if response is None:
            raise StateError('No retained terminal observation; inspect the existing allocation, do not retry')
        run = response['run']
        outcome = self.store.get(response.get('failure', response.get('result')))
        d = outcome['data']
        refs = ([d['capture_artifact'], d['response_artifact'], d['task'], d['run']]
                if outcome['kind'] == 'native_failure' else
                [d['artifact'], d['host_receipt'], d['task'], d['run']])
        current = self.store.status(outcome['id']) not in {'withdrawn', 'rejected'} and all(self.c._scope_current(r) for r in refs)
        return {'historical_observation': response, 'source_attribution_current': current,
            'conflicts': [c['id'] for c in self.store.records('native_conflict')
                          if c['data']['previous_run'] == run and self.c.finding_blocking(c['data']['finding'])],
            'retry_authorized': False, 'mathematical_acceptance': False}

    def reserve(self, tasks: list[str], parent: str) -> dict:
        if (not isinstance(tasks, list) or not tasks or len(set(tasks)) != len(tasks)
                or any(not isinstance(t, str) or not t.strip() for t in tasks)):
            raise StateError('Reserve a nonempty list of distinct tasks')
        self.logs._id(parent)
        with self.store.transaction():
            for task in tasks:
                self.store.get(task, 'task')
                if self.store.status(task) != 'ready':
                    raise StateError('Task already dispatched or reserved; inspect existing execution before retry')
            arguments = {'Subagents': [
                {'Prompt': canonical(self.tasks.packet(task)),
                 'TypeName': 'math-' + self.tasks.packet(task)['role'],
                 'Role': 'Math ' + self.tasks.packet(task)['role'],
                 'Model': 'inherit', 'Workspace': 'inherit'} for task in tasks]}
            request = self.store.put('dispatch', {'tasks': list(tasks), 'parent': parent,
                'tool': 'invoke_subagent', 'arguments': arguments})
            self.store.decide(request, 'reserved', {'host_execution_observed': False})
            for task in tasks:
                self.store.decide(task, 'awaiting-native', {'dispatch': request,
                    'reason': 'Reserved before native dispatch; not proof that a child is running'})
        return {'tasks': list(tasks), 'dispatch': request, 'arguments': arguments,
                'status': 'awaiting-native', 'retry_without_observation': False}

    def inspect(self, dispatch: str) -> dict:
        """Recover known allocation handles without dispatching or judging liveness."""
        request = self.store.get(dispatch, 'dispatch')['data']
        parent = request['parent']
        calls = [call for call in self.logs.dispatches(parent)
                 if canonical(call['subagents']) == canonical(request['arguments']['Subagents'])]
        allocations = self.logs.allocations(parent)
        recovered = []
        for call in calls:
            for allocation in allocations:
                if allocation['call_id'] != call['call_id']:
                    continue
                matching = []
                input_error = None
                try:
                    observed = task_input_observation(self.logs.transcript(allocation['child']), parent)
                    matching = [task for task in request['tasks']
                                if canonical(observed['packet']) == canonical(self.tasks.packet(task))]
                except (ValueError, StateError) as error:
                    input_error = str(error)
                recovered.append({'child': allocation['child'], 'call_id': call['call_id'],
                                  'task': matching[0] if len(matching) == 1 else None,
                                  **({'input_error': input_error} if input_error else {})})
        return {'dispatch': dispatch, 'parent': parent,
                'matching_calls': [call['call_id'] for call in calls], 'allocations': recovered,
                'duplicate_dispatch_observed': len(calls) > 1,
                'retry_authorized': False, 'host_terminal_state': 'not-established',
                'note': 'Missing or unmatched observations do not establish that execution never started or stopped.'}

    def collect(self, task: str, child: str) -> dict:
        retained = self._retained_terminal(task, child)
        try:
            return self._collect(task, child)
        except (NativeObservationUnavailable, FileNotFoundError):
            if retained is not None:
                return self._historical_reply(task, child, retained)
            raise

    def _historical_reply(self, task, child, retained):
        recovery = self.recover(task, child)
        if not recovery['conflicts']:
            return retained
        return {**retained, 'historical_recovery': True, 'retained_conflicts': recovery['conflicts'],
            'source_attribution_current': recovery['source_attribution_current'],
            'retry_authorized': False, 'mathematical_acceptance': False}

    def _collect(self, task: str, child: str) -> dict:
        packet = self.tasks.packet(task)
        retained_terminal = self._retained_terminal(task, child)
        requests = [r for r in self.store.records('dispatch') if task in r['data']['tasks']]
        if len(requests) > 1:
            raise StateError('Task has ambiguous native reservations')
        request = requests[0] if requests else None
        role = 'math-' + packet['role']
        role_path = f'agents/{role}/agent.md'
        expected_role = runtime_files()[role_path]
        workspace = self.workspace
        installed = workspace / '.agents' / role_path
        if not installed.is_file() or installed.read_text(encoding='utf-8') != expected_role:
            if retained_terminal is not None:
                return self._historical_reply(task, child, retained_terminal)
            raise StateError('Owned native role definition is missing or differs from the renderer')
        child_rows = self.logs.transcript(child)
        if not child_rows:
            if retained_terminal is not None:
                return self._historical_reply(task, child, retained_terminal)
            return {'observation': 'unavailable', 'child': child, 'retry_authorized': False}
        terminal_position = next((i for i, r in enumerate(child_rows)
            if r.get('type') == 'PLANNER_RESPONSE' and r.get('status') == 'DONE'), None)
        prefix = child_rows[:terminal_position + 1] if terminal_position is not None else child_rows
        try:
            input_observation = task_input_observation(child_rows,
                request['data']['parent'] if request else None)
        except ValueError as error:
            raise StateError('Native input is not the exact exported packet') from error
        if canonical(input_observation['packet']) != canonical(packet):
            raise StateError('Native child received different or additional packet data')
        matches = []
        for parent in self.logs.parents(child):
            if request and parent != request['data']['parent']:
                continue
            if input_observation['header'] and input_observation['header']['sender'] != parent:
                continue
            parent_rows = self.logs.transcript(parent)
            if not parent_rows:
                raise NativeObservationUnavailable('Parent public transcript is unavailable; retain canonical history without retry')
            if child not in created_children(parent_rows):
                continue
            allocations = [a for a in self.logs.allocations(parent) if a['child'] == child]
            if len(allocations) != 1:
                raise StateError('No unique producer allocation binds this child to a call')
            allocation = allocations[0]
            for call in self.logs.dispatches(parent):
                if call['call_id'] != allocation['call_id']:
                    continue
                if request and canonical(call['subagents']) != canonical(request['data']['arguments']['Subagents']):
                    raise StateError('Observed native call differs from the reserved dispatch arguments')
                for specification in call['subagents']:
                    try:
                        supplied = strict_json(specification.get('Prompt', ''))
                    except ValueError:
                        continue
                    if canonical(supplied) != canonical(packet):
                        continue
                    if (specification.get('TypeName') != role or specification.get('Model', 'inherit') != 'inherit'
                            or specification.get('Workspace', 'inherit') != 'inherit'):
                        raise StateError('Observed native role, model or workspace differs from the task policy')
                    matches.append({'parent': parent, 'call_id': call['call_id'], 'step_index': call['step_index'],
                                    'allocation_step_index': allocation['step_index'],
                                    'requested_type': specification['TypeName'],
                                    'model_argument': specification.get('Model'),
                                    'workspace_argument': specification.get('Workspace')})
        if len(matches) != 1:
            raise StateError('No unique producer-recorded dispatch binds this child to the task')
        responses = [r for r in child_rows if r.get('type') == 'PLANNER_RESPONSE']
        completed = [r for r in responses if r.get('status') == 'DONE']
        final = completed[0] if completed else responses[-1] if responses else None
        complete = bool(completed)
        terminal_position = next((i for i, r in enumerate(child_rows)
            if r.get('type') == 'PLANNER_RESPONSE' and r.get('status') == 'DONE'), None)
        tail = child_rows[terminal_position + 1:] if terminal_position is not None else []
        unexpected = [r for i, r in enumerate(child_rows)
            if i != input_observation['position'] and (r.get('type') != 'PLANNER_RESPONSE'
                or (terminal_position is not None and i > terminal_position))]
        capture = {'kind': 'native-dispatch-capture', 'task_id': task, 'packet_hash': packet['packet_hash'],
            'dispatch_request': request['id'] if request else None,
            'conversation_id': child, 'host': 'antigravity', 'declared_tools': [], 'declared_inherited_history': False,
            'producer': 'antigravity-cli-local-transcript-and-conversation-db',
            'schema_profile': ('2026-09-08' if input_observation['profile'] == 'raw-user-input-v1'
                               else '2026-10-04-parent-message-v1'), 'parent_dispatch': matches[0],
            'input_observation': input_observation,
            'requested_role_type': role,
            'installed_role_definition_hash': digest(expected_role),
            'role_definition_observation': 'current-installed-file-matches-owned-renderer',
            'host_instantiated_role_definition_hash': None,
            'effective_host_tool_policy': None,
            'complete_host_context_observed': False,
            'recorded_child_input_count': 1,
            'unaccounted_public_event_count': len(unexpected),
            'terminal_tail_count': len(tail), 'terminal_tail': tail,
            'qualification_scope': 'producer-recorded-dispatch-and-public-task-context',
            'public_transcript': child_rows,
            'limits': ['Not a cryptographic host attestation', 'Hidden host instructions are not observable',
                       'Installed role bytes are observed locally, not attested as the bytes instantiated by the host',
                       'Declared tool/history policy is not proof of effective hidden host capabilities',
                       'Unaccounted public events, when present, are recorded as exposure and disqualify blind review']}
        # Historical captures retain their original evidence/holds. A current
        # parent-message profile cannot borrow a clean transcript as admission.
        context_admission = None
        context_error = None
        retained_profile = None
        if retained_terminal is not None:
            from .native_controls import retained_context
            retained_profile = retained_context(self.c, self.store.get(retained_terminal['run'], 'run')).get('native_context_profile')
        if retained_terminal is None or retained_profile:
            from .native_controls import observe, admission, PROFILE
            if complete:
                try:
                    recorded_inputs = observe(self, task, child)
                    context_admission = admission(self, task, child, recorded_inputs)
                    context_error = None if context_admission else 'Exact recorded native bootstrap has no current root admission'
                    capture['recorded_native_inputs'] = recorded_inputs
                except (StateError, ValueError, sqlite3.DatabaseError, KeyError, UnicodeDecodeError) as error:
                    context_error = str(error)
            capture['native_context_profile'] = PROFILE
            capture['native_context_admission'] = context_admission
            capture['native_context_hold_reason'] = context_error
        output, protocol_error = None, None
        if complete:
            # Attribution above is mandatory. Only this pure result-contract
            # exception can classify an observed DONE response as invalid.
            # Transport, producer, database and run-state errors still propagate.
            try:
                output = worker_result(packet, task, packet['packet_hash'], final.get('content'))
            except ResultProtocolError as error:
                protocol_error = str(error)
        with self.store.transaction():
            known_terminal = complete or retained_terminal is not None
            key = ('native-capture:' if known_terminal else 'native-observation:') + child
            fingerprint = digest({'task': task, 'child': child, 'capture': capture})
            if not known_terminal:
                key += ':' + fingerprint
            retained = self.store.db.execute('SELECT fingerprint,response FROM requests WHERE id=?', (key,)).fetchone()
            if known_terminal and retained and retained['fingerprint'] != fingerprint:
                prior = json.loads(retained['response'])
                original_id = prior.get('failure', prior.get('result'))
                original = self.store.get(original_id)
                original_capture = (original['data']['capture_artifact'] if original['kind'] == 'native_failure' else
                    strict_json(self.store.get(original['data']['host_receipt'])['data']['text'])['producer_evidence'])
                old_capture = strict_json(self.store.get(original_capture)['data']['text'])
                # Today's installed-file observation does not rewrite the role
                # bytes originally observed or reinterpret a historical outcome.
                causal = ('task_id', 'packet_hash', 'conversation_id', 'parent_dispatch', 'producer',
                          'schema_profile', 'requested_role_type', 'public_transcript',
                          'unaccounted_public_event_count', 'recorded_child_input_count',
                          'recorded_native_inputs', 'native_context_profile', 'native_context_admission',
                          'native_context_hold_reason')
                if all(capture.get(k) == old_capture.get(k) for k in causal):
                    return prior
                conflict_key = 'native-terminal-conflict:' + child + ':' + fingerprint
                old_conflict = self.store.request(conflict_key, fingerprint)
                if old_conflict is not None:
                    return old_conflict
                evidence = self.c.artifact(canonical(capture))
                substantive_rows = [r for r in child_rows if r not in old_capture['public_transcript']
                    and 'content' in r and r['content'] is not None
                    and (not isinstance(r['content'], str) or r['content'].strip())]
                response_artifact = self.c.artifact(canonical({'content_present': bool(substantive_rows),
                    'content': substantive_rows}), 'application/vnd.mathtrace.native-response+json')
                comparison = self.c.artifact(canonical({'kind': 'attributed-terminal-observation-conflict',
                    'previous_observation': old_capture, 'conflicting_observation': capture,
                    'previous_outcome': original_id, 'mathematical_claim': 'none; producer attribution requires investigation'}))
                finding = self.c.objection(original['data']['run'], comparison, 'root-native-recorder')
                conflict = self.store.put('native_conflict', {'profile': 'attributed-terminal-conflict-v1',
                    'task': task, 'previous_task': prior['task'], 'target': packet['target'],
                    'previous_run': original['data']['run'], 'previous_outcome': original_id,
                    'previous_outcome_hash': original['hash'], 'capture_artifact': evidence,
                    'capture_hash': self.store.get(evidence)['hash'], 'response_artifact': response_artifact,
                    'response_hash': self.store.get(response_artifact)['hash'], 'comparison_artifact': comparison,
                    'finding': finding, 'conversation_id': child, 'retry_authorized': False,
                    'mathematical_acceptance': False})
                self.store.decide(conflict, 'observed', {'reason': 'Retained conflicting terminal observation', 'finding': finding})
                substance = self._substance_concern(conflict, task, original['data']['run'], evidence,
                    response_artifact, substantive_rows, present=bool(substantive_rows), selection='changed-public-rows')
                response = {'observation': 'terminal-conflict', 'conflict': conflict, 'finding': finding,
                    'substance_finding': substance,
                    'task': task, 'child': child, 'run': original['data']['run'],
                    'previous_outcome': original_id, 'retry_authorized': False, 'mathematical_acceptance': False}
                self.store.finish_request(conflict_key, fingerprint, response)
                return response
            previous = self.store.request(key, fingerprint)
            if previous is not None:
                return previous
            evidence = self.c.artifact(canonical(capture))
            existing = [r for r in self.store.records('run') if r['data']['conversation_id'] == child]
            if existing:
                if len(existing) != 1 or existing[0]['data']['task'] != task:
                    raise StateError('Native conversation already bound to another task')
                run = existing[0]['id']
            else:
                run = self.tasks._start_captured(task, child, host='antigravity', dispatch_evidence=evidence,
                                                 tools=[], inherited_history=False)
            if unexpected:
                self.tasks.expose(run, 'unknown', evidence, 'Unaccounted native child tool/system events during this task')
            if context_error:
                self.tasks.expose(run, 'unknown', evidence, 'Native recorded-input qualification unavailable: ' + context_error)
            if request:
                bindings = self.store.get(request['id'])['data']['tasks']
                observed = {r['data']['task'] for r in self.store.records('run')}
                self.store.decide(request['id'], 'allocated' if set(bindings) <= observed else 'partially-allocated',
                                  {'observed_task': task, 'child': child, 'evidence': evidence})
            if not complete:
                response = {'observation': 'no-completed-response', 'child': child, 'run': run, 'retry_authorized': False}
                self.store.finish_request(key, fingerprint, response)
                return response
            if protocol_error is not None:
                if self.store.status(run) != 'running' or self.store.status(task) != 'running':
                    raise StateError('Terminal protocol failure cannot replace an already finished run')
                artifact = self.c.artifact(canonical({'content_present': 'content' in final,
                    'content': final.get('content')}), 'application/vnd.mathtrace.native-response+json')
                raw_content = final.get('content')
                raw_binding = ({'encoding': 'utf-8', 'size': len(raw_content.encode('utf-8')),
                    'sha256': hashlib.sha256(raw_content.encode('utf-8')).hexdigest()}
                    if isinstance(raw_content, str) else None)
                failure = self.store.put('native_failure', {
                    'profile': 'attributed-terminal-result-failure-v1', 'target': packet['target'],
                    'result_contract_profile': RESULT_CONTRACT_PROFILE,
                    'target_hash': packet['target_hash'], 'task': task, 'packet_hash': packet['packet_hash'],
                    'run': run, 'conversation_id': child, 'capture_artifact': evidence,
                    'capture_hash': self.store.get(evidence)['hash'], 'response_artifact': artifact,
                    'response_hash': self.store.get(artifact)['hash'], 'protocol_error': protocol_error,
                    'raw_response_binding': raw_binding,
                    'terminal_public_response': {'step_index': final['step_index'], 'status': 'DONE',
                        'created_at': final.get('created_at')},
                    'qualification_scope': capture['qualification_scope'],
                    'unaccounted_public_event_count': len(unexpected), 'limitations': capture['limits'],
                    'mathematical_acceptance': False, 'retry_authorized': False,
                    'negative_evidence_disposition': 'unassessed; format failure never dismisses substance'})
                reason = {'failure': failure, 'evidence': evidence,
                          'reason': 'Observed attributed terminal public response violates the result contract'}
                self.store.decide(failure, 'observed', reason)
                self.store.decide(run, 'protocol-failed', reason)
                self.store.decide(task, 'protocol-failed', reason)
                self.store.event('native-protocol-failure', run, reason)
                substance = self._substance_concern(failure, task, run, evidence, artifact,
                                                   final.get('content'), present='content' in final)
                if substance is None:
                    earlier = [r for r in prefix[:-1] if r.get('type') == 'PLANNER_RESPONSE'
                        and 'content' in r and r['content'] is not None
                        and (not isinstance(r['content'], str) or r['content'].strip())]
                    if earlier:
                        earlier_artifact = self.c.artifact(canonical({'content_present': True, 'content': earlier}),
                            'application/vnd.mathtrace.native-response+json')
                        substance = self._substance_concern(failure, task, run, evidence, earlier_artifact, earlier,
                                                           selection='earlier-public-responses')
                response = {'observation': 'terminal-protocol-failure', 'task': task, 'child': child,
                    'substance_finding': substance,
                    'run': run, 'failure': failure, 'retry_authorized': False,
                    'mathematical_acceptance': False, 'negative_evidence_disposition': 'unassessed'}
                if tail:
                    response['terminal_tail_observation'] = self._retain_tail(task, run, child, failure, evidence, tail)
                self.store.finish_request(key, fingerprint, response)
                return response
            artifact = self.c.artifact(final['content'])
            receipt = self.c.artifact(canonical({'conversation_id': child, 'status': 'SUCCESS',
                'response': final['content'], 'producer_evidence': evidence, 'completed_at': final.get('created_at')}))
            result = self.tasks._finish_captured(run, artifact, receipt, outcome=output.get('outcome'),
                verdict=output.get('verdict'), checks=output.get('checks'))
            failing_review = None
            if output['outcome'] == 'review' and output['verdict'] == 'fail':
                provenance = self.tasks.review_provenance(run, packet['target'], 'fail', artifact, output['checks'])
                failing_review = self.c.review(packet['target'], child, run, 'fail', artifact, output['checks'],
                                               exposure=provenance['exposure'])
            response = {'observation': 'captured', 'task': task, 'child': child, 'run': run, 'result': result,
                        'failing_review': failing_review,
                        'qualification_scope': 'producer-recorded-dispatch-and-public-task-context',
                        'effective_host_isolation_verified_by_capture': False,
                        'mathematical_acceptance': False}
            if output['outcome'] != 'review':
                # Register proposed records or quarantine exact contract failures
                # at intake. Ingestion has no mathematical acceptance authority.
                from .orchestration import Orchestration
                response['ingestion'] = Orchestration(self.c).ingest(result)
            if tail:
                response['terminal_tail_observation'] = self._retain_tail(task, run, child, result, evidence, tail)
            self.store.finish_request(key, fingerprint, response)
            return response
