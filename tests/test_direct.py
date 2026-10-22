"""Real native process checks and synthetic version-aware evidence admission."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import formal_fixture as fixture
import test_research
from mathtrace.backend import EXECUTION_PROTOCOL, invoke, mode
from mathtrace.direct import run, record
from mathtrace.evidence import Evidence
from mathtrace.execution import Executions
from mathtrace.formal import MODE_RECEIPT_VERSION, receipt_evidence, process_passed
from mathtrace.store import StateError
from mathtrace.toolchain import execution_target
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks


class DirectProcessTests(unittest.TestCase):
    def compute(self, source, timeout=5):
        return invoke({'source': source, 'inputs': {'value': 7}, 'timeout': timeout,
                       'execution_mode': 'direct', 'execution_protocol': EXECUTION_PROTOCOL})

    def test_native_inputs_environment_and_no_optional_backend(self):
        with patch('mathtrace.sandbox.invoke', side_effect=AssertionError('No sandbox probe')), \
             patch.dict(os.environ, {'PYTHONPATH': 'bogus', 'LEAN_PATH':'bogus', 'LD_PRELOAD':'bogus'}):
            result = self.compute("import json,os; print(json.load(open('inputs.json'))['value']); print('LEAN_PATH' in os.environ)")
        self.assertEqual(result['stdout'].splitlines(), ['7', 'False'])
        self.assertTrue(process_passed(result, 'direct'))
        self.assertFalse(process_passed(result))

    def test_bounded_output_timeout_and_nonzero(self):
        value = self.compute("import sys; sys.stdout.write('x'*(4*1024*1024+1))")
        self.assertTrue(value['output_limited'])
        self.assertEqual(len(value['stdout']), 4*1024*1024)
        self.assertTrue(self.compute('import time; time.sleep(30)', .15)['timed_out'])
        self.assertEqual(self.compute('raise SystemExit(7)')['exit_code'], 7)

    def test_native_descendant_cleanup_and_unicode_workdir(self):
        with tempfile.TemporaryDirectory(prefix='mathtrace space ü-') as directory:
            result = run([sys.executable, '-I', '-c',
                "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print('parent',flush=True); time.sleep(30)"],
                Path(directory), .4)
        self.assertTrue(result['timed_out'])
        self.assertIn('parent', result['stdout'])

    def test_unknown_mode_and_no_fallback(self):
        with self.assertRaises(StateError):
            mode('automatic')
        with patch('mathtrace.sandbox.invoke', side_effect=StateError('unavailable')), \
             patch('mathtrace.direct.invoke') as direct:
            with self.assertRaises(StateError):
                invoke({'execution_mode':'bubblewrap','timeout':1})
            direct.assert_not_called()

    def test_uncertain_cleanup_never_publishes_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            from mathtrace.store import digest
            request = {'source':'pass','inputs':{},'timeout':1,
                       'execution_mode':'direct','execution_protocol':EXECUTION_PROTOCOL}
            journal = {'directory':str(Path(directory)/'attempt'), 'execution':'test', 'request_hash':digest(request)}
            with patch('mathtrace.direct.run', side_effect=RuntimeError('teardown uncertain')):
                with self.assertRaises(RuntimeError):
                    record({**request,'_journal':journal})
            self.assertTrue((Path(journal['directory'])/'started.json').is_file())
            self.assertFalse((Path(journal['directory'])/'terminal.json').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows job assignment')
    def test_windows_control_setup_failure_does_not_start_workload(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'must-not-exist'
            command = [sys.executable, '-I', '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()']
            with patch('mathtrace.direct.WindowsJob.assign', side_effect=OSError('assignment failed')):
                with self.assertRaises(OSError):
                    run(command,Path(directory),5)
            self.assertFalse(marker.exists())

    def test_target_mapping(self):
        for host, arch, marker in [('win32','AMD64','windows'),('linux','aarch64','linux_aarch64'),
                                   ('darwin','arm64','darwin_aarch64'),('darwin','x86_64','darwin')]:
            with patch('sys.platform',host), patch('platform.machine',return_value=arch):
                self.assertEqual(execution_target()[0],marker)
        with patch('sys.platform','win32'),patch('platform.machine',return_value='ARM64'):
            with self.assertRaises(StateError):
                execution_target()

    def test_cli_uses_same_json_selection(self):
        import contextlib
        import io
        from mathtrace.cli import main
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory)/'state.sqlite'
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['init','--db',str(database)]),0)
            # Invalid selector fails through the ordinary JSON dispatch before downloading.
            source = Path(directory)/'install.json'
            source.write_text(json.dumps({'version':'v4.30.0','execution_mode':'auto'}))
            with contextlib.redirect_stderr(output):
                self.assertEqual(main(['install_lean','--db',str(database),'--input',str(source)]),2)
            self.assertIn('execution_mode',output.getvalue())

    def test_resolution_rejects_traversal_root_alias_and_wrong_order(self):
        from mathtrace.resolution import normalized_resolution
        roots = {'platform':'windows','stage':'C:\\native stage',
                 'paths':{'/toolchain':'C:\\native stage\\toolchain','/replay':'C:\\native stage\\replay'}}
        for path in ['C:\\native stage\\replay\\..\\toolchain\\Init.olean',
                     'C:\\native stage\\replay-other\\Main.olean','relative\\Main.olean']:
            with self.subTest(path=path),self.assertRaises(StateError):
                normalized_resolution({'reference_search_roots':[path], 'reference':[],'candidate':[]},
                                      {},roots,0)
        roots['paths']['/replay'] = 'C:\\arbitrary'
        with self.assertRaises(StateError):
            normalized_resolution({}, {}, roots, 0)


class ModeFormalTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    review = test_research.ResearchTests.review
    claim = test_research.ResearchTests.claim

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.e = Evidence(self.r)
        self.target = self.claim('True')
        self.plan = self.e.formal_plan(self.target,self.r.artifact('theorem t : True := True.intro'),
                                      't','True',author='formalizer')
        self.review(self.plan,['formal-source-integrity','formal-target-fidelity','foundations'])
        self.tc = fixture.toolchain(self.r)

    def check(self, observed=None, selected='direct'):
        observed = fixture.mode_execution(self.r,self.plan,selected) if observed is None else observed
        def runner(request, *, journal):
            result = test_research.recorded_result(observed,journal,mode=selected)
            producer = result['_producer']['producer']
            producer['stage'] = observed.get('staged_roots',{}).get('stage')
            from mathtrace.store import digest
            result['_producer']['producer_hash'] = digest(producer)
            return result
        with patch('mathtrace.evidence.invoke',side_effect=runner), \
             patch('mathtrace.evidence.verify_toolchain',return_value=fixture.PINNED), \
             patch('mathtrace.toolchain.execution_target',return_value=('synthetic',None)):
            return self.e.run_lean(self.plan,toolchain=self.tc,execution_mode=selected)

    def test_new_direct_and_sandbox_receipts_preserve_qualification(self):
        for selected in ('direct','bubblewrap'):
            with self.subTest(selected=selected):
                if selected == 'bubblewrap':
                    self.setUpNewPlan()
                receipt = self.check(selected=selected)
                self.assertEqual(self.store.status(receipt),'checked')
                receipt_evidence(self.store,receipt)
                self.review(receipt,['formal-receipt','formal-target-fidelity','foundations'])
                self.assertTrue(self.r._formal_current(receipt))
                source = self.store.get(self.plan)['data']['source']
                inference = self.r.inference(self.target, [], source, 'formalizer',
                    assurance='formal', formal_receipt=receipt)
                self.review(inference,['validity','scope','dependencies'])
                self.r.promote(inference,expected=self.store.revision,request_id='mode-'+selected)
                candidate = self.r.freeze(self.target,source,author='fixture',assurance='machine-checked')
                self.assertTrue(self.r.candidate_current(candidate))
                packet = Tasks(self.r).packet(Tasks(self.r).create('fidelity-auditor',receipt,
                    checks=['formal-target-fidelity'],mandate='Inspect exact evidence'))
                self.assertIn('execution_assurance',packet['records'][receipt]['data'])
                compiled = self.store.get(receipt)['data']['compiled_artifact']
                self.r.withdraw(compiled,'withdraw exact object')
                self.assertFalse(self.r._formal_current(receipt))
                self.assertFalse(self.r.candidate_current(candidate))

    def setUpNewPlan(self):
        self.plan = self.e.formal_plan(self.target,self.r.artifact('theorem u : True := True.intro'),
                                      'u','True',author='formalizer')
        self.review(self.plan,['formal-source-integrity','formal-target-fidelity','foundations'])

    def test_direct_cannot_fabricate_namespace_or_lose_root_binding(self):
        observed = fixture.mode_execution(self.r,self.plan)
        observed['result']['namespace_setup'] = {'child-pid':1}
        receipt = self.check(observed)
        self.assertEqual(self.store.status(receipt),'failed')
        self.assertFalse(self.r._formal_current(receipt))

    def test_mode_replay_cannot_switch_backend(self):
        receipt = self.check()
        with self.assertRaises(StateError):
            self.e.run_lean(self.plan,toolchain=self.tc,execution_mode='bubblewrap')
        self.assertEqual(self.e.recover_execution(self.store.get(receipt)['data']['execution'])['receipt'],receipt)
