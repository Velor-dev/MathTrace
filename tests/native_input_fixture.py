"""Synthetic stored static inputs; no claim of actual host independence."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from mathtrace.native import runtime_files
from mathtrace.native_controls import role_text, CHECKS


def install(case, *, admit=True, system_extra='', extra_message=False, schema_extra=False, role_crlf=False, platform_guides=False):
    from test_native_capture import field
    rows=case.recorder.logs.transcript(case.child)
    role=role_text(runtime_files()['agents/math-'+case.packet['role']+'/agent.md'])
    if role_crlf:role=role.replace('\n','\r\n')
    sections=[('Mathematical '+case.packet['role'],role),('guidelines','<guidelines>Operational fixture only</guidelines>')]
    if platform_guides:
        sections.append(('skills','<skills>Benign persistent Antigravity platform guide: CLI flags and customization documentation only. No project/math history or task-specific advice.</skills>'))
    system='\n'.join(t for _,t in sections)+system_extra
    tools=json.loads(Path(__file__).with_name('native_input_schemas.json').read_text(encoding='utf-8'))
    if schema_extra:tools.append({'name':'view_file','description':'Read files','schema':{}})
    generator=field(1,system)
    for name,text in sections:generator+=field(16,field(1,name)+field(2,text))
    for t in tools:generator+=field(8,field(1,t['name'])+field(2,t['description'])+field(3,json.dumps(t['schema'])))
    # Message role fields are varint. Generated private bytes are opaque and omitted.
    generator+=field(2,b'\x10\x01'+field(3,rows[0]['content']))
    generator+=field(2,b'\x10\x02'+field(3,rows[-1]['content'])+field(11,'DO NOT EXPORT PRIVATE THOUGHT FIXTURE'))
    if extra_message:generator+=field(2,b'\x10\x02'+field(3,'Prior author history'))
    blob=field(1,generator)+field(2,'x')+field(3,b'')+field(4,'metadata')+field(8,b'')
    p=case.recorder.logs.root/'conversations'/(case.child+'.db')
    with closing(sqlite3.connect(p)) as db:
        db.execute('CREATE TABLE IF NOT EXISTS gen_metadata(idx INTEGER PRIMARY KEY,data BLOB)')
        db.execute('CREATE TABLE IF NOT EXISTS steps(idx INTEGER,step_type INTEGER,status INTEGER,step_payload BLOB)')
        db.execute('INSERT OR REPLACE INTO gen_metadata VALUES(0,?)',(blob,))
        db.commit()
    if admit:
        observed=case.recorder.inspect_native_context(case.task,case.child)
        return case.recorder.admit_native_context(case.task,case.child,observed['observation_hash'],
            'Synthetic bookkeeping fixture; exact bootstrap has no mathematics/history/advice and no operational conflict.',sorted(CHECKS))
