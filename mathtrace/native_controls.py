"""Root-admitted recorded native inputs, never an OS isolation attestation."""
from __future__ import annotations

import json
import hashlib
from .research import nonempty
from .store import StateError, canonical, digest

PROFILE = 'agy-1.2.16-recorded-input-no-tools-v1'
TOOL_SCHEMA_HASH = 'f507caca58ccd7f5841cb281a0166620545e03f629fd1d628bd5103d96c11f32'
CHECKS = {'task-neutral-bootstrap', 'no-mathematical-history-or-advice', 'operational-conflicts-assessed'}


def one(fields, key):
    values = fields.get(key, [])
    if len(values) != 1:
        raise StateError('Native input profile requires one exact field')
    return values[0]


def text(fields, key):
    value = one(fields, key)
    if not isinstance(value, bytes):
        raise StateError('Native input field is not text')
    return value.decode('utf-8')


def role_text(role_file):
    body = role_file.split('---', 2)[2].strip()
    title, body = body.split('\n\n', 1)
    title = title.removeprefix('# ')
    return f'<{title}>\n{body.rstrip()}\n</{title}>'


def fingerprints(fields, selected):
    return {str(k): [{'size': len(v), 'sha256': hashlib.sha256(v).hexdigest()}
                    if isinstance(v, bytes) else {'scalar': v} for v in fields[k]]
            for k in sorted(selected) if k in fields}


def observe(controller, task, child):
    """Select only static/input fields; generated reasoning is never decoded."""
    from .native_capture import protobuf_fields, task_input_observation, strict_json
    from .native import runtime_files
    wire_fields = protobuf_fields
    def protobuf_fields(blob):
        if not isinstance(blob, bytes):
            raise StateError('Native input profile contains a nonmessage wire field')
        return wire_fields(blob)
    packet = controller.tasks.packet(task)
    rows = controller.logs.transcript(child)
    finals = [r for r in rows if r.get('type') == 'PLANNER_RESPONSE' and r.get('status') == 'DONE']
    if len(rows) != 2 or len(finals) != 1 or rows[-1] != finals[0]:
        raise StateError('Recorded-input qualification requires only one input and terminal public response')
    parents = controller.logs.parents(child)
    bindings = []
    for parent in parents:
        inputs = task_input_observation(rows, parent)
        if canonical(inputs['packet']) != canonical(packet):
            continue
        allocations = [a for a in controller.logs.allocations(parent) if a['child'] == child]
        if len(allocations) != 1:
            continue
        for call in controller.logs.dispatches(parent):
            if call['call_id'] != allocations[0]['call_id']:
                continue
            specifications = [s for s in call['subagents'] if strict_json(s.get('Prompt', '')) == packet]
            if len(specifications) != 1:
                continue
            specification = specifications[0]
            if (specification.get('TypeName') != 'math-' + packet['role']
                    or specification.get('Model', 'inherit') != 'inherit'
                    or specification.get('Workspace', 'inherit') != 'inherit'):
                continue
            reservations = [r for r in controller.store.records('dispatch') if task in r['data']['tasks']]
            if reservations and (len(reservations) != 1 or reservations[0]['data']['parent'] != parent
                    or canonical(reservations[0]['data']['arguments']['Subagents']) != canonical(call['subagents'])):
                continue
            bindings.append({'parent': parent, 'call_id': call['call_id'], 'allocation': allocations[0]})
    if len(bindings) != 1:
        raise StateError('Recorded input lacks one exact task/call/allocation binding')
    with controller.logs.database(child) as db:
        generated = db.execute('SELECT idx,data FROM gen_metadata ORDER BY idx').fetchall()
        if len(generated) != 1:
            raise StateError('Recorded-input profile requires one complete generator observation')
        calls = []
        # The attempt itself, including a failed/denied attempt, is disqualifying.
        for idx, payload in db.execute('SELECT idx,step_payload FROM steps WHERE step_type=15'):
            for planner in protobuf_fields(payload).get(20, []):
                for call in protobuf_fields(planner).get(7, []):
                    f = protobuf_fields(call)
                    calls.append({'step_index': idx, 'name': text(f, 2), 'call_id': text(f, 1)})
        if calls:
            raise StateError('Native worker attempted tools; recorded-input independence is unavailable')
    outer = protobuf_fields(generated[0][1])
    if set(outer) != {1, 2, 3, 4, 8}:
        raise StateError('Unknown native generator envelope profile')
    g = protobuf_fields(one(outer, 1))
    if set(g) - {1, 2, 3, 4, 8, 9, 10, 11, 12, 16, 17, 19, 20}:
        raise StateError('Unknown native generator input fields')
    system = text(g, 1)
    sections = []
    for raw in g.get(16, []):
        f = protobuf_fields(raw)
        if set(f) - {1, 2, 4, 6, 7}:
            raise StateError('Unknown native static section fields')
        sections.append({'name': text(f, 1), 'text': text(f, 2),
                         'metadata_fingerprints': fingerprints(f, {4, 6, 7})})
    names = [s['name'] for s in sections]
    allowed = {'user_information', 'user_rules', 'skills', 'messaging', 'artifacts',
               'guidelines', 'communication_style', 'subagent_reminder'}
    if (not sections or len(names) != len(set(names))
            or set(names[1:]) - allowed or system != '\n'.join(s['text'] for s in sections)):
        raise StateError('Native static system context is incomplete or has unknown sections')
    expected_role = role_text(runtime_files()['agents/math-' + packet['role'] + '/agent.md'])
    if sections[0]['text'].replace('\r\n', '\n') != expected_role:
        raise StateError('Instantiated native role body differs from the owned renderer')
    tools = []
    for raw in g.get(8, []):
        f = protobuf_fields(raw)
        if set(f) != {1, 2, 3}:
            raise StateError('Unknown native tool declaration fields')
        tools.append({'name': text(f, 1), 'description': text(f, 2), 'schema': strict_json(text(f, 3))})
    if ([t['name'] for t in tools] != ['send_message', 'manage_task']
            or digest(tools) != TOOL_SCHEMA_HASH):
        raise StateError('Native input has an unknown or stronger tool schema surface')
    messages = g.get(2, [])
    if len(messages) != 2:
        raise StateError('Native generator context has extra or missing messages')
    incoming, public = (protobuf_fields(m) for m in messages)
    if (set(incoming) - {2, 3, 4} or set(public) - {2, 3, 11, 18, 20}
            or incoming.get(2) != [1] or public.get(2) != [2]
            or text(incoming, 3) != rows[0]['content'] or text(public, 3) != rows[-1]['content']):
        raise StateError('Recorded generator inputs/response differ from the exact public interval')
    # No output field except the already-public text at3 is read or exported.
    observation = {'profile': PROFILE, 'task': task, 'child': child,
        'packet_hash': packet['packet_hash'], 'binding': bindings[0],
        'system_text': system, 'sections': sections, 'tool_schemas': tools,
        'input_text': rows[0]['content'], 'public_response': rows[-1]['content'],
        'recorded_tool_attempts': [], 'generator_index': generated[0][0],
        'noninput_metadata_fingerprints': {
            'incoming': fingerprints(incoming, {4})},
        'scope': 'producer-recorded-input-and-no-recorded-tool-use',
        'residual_controls_physically_available': True, 'dispatcher_or_os_denial_verified': False,
        'complete_hidden_context_verified': False}
    return {**observation, 'observation_hash': digest(observation)}


def admit(controller, task, child, observation_hash, reason, checks):
    if (not isinstance(checks, list) or any(not isinstance(c, str) for c in checks)
            or set(checks) != CHECKS or len(checks) != len(CHECKS)):
        raise StateError('Root must assess every exact native bootstrap duty')
    reason = nonempty(reason, 'native bootstrap assessment reason')
    with controller.store.transaction():
        if any(r['data']['conversation_id'] == child and controller.store.status(r['id']) != 'running'
               for r in controller.store.records('run')):
            raise StateError('Native context admission cannot upgrade an already captured run')
        observed = observe(controller, task, child)
        if observed['observation_hash'] != observation_hash:
            raise StateError('Native context changed since root inspection')
        artifact = controller.c.artifact(canonical({'profile': 'root-native-input-admission-v1',
            'observation': observed, 'reason': reason, 'checks': sorted(checks),
            'mathematical_acceptance': False}))
        controller.store.event('native-context-admission', task,
            {'child': child, 'artifact': artifact, 'observation_hash': observation_hash})
        return {'artifact': artifact, 'observation_hash': observation_hash, 'mathematical_acceptance': False}


def admission(controller, task, child, observed):
    if (observed.get('task') != task or observed.get('child') != child
            or observed.get('packet_hash') != controller.tasks.packet(task)['packet_hash']):
        return None
    rows = controller.store.db.execute("SELECT payload FROM events WHERE type='native-context-admission' AND target=? ORDER BY seq DESC", (task,)).fetchall()
    for row in rows:
        data = json.loads(row['payload'])
        if data.get('child') != child or data.get('observation_hash') != observed['observation_hash']:
            continue
        artifact = controller.store.get(data['artifact'], 'artifact')
        value = json.loads(artifact['data']['text'])
        if (value.get('profile') == 'root-native-input-admission-v1' and value.get('observation') == observed
                and value.get('checks') == sorted(CHECKS) and value.get('reason')
                and value.get('mathematical_acceptance') is False):
            return artifact['id']
    return None


def retained_context_record(research, execution):
    """Use the completion's capture after a prior nonterminal observation."""
    d = execution['data']
    source = research.store.get(d['dispatch_evidence'], 'artifact')
    results = [r for r in research.store.records('result') if r['data']['run'] == execution['id']]
    failures = [r for r in research.store.records('native_failure') if r['data']['run'] == execution['id']]
    if results and failures or len(results) > 1 or len(failures) > 1:
        raise StateError('Native context has ambiguous terminal evidence')
    if failures:
        source = research.store.get(failures[0]['data']['capture_artifact'], 'artifact')
    if results:
        result = results[0]['data']
        receipt = json.loads(research.store.get(result['host_receipt'], 'artifact')['data']['text'])
        if (receipt.get('conversation_id') != d['conversation_id']
                or receipt.get('response') != research.store.get(result['artifact'], 'artifact')['data']['text']):
            raise StateError('Native completion context differs from actual result')
        if receipt.get('producer_evidence'):
            source = research.store.get(receipt['producer_evidence'], 'artifact')
    return source


def retained_context(research, execution):
    return json.loads(retained_context_record(research, execution)['data']['text'])


def retained_admission(research, execution):
    """Reconstruct the exact retained admission; current host files are irrelevant."""
    d = execution['data']
    try:
        context_record = retained_context_record(research, execution)
        capture = json.loads(context_record['data']['text'])
        if capture.get('native_context_profile') != PROFILE:
            return False
        artifact = research.store.get(capture['native_context_admission'], 'artifact')
        value = json.loads(artifact['data']['text'])
        observed = value['observation']
        task = research.store.get(d['task'], 'task')['data']
        expected_hash = digest({k: v for k, v in observed.items() if k != 'observation_hash'})
        if (value.get('profile') != 'root-native-input-admission-v1' or value.get('checks') != sorted(CHECKS)
                or not isinstance(value.get('reason'), str) or not value['reason'].strip()
                or value.get('mathematical_acceptance') is not False
                or observed.get('profile') != PROFILE or observed.get('observation_hash') != expected_hash
                or observed.get('task') != d['task'] or observed.get('child') != d['conversation_id']
                or observed.get('packet_hash') != d['packet_hash'] or task['packet_hash'] != d['packet_hash']
                or capture.get('recorded_native_inputs') != observed
                or capture.get('native_context_admission') != artifact['id']
                or capture.get('native_context_profile') != PROFILE
                or observed['input_text'] != capture['input_observation']['row']['content']
                or observed['binding']['parent'] != capture['parent_dispatch']['parent']
                or observed['binding']['call_id'] != capture['parent_dispatch']['call_id']
                or observed['binding']['allocation']['child'] != d['conversation_id']):
            return False
        event = research.store.db.execute("SELECT payload FROM events WHERE type='native-context-admission' AND target=?", (d['task'],)).fetchall()
        expected = {'child': d['conversation_id'], 'artifact': artifact['id'], 'observation_hash': expected_hash}
        return (any(json.loads(e['payload']) == expected for e in event)
                and research._scope_current(artifact['id']) and research._scope_current(context_record['id']))
    except (StateError, ValueError, KeyError, TypeError):
        return False
