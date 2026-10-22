import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_research
import formal_fixture

from mathtrace.evidence import Evidence
from mathtrace.context import Tasks
from mathtrace.store import StateError


class EvidenceTests(unittest.TestCase):
    setUp = test_research.ResearchTests.setUp
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review

    def test_actual_computation_is_observation_and_requires_source_review(self):
        target = self.claim('All natural n satisfy P(n)')
        source = self.r.artifact('import json\nprint(json.dumps({"checked": 100, "all_passed": True}))')
        evidence = Evidence(self.r)
        plan = evidence.experiment(target, source, 'n from 0 to 99 only', author='computationalist')
        with self.assertRaises(StateError):
            evidence.run_experiment(plan)
        self.review(plan, ['execution-scope', 'source-integrity'])
        receipt = self.store.get(evidence.run_experiment(plan))['data']
        self.assertEqual(json.loads(receipt['result']['stdout'])['checked'], 100)
        self.assertEqual(receipt['result']['exit_code'], 0)
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_timeout_is_preserved_without_positive_evidence(self):
        source = self.r.artifact('import time\ntime.sleep(3)')
        evidence = Evidence(self.r)
        plan = evidence.experiment(self.claim(), source, 'bounded experiment', author='worker')
        self.review(plan, ['execution-scope', 'source-integrity'])
        receipt = self.store.get(evidence.run_experiment(plan, timeout=0.05))['data']
        self.assertTrue(receipt['result']['timed_out'])
        self.assertIsNone(receipt['result']['exit_code'])

    def formal_plan(self):
        target = self.claim('True')
        source = self.r.artifact('theorem t : True := by trivial')
        evidence = Evidence(self.r)
        plan = evidence.formal_plan(target, source, 't', 'True', author='formalizer')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        return evidence, plan, target

    def toolchain_fixture(self):
        return formal_fixture.toolchain(self.r)

    def test_missing_formal_tool_creates_no_receipt(self):
        evidence, plan, _ = self.formal_plan()
        with self.assertRaisesRegex(StateError, 'missing'):
            evidence.run_lean(plan, toolchain=self.toolchain_fixture())
        self.assertEqual(self.store.records('formal_receipt'), [])

    def test_mocked_checker_receipt_needs_independent_fidelity_before_formal_use(self):
        # Tests receipt/gate logic at an explicitly mocked process boundary, not
        # Lean correctness. A real Lean integration run is still required.
        evidence, plan, target = self.formal_plan()
        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan)
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            receipt = evidence.run_lean(plan, toolchain=self.toolchain_fixture())
        self.assertEqual(self.store.status(receipt), 'checked')
        inference = self.r.inference(target, [], self.proof, 'author', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        with self.assertRaisesRegex(StateError, 'fidelity evidence'):
            self.r.promote(inference, expected=self.store.revision, request_id='formal')
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.r.promote(inference, expected=self.store.revision, request_id='formal')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'supported')
        self.r.withdraw(receipt, 'checker defect discovered')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'unsupported')

    def test_mocked_sorry_axiom_is_not_accepted_despite_zero_exit(self):
        evidence, plan, _ = self.formal_plan()
        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan)
        report = json.loads(formal_fixture.blob_bytes(execution["semantic_output"]))
        axiom = {**report["semantics"]["declarations"][0], "name": formal_fixture.exact_name("sorryAx"), "display_name": "sorryAx", "values": [], "detail": {"kind": "axiom"}}
        report["semantics"]["declarations"].append(axiom)
        report["semantics"]["axioms"] = [axiom["name"]]
        execution["semantic_output"] = formal_fixture.blob(json.dumps(report).encode())
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            receipt = evidence.run_lean(plan, toolchain=self.toolchain_fixture())
        self.assertEqual(self.store.status(receipt), 'failed')

    def test_zero_exit_without_compiled_output_is_rejected(self):
        evidence, plan, _ = self.formal_plan()
        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan)
        execution["compiled_output"] = None
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            receipt = evidence.run_lean(plan, toolchain=self.toolchain_fixture())
        self.assertEqual(self.store.status(receipt), 'failed')

    def test_formal_plan_cannot_add_axiom_or_mislabel_disproof(self):
        evidence, _, target = self.formal_plan()
        with self.assertRaisesRegex(StateError, 'enlarge'):
            evidence.formal_plan(target, self.proof, 't', 'True', author='author', allowed_axioms=['MyUnprovedAxiom'])

    def test_successful_elaboration_cannot_mask_failed_kernel_replay(self):
        evidence, plan, _ = self.formal_plan()
        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan)
        execution["replay"]["exit_code"] = 1
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            receipt = evidence.run_lean(plan, toolchain=self.toolchain_fixture())
        self.assertEqual(self.store.status(receipt), 'failed')
        self.assertIsNotNone(self.store.get(receipt)['data']['compiled_artifact'])
        from mathtrace.campaign import Campaign
        from mathtrace.orchestration import Orchestration
        self.assertTrue(any(a.get('receipt') == receipt and a['action'] == 'assess-formal-failure'
                            for a in Orchestration(Campaign(self.store)).next_actions()['actions']))

    def test_libraries_are_bound_before_review_and_cannot_be_added_or_changed_at_execution(self):
        root = Path(self.temp.name) / 'library'
        root.mkdir()
        (root / 'Library.olean').write_bytes(b'reviewed fixture bytes')
        evidence, _, target = self.formal_plan()
        source = self.r.artifact('theorem t : True := by trivial')
        plan = evidence.formal_plan(target, source, 't', 'True', author='formalizer', library_paths=[str(root)])
        tasks = Tasks(self.r)
        task = tasks.create('referee', plan, checks=['formal-source-integrity'], mandate='Review the fixed import environment')
        projected = tasks.packet(task)['records'][plan]['data']['libraries'][0]
        self.assertNotIn('root', projected)
        self.assertNotIn('files', projected)
        self.assertTrue(projected['manifest_omitted'])
        self.assertEqual(projected['file_count'], 1)
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        pinned = {'executable': sys.executable}
        toolchain = self.toolchain_fixture()

        with patch('mathtrace.evidence.verify_toolchain', return_value=pinned), patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean') as execute:
            with self.assertRaisesRegex(StateError, 'cannot change reviewed library'):
                evidence.run_lean(plan, toolchain=toolchain, library_paths=[])
            (root / 'injected.so').write_bytes(b'new unreviewed plugin')
            with self.assertRaisesRegex(StateError, 'bytes changed after plan'):
                evidence.run_lean(plan, toolchain=toolchain)
            execute.assert_not_called()

    def test_withdrawn_sources_are_not_executed(self):
        evidence = Evidence(self.r)
        source = self.r.artifact('raise RuntimeError("must not run")')
        plan = evidence.experiment(self.claim(), source, 'finite test', author='author')
        self.review(plan, ['execution-scope', 'source-integrity'])
        self.r.withdraw(source, 'source review invalidated')
        with self.assertRaises(StateError):
            evidence.run_experiment(plan)
        evidence, plan, _ = self.formal_plan()
        self.r.withdraw(self.store.get(plan)['data']['source'], 'original formal source withdrawn')
        with self.assertRaises(StateError):
            evidence.run_lean(plan, toolchain='never-invoked')

    def test_formal_toolchain_objection_and_withdrawal_suspend_current_evidence_and_execution(self):
        evidence, plan, target = self.formal_plan()
        toolchain = self.toolchain_fixture()
        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan)
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            receipt = evidence.run_lean(plan, toolchain=toolchain)
        inference = self.r.inference(target, [], self.proof, 'author', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.r.promote(inference, expected=self.store.revision, request_id='formal-toolchain-test')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'supported')

        # Register blocking objection against toolchain
        objection = self.r.objection(toolchain, self.r.artifact('Compiler flaw discovered'), 'adversary')
        self.assertEqual(self.store.status(objection), 'open')
        # Formal-only target becomes unsupported without rewriting historical receipt/inference
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'unsupported')
        self.assertEqual(self.store.status(receipt), 'checked')
        self.assertEqual(self.store.status(inference), 'accepted')

        # While blocked, run_lean fails closed before checker execution
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean') as execute, patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            with self.assertRaisesRegex(StateError, 'current scope'):
                evidence.run_lean(plan, toolchain=toolchain)
            execute.assert_not_called()

        # Exact infrastructure adjudication can restore historical receipt eligibility.
        response = self.r.artifact('Self-contained assessment of the exact compiler-flaw report')
        case = self.r.adjudication(objection, response, disposition='dismissed', author='root')
        self.review(case, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'supported')
        self.assertEqual(self.store.status(receipt), 'checked')

        # Withdrawing toolchain also suspends formal evidence and blocks run_lean
        self.r.withdraw(toolchain, 'retired defective toolchain')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'unsupported')
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean') as execute, patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            with self.assertRaisesRegex(StateError, 'current scope'):
                evidence.run_lean(plan, toolchain=toolchain)
            execute.assert_not_called()

    def test_formal_plan_and_execution_reject_collection_coercion(self):
        contract = self.r.contract("For x in R, x=x", [], completion="Proof", allowed_axioms=["propext"])
        claim = self.r.claim("x=x", contract)
        source = self.r.artifact("theorem t : True := by trivial")
        evidence = Evidence(self.r)
        asm = self.r.assumption("x is real")
        root = Path(self.temp.name) / "test_lib"
        root.mkdir()
        (root / "Test.olean").write_bytes(b"bytes")

        # 1. allowed_axioms tests
        # Valid when contract permits it:
        valid_plan = evidence.formal_plan(claim, source, "t", "True", author="formalizer", allowed_axioms=["propext"])
        self.assertEqual(self.store.get(valid_plan)['data']['allowed_axioms'], ["propext"])

        for invalid in [{"propext": False}, "propext"]:
            with self.assertRaisesRegex(StateError, "allowed_axioms must be an exact list"):
                evidence.formal_plan(claim, source, "t", "True", author="formalizer", allowed_axioms=invalid)
        for invalid in [[123], [""]]:
            with self.assertRaisesRegex(StateError, "entries must be nonempty strings"):
                evidence.formal_plan(claim, source, "t", "True", author="formalizer", allowed_axioms=invalid)
        with self.assertRaisesRegex(StateError, "duplicate"):
            evidence.formal_plan(claim, source, "t", "True", author="formalizer", allowed_axioms=["propext", "propext"])
        with self.assertRaisesRegex(StateError, "sorryAx"):
            evidence.formal_plan(claim, source, "t", "True", author="formalizer", allowed_axioms=["sorryAx"])

        # 2. assumptions tests
        for invalid in [{asm: False}, 123, "not a list"]:
            with self.assertRaisesRegex(StateError, "assumptions must be an exact list"):
                evidence.formal_plan(claim, source, "t", "True", author="formalizer", assumptions=invalid)

        # 3. library_paths tests in formal_plan
        for invalid in [{str(root): False}, 123, str(root)]:
            with self.assertRaisesRegex(StateError, "library_paths must be an exact list"):
                evidence.formal_plan(claim, source, "t", "True", author="formalizer", library_paths=invalid)

        # 4. library_paths tests in run_lean
        self.review(valid_plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        toolchain = self.toolchain_fixture()
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            for invalid in [{str(root): False}, 123, str(root)]:
                with self.assertRaisesRegex(StateError, "library_paths must be an exact list"):
                    evidence.run_lean(valid_plan, toolchain=toolchain, library_paths=invalid)
