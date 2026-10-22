import json
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch

from mathtrace.context import Tasks
from mathtrace.native_controls import CHECKS
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError, canonical
import test_native_capture as capture_fixture
from test_native_capture import field
from native_input_fixture import install


class NativeControlsTests(unittest.TestCase):
    setUp = capture_fixture.NativeCaptureTests.setUp
    tearDown = capture_fixture.NativeCaptureTests.tearDown
    claim = capture_fixture.NativeCaptureTests.claim
    review = capture_fixture.NativeCaptureTests.review
    transcript = capture_fixture.NativeCaptureTests.transcript
    producer_fixture = capture_fixture.NativeCaptureTests.producer_fixture

    def capture(self):
        result=self.recorder.collect(self.task,self.child)
        Orchestration(self.r).ingest(result['result'])
        return result

    def test_exact_admission_qualifies_without_exporting_private_output(self):
        self.producer_fixture(); install(self)
        result=self.capture()
        self.assertEqual(self.store.records('exposure'),[])
        self.r.promote(self.inference,expected=self.store.revision,request_id='qualified')
        artifact=self.store.get(self.store.get(result['run'])['data']['dispatch_evidence'])['data']['text']
        self.assertNotIn('DO NOT EXPORT PRIVATE',artifact)
        self.assertIn('residual_controls_physically_available',artifact)

    def test_missing_metadata_or_admission_is_held(self):
        self.producer_fixture()
        result=self.capture()
        self.assertTrue(self.store.records('exposure'))
        with self.assertRaises(StateError):self.r.promote(self.inference,expected=self.store.revision,request_id='missing')
        with self.assertRaises(StateError):
            self.recorder.admit_native_context(self.task,self.child,'unknown','No retrospective upgrade',sorted(CHECKS))

    def test_complete_unadmitted_inputs_still_hold(self):
        self.producer_fixture(); install(self,admit=False)
        result=self.capture()
        self.assertTrue(self.store.records('exposure'))
        self.assertIsNone(self.store.get(result['run'])['data']['native_context_admission'])

    def test_unaccounted_system_extra_message_and_extra_schema_reject(self):
        self.producer_fixture()
        for kw in ({'system_extra':'\nOther referee passed'},{'extra_message':True},{'schema_extra':True}):
            install(self,admit=False,**kw)
            with self.assertRaises(StateError):self.recorder.inspect_native_context(self.task,self.child)

    def test_unfinished_tool_attempt_rejects_without_public_tool_event(self):
        self.producer_fixture(); install(self,admit=False)
        p=self.recorder.logs.root/'conversations'/(self.child+'.db')
        with closing(sqlite3.connect(p)) as db:
            call=field(1,'tool-attempt')+field(2,'send_message')+field(3,'{}')
            db.execute('INSERT INTO steps VALUES(1,15,1,?)',(field(20,field(7,call)),));db.commit()
        with self.assertRaisesRegex(StateError,'attempted tools'):self.recorder.inspect_native_context(self.task,self.child)
        self.capture();self.assertTrue(self.store.records('exposure'))

    def test_missing_static_snapshot_is_not_empty_surface(self):
        self.producer_fixture();install(self,admit=False)
        p=self.recorder.logs.root/'conversations'/(self.child+'.db')
        with closing(sqlite3.connect(p)) as db:
            db.execute('INSERT INTO gen_metadata VALUES(1,?)',(field(1,b''),));db.commit()
        with self.assertRaises(StateError):self.recorder.inspect_native_context(self.task,self.child)

    def test_withdrawn_admission_invalidates_review_preserves_history(self):
        self.producer_fixture();admitted=install(self)
        captured=self.capture()
        self.r.promote(self.inference,expected=self.store.revision,request_id='before')
        self.r.withdraw(admitted['artifact'],'Bootstrap neutrality challenged')
        with self.assertRaises(StateError):self.r._reviews(self.inference,{'validity','scope','dependencies'})
        self.assertEqual(self.recorder.collect(self.task,self.child),captured)
        self.assertFalse(self.recorder.recover(self.task,self.child)['source_attribution_current'])

    def test_stale_inspection_and_new_evidence_do_not_clear_old_hold(self):
        self.producer_fixture();install(self,admit=False)
        observed=self.recorder.inspect_native_context(self.task,self.child)
        with self.assertRaises(StateError):
            self.recorder.admit_native_context(self.task,self.child,'wrong-hash','Exact assessment',sorted(CHECKS))
        captured=self.capture()
        before=self.store.records('exposure')
        with self.assertRaises(StateError):
            self.recorder.admit_native_context(self.task,self.child,observed['observation_hash'],'Too late',sorted(CHECKS))
        self.assertEqual(before,self.store.records('exposure'))

    def test_changed_input_metadata_after_capture_retains_conflict(self):
        self.producer_fixture();install(self)
        first=self.capture()
        install(self,admit=False,system_extra='\nLater contamination')
        changed=self.recorder.collect(self.task,self.child)
        self.assertEqual(changed['observation'],'terminal-conflict')
        self.assertEqual(changed['previous_outcome'],first['result'])
        self.assertTrue(self.recorder.recover(self.task,self.child)['conflicts'])

    def test_admission_findings_block_current_review(self):
        self.producer_fixture();admitted=install(self)
        self.capture()
        self.r.objection(admitted['artifact'],self.r.artifact('Exact bootstrap contains an undisclosed method hint'),'critic')
        with self.assertRaises(StateError):self.r._reviews(self.inference,{'validity','scope','dependencies'})

    def test_canonical_recovery_does_not_need_current_host_metadata(self):
        self.producer_fixture();install(self)
        captured=self.capture()
        with patch.object(self.recorder.logs,'database',side_effect=FileNotFoundError()):
            recovered=self.recorder.recover(self.task,self.child)
        self.assertEqual(recovered['historical_observation'],captured)
        self.assertTrue(recovered['source_attribution_current'])

    def test_early_nonterminal_capture_does_not_prevent_terminal_admission(self):
        self.producer_fixture(complete=False)
        first=self.recorder.collect(self.task,self.child)
        self.assertEqual(first['observation'],'no-completed-response')
        self.assertEqual(self.store.records('exposure'),[])
        self.producer_fixture();install(self)
        captured=self.capture()
        self.assertEqual(captured['run'],first['run'])
        self.r.promote(self.inference,expected=self.store.revision,request_id='after-early-inspect')

    def test_withdrawn_admission_blocks_informed_adjudicator_too(self):
        finding=self.r.objection(self.target,self.r.artifact('Synthetic allegation'),'critic')
        case=self.r.adjudication(finding,self.r.artifact('Exact response'),disposition='dismissed',author='root')
        self.task=Tasks(self.r).create('adjudicator',case,independence='informed',
            checks=['finding-scope','counterargument','dismissed'],mandate='Assess the synthetic response')
        self.packet=Tasks(self.r).packet(self.task)
        self.producer_fixture();admitted=install(self)
        self.capture()
        self.assertTrue(self.r._review_condition(case,{'finding-scope','counterargument','dismissed'})['current'])
        self.r.withdraw(admitted['artifact'],'Input bootstrap challenged')
        self.assertFalse(self.r._review_condition(case,{'finding-scope','counterargument','dismissed'})['current'])

    def test_nonmessage_wire_field_retains_attributed_terminal_with_hold(self):
        self.producer_fixture();install(self,admit=False)
        p=self.recorder.logs.root/'conversations'/(self.child+'.db')
        with closing(sqlite3.connect(p)) as db:
            # Outer field1 is a scalar, not the required nested generator message.
            db.execute('UPDATE gen_metadata SET data=?',(b'\x08\x01'+field(2,'x')+field(3,b'')+field(4,'metadata')+field(8,b''),));db.commit()
        result=self.capture()
        self.assertEqual(result['observation'],'captured')
        self.assertTrue(self.store.records('exposure'))

    def test_legacy_running_observation_gets_terminal_profile_gate(self):
        self.producer_fixture(complete=False)
        # Explicit pre-H2 recorder seam: the running record has no new profile.
        evidence=self.r.artifact(canonical({'kind':'native-dispatch-capture','task_id':self.task,
            'packet_hash':self.packet['packet_hash'],'conversation_id':self.child,'host':'antigravity',
            'declared_tools':[],'declared_inherited_history':False}))
        run=Tasks(self.r)._start_captured(self.task,self.child,host='antigravity',dispatch_evidence=evidence,
            tools=[],inherited_history=False)
        self.producer_fixture();admitted=install(self)
        captured=self.capture()
        self.assertEqual(captured['run'],run)
        self.assertEqual(self.recorder.collect(self.task,self.child),captured)
        self.assertEqual(self.recorder.recover(self.task,self.child)['historical_observation'],captured)
        self.assertTrue(self.r._review_condition(self.inference,{'validity','scope','dependencies'})['current'])
        self.r.withdraw(admitted['artifact'],'No migration bypass')
        self.assertFalse(self.r._review_condition(self.inference,{'validity','scope','dependencies'})['current'])
        self.r.withdraw(run,'Historical run withdrawal')
        self.assertEqual(self.recorder.collect(self.task,self.child),captured)
        self.assertFalse(self.recorder.recover(self.task,self.child)['source_attribution_current'])

    def test_terminal_capture_dependency_survives_early_observation(self):
        self.producer_fixture(complete=False)
        first=self.recorder.collect(self.task,self.child)
        self.producer_fixture();install(self)
        captured=self.capture()
        result=self.store.get(captured['result'])['data']
        receipt=json.loads(self.store.get(result['host_receipt'])['data']['text'])
        self.assertNotEqual(receipt['producer_evidence'],self.store.get(first['run'])['data']['dispatch_evidence'])
        self.r.withdraw(receipt['producer_evidence'],'Terminal producer evidence withdrawn')
        self.assertFalse(self.r._review_condition(self.inference,{'validity','scope','dependencies'})['current'])
        self.assertFalse(self.recorder.recover(self.task,self.child)['source_attribution_current'])

    def test_legacy_running_protocol_failure_replays_without_false_conflict(self):
        self.producer_fixture(complete=False)
        evidence=self.r.artifact(canonical({'kind':'native-dispatch-capture','task_id':self.task,
            'packet_hash':self.packet['packet_hash'],'conversation_id':self.child,'host':'antigravity',
            'declared_tools':[],'declared_inherited_history':False}))
        Tasks(self.r)._start_captured(self.task,self.child,host='antigravity',dispatch_evidence=evidence,
            tools=[],inherited_history=False)
        self.producer_fixture()
        rows=self.recorder.logs.transcript(self.child);rows[-1]['content']='Invalid public terminal output'
        self.transcript(self.child,rows);install(self,admit=False)
        captured=self.recorder.collect(self.task,self.child)
        self.assertEqual(captured['observation'],'terminal-protocol-failure')
        self.assertEqual(self.recorder.collect(self.task,self.child),captured)
        self.assertEqual(self.recorder.recover(self.task,self.child)['conflicts'],[])
        self.r.withdraw(captured['run'],'Historical failure run withdrawal')
        self.assertEqual(self.recorder.collect(self.task,self.child),captured)
        self.assertFalse(self.recorder.recover(self.task,self.child)['source_attribution_current'])

    def test_admission_lookup_cannot_borrow_another_task_or_child(self):
        from mathtrace.native_controls import admission
        self.producer_fixture();admitted=install(self)
        observed=self.recorder.inspect_native_context(self.task,self.child)
        other=Tasks(self.r).create('referee',self.inference,checks=self.packet['checks'],mandate='Different exact work identity')
        with self.store.transaction():
            self.store.event('native-context-admission',other,{'child':self.child,'artifact':admitted['artifact'],
                'observation_hash':observed['observation_hash']})
        self.assertIsNone(admission(self.recorder,other,self.child,observed))
        self.assertIsNone(admission(self.recorder,self.task,'33333333-3333-4333-8333-333333333333',observed))

    def test_owned_role_crlf_transport_preserves_raw_exact_input(self):
        self.producer_fixture();install(self,role_crlf=True)
        observed=self.recorder.inspect_native_context(self.task,self.child)
        self.assertIn('\r\n',observed['sections'][0]['text'])
        self.capture()
        self.assertTrue(self.r._review_condition(self.inference,{'validity','scope','dependencies'})['current'])

    def test_benign_platform_guide_presence_does_not_contaminate_admitted_inputs(self):
        self.producer_fixture();install(self,platform_guides=True)
        self.capture()
        self.assertEqual(self.store.records('exposure'),[])
        self.assertTrue(self.r._review_condition(self.inference,{'validity','scope','dependencies'})['current'])
