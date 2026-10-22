"""High-information evidence/coverage negatives at a synthetic producer seam."""
import copy
import json
import unittest
import uuid
from unittest.mock import patch

import formal_fixture as fixture
import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.evidence import Evidence
from mathtrace.formal import (SemanticGraph, blob_bytes, compiled_bundle, validate_report,
                             receipt_evidence, semantic_view, validate_view, exact_name)
from mathtrace.store import StateError, canonical, digest


class FormalTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.evidence = Evidence(self.r)
        self.tasks = Tasks(self.r)
        self.target = self.claim('True')
        self.plan = self.evidence.formal_plan(self.target,
            self.r.artifact('theorem t : True := True.intro'), 't', 'True', author='formalizer')
        self.review(self.plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        self.toolchain = fixture.toolchain(self.r)

    def run_check(self, observed=None):
        observed = fixture.execution(self.r, self.plan) if observed is None else observed
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(observed)), \
                patch('mathtrace.evidence.verify_toolchain', return_value=fixture.PINNED):
            return self.evidence.run_lean(self.plan, toolchain=self.toolchain)

    def native_review(self, task, verdict='pass'):
        """Synthetic public capture; no host or mathematical assessment occurs."""
        packet = self.tasks.packet(task)
        conversation = 'synthetic-' + uuid.uuid4().hex
        capture = self.r.artifact(json.dumps({'kind': 'native-dispatch-capture', 'task_id': task,
            'packet_hash': packet['packet_hash'], 'conversation_id': conversation, 'host': 'antigravity',
            'declared_tools': [], 'declared_inherited_history': False}))
        run = self.tasks._start_captured(task, conversation, host='antigravity', dispatch_evidence=capture,
                                         tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': packet['packet_hash'], 'outcome': 'review',
            'verdict': verdict, 'checks': packet['checks'], 'reasoning': 'Synthetic coverage bookkeeping'})
        artifact = self.r.artifact(output)
        completion = self.r.artifact(json.dumps({'conversation_id': conversation, 'status': 'SUCCESS', 'response': output}))
        self.tasks._finish_captured(run, artifact, completion, outcome='review', verdict=verdict, checks=packet['checks'])
        return run, artifact

    def test_checked_report_overrides_diagnostic_stdout_and_excludes_it_from_packets(self):
        observed = fixture.execution(self.r, self.plan)
        observed['result']['stdout'] = 'untrusted prior verdict text; depends on axioms [sorryAx]'
        observed['replay']['stderr'] = 'untrusted prior reasoning text'
        receipt = self.run_check(observed)
        self.assertEqual(self.store.status(receipt), 'checked')
        self.assertEqual(self.store.get(receipt)['data']['axioms'], [])
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        self.assertTrue(self.r._formal_current(receipt))
        task = self.tasks.create('fidelity-auditor', receipt, checks=['formal-target-fidelity'], mandate='Assess exact semantics')
        packet = canonical(self.tasks.packet(task))
        self.assertNotIn('untrusted prior', packet)
        self.assertNotIn('source_reviews', packet)
        self.assertNotIn('root-checker-execution', packet)

    def test_missing_inspect_only_and_mismatched_report_cannot_qualify(self):
        mutations = ('missing', 'inspection', 'symbol', 'profile', 'helper', 'resolution')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                observed = fixture.execution(self.r, self.plan)
                report = json.loads(blob_bytes(observed['semantic_output']))
                if mutation == 'missing':
                    observed['semantic_output'] = None
                elif mutation == 'inspection':
                    report['verification_mode'] = 'inspect'
                elif mutation == 'symbol':
                    report['semantics']['target'] = exact_name('other')
                elif mutation == 'profile':
                    report['primitive_profile'] = 'unsupported'
                elif mutation == 'helper':
                    observed['verification_binding']['helper_sha256'] = '0' * 64
                else:
                    observed['resolved_inputs']['candidate'][1]['parts']['olean']['sha256'] = '0' * 64
                if mutation != 'missing':
                    observed['semantic_output'] = fixture.blob(json.dumps(report).encode())
                # Each subcase is an independent plan/execution, rather than an
                # implicit retry after a terminal attempt.
                if mutation != mutations[0]:
                    self.plan = self.evidence.formal_plan(self.target,
                        self.r.artifact('theorem t : True := True.intro'), 't', 'True', author='formalizer')
                    self.review(self.plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
                    # Bind the mutated observation to the new exact plan first.
                    fresh = fixture.execution(self.r, self.plan)
                    if mutation == 'helper':
                        fresh['verification_binding']['helper_sha256'] = '0' * 64
                    elif mutation == 'resolution':
                        fresh['resolved_inputs']['candidate'][1]['parts']['olean']['sha256'] = '0' * 64
                    else:
                        report = json.loads(blob_bytes(fresh['semantic_output']))
                        if mutation == 'inspection': report['verification_mode'] = 'inspect'
                        elif mutation == 'symbol': report['semantics']['target'] = exact_name('other')
                        elif mutation == 'profile': report['primitive_profile'] = 'unsupported'
                        fresh['semantic_output'] = fixture.blob(json.dumps(report).encode())
                    observed = fresh
                receipt = self.run_check(observed)
                self.assertEqual(self.store.status(receipt), 'failed')
                self.assertFalse(self.r._formal_current(receipt))
                # Retained malformed evidence remains inspectable/diagnosable.
                self.tasks.create('fidelity-auditor', receipt, checks=['formal-receipt'], mandate='Diagnose failure')

    def test_malformed_part_is_failed_receipt_without_false_terminal_retry(self):
        observed = fixture.execution(self.r, self.plan)
        observed['compiled_parts'] = ['wrong shape']
        observed['compiled_output']['encoding'] = 'text'
        receipt = self.run_check(observed)
        self.assertEqual(self.store.status(receipt), 'failed')
        self.assertIsNone(self.store.get(receipt)['data']['compiled_artifact'])
        self.assertEqual(self.run_check(observed), receipt)

    def test_terminal_receipt_identity_cannot_be_copied_by_a_matching_manifest(self):
        receipt = self.run_check()
        data = self.store.get(receipt)['data']
        with self.store.transaction():
            counterfeit = self.store.put('formal_receipt', copy.deepcopy(data))
            self.store.decide(counterfeit, 'checked', {'reason': 'Synthetic imported duplicate'})
        with self.assertRaisesRegex(StateError, 'attribute'):
            receipt_evidence(self.store, counterfeit)
        self.assertFalse(self.r._formal_current(counterfeit))
        self.assertEqual(receipt_evidence(self.store, receipt)['report']['verification_mode'], 'checked-target')

    def test_all_formal_artifacts_and_terminal_observation_are_frozen_and_withdrawable(self):
        receipt = self.run_check()
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        inference = self.r.inference(self.target, [], self.proof, 'prover', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='modern-formal')
        candidate = self.r.freeze(self.target, self.proof, author='prover', assurance='machine-checked')
        evidence = receipt_evidence(self.store, receipt)
        self.assertTrue(set(evidence['records']).issubset(self.store.get(candidate)['data']['manifest']))
        self.r.withdraw(evidence['observation'], 'Terminal evidence attribution withdrawn')
        self.assertFalse(self.r.candidate_current(candidate))
        self.assertEqual(self.r.claim_state(self.target, policy='formal-only')['state'], 'unsupported')
        self.assertEqual(self.store.status(receipt), 'checked')

    def test_incomplete_pass_cannot_be_repaired_retroactively_by_blind_expansion(self):
        receipt = self.run_check()
        capsule = self.store.get(receipt)['data']['semantic_artifact']
        report = json.loads(self.store.get(capsule)['data']['text'])
        small_view = semantic_view(report, max_chars=1800)
        self.assertLessEqual(len(canonical(small_view)), 1800)
        self.assertFalse(small_view['statement_complete'])
        with patch('mathtrace.context.semantic_view', return_value=small_view):
            task = self.tasks.create('fidelity-auditor', receipt, checks=['formal-target-fidelity'], mandate='Assess exact compiled target')
        run, artifact = self.native_review(task)
        with self.assertRaisesRegex(StateError, 'complete compiled statement'):
            self.tasks.review_provenance(run, receipt, 'pass', artifact, ['formal-target-fidelity'])
        selectors = list(SemanticGraph(report['semantics']).declarations)
        with self.assertRaisesRegex(StateError, 'expansion budget'):
            self.tasks.expand_semantics(task, capsule, selectors, 'Budget cannot shorten required units', max_chars=1800)
        expanded = self.tasks.expand_semantics(task, capsule, selectors, 'Private root rationale with peer verdict')
        self.assertNotIn('peer verdict', canonical(self.tasks.packet(expanded)))
        self.assertEqual(self.tasks.packet(expanded)['independence'], 'blind')
        self.assertNotEqual(self.tasks.packet(task)['packet_hash'], self.tasks.packet(expanded)['packet_hash'])
        with self.assertRaisesRegex(StateError, 'complete compiled statement'):
            self.tasks.review_provenance(run, receipt, 'pass', artifact, ['formal-target-fidelity'])
        new_run, new_artifact = self.native_review(expanded)
        self.assertEqual(self.tasks.review_provenance(new_run, receipt, 'pass', new_artifact,
            ['formal-target-fidelity'])['exposure'], 'independent')
        proof_task = self.tasks.expand_semantics(expanded, capsule, selectors, 'Investigate exact proof bodies',
                                                  include_theorem_proofs=True)
        proof_view = self.tasks.packet(proof_task)['records'][capsule]['data']['semantic_view']
        validate_view(report, proof_view)
        theorem = next(d for d in proof_view['declarations'].values() if d['detail']['kind'] == 'theorem')
        self.assertTrue(theorem['values'])
        self.assertNotIn('proof_body_omitted', theorem)
        again = self.tasks.expand_semantics(proof_task, capsule, selectors, 'Keep previous proof exposure')
        self.assertEqual(self.tasks.packet(again)['records'][capsule]['data']['semantic_view'], proof_view)
        unrelated = self.r.artifact('Peer review history')
        with self.assertRaisesRegex(StateError, 'already admitted'):
            self.tasks.expand_semantics(expanded, unrelated, selectors, 'Cannot add arbitrary history')

    def test_formal_environment_requires_both_coverage_dimensions(self):
        receipt = self.run_check()
        capsule = self.store.get(receipt)['data']['semantic_artifact']
        report = json.loads(self.store.get(capsule)['data']['text'])
        with patch('mathtrace.context.semantic_view', return_value=semantic_view(report, max_chars=1800)):
            task = self.tasks.create('referee', receipt, checks=['formal-environment'], mandate='Assess checking context')
        run, artifact = self.native_review(task)
        with self.assertRaisesRegex(StateError, 'complete compiled statement'):
            self.tasks.review_provenance(run, receipt, 'pass', artifact, ['formal-environment'])
        expanded = self.tasks.expand_semantics(task, capsule, list(SemanticGraph(report['semantics']).declarations), 'Complete environment exposure')
        new_run, new_artifact = self.native_review(expanded)
        self.assertEqual(self.tasks.review_provenance(new_run, receipt, 'pass', new_artifact,
            ['formal-environment'])['exposure'], 'independent')

    def test_imported_packet_cannot_suppress_receipt_coverage_or_add_capsule_text(self):
        receipt = self.run_check()
        task = self.tasks.create('fidelity-auditor', receipt, checks=['formal-target-fidelity'], mandate='Read exact target')
        original = self.store.get(task)['data']['packet']
        capsule = self.store.get(receipt)['data']['semantic_artifact']
        bound = receipt_evidence(self.store, receipt)
        omissions = [receipt, bound['observation'], *[self.store.get(receipt)['data'][k]
                     for k in ('execution', 'compiled_artifact', 'plan', 'source')]]
        injected = self.r.artifact('Unadmitted independent proof narrative')
        for mutation in ['hide-version', 'change-outcome', 'capsule-header', 'target-hash', 'inject', *omissions]:
            packet = copy.deepcopy(original)
            if mutation in omissions: del packet['records'][mutation]
            elif mutation == 'hide-version': del packet['records'][receipt]['data']['receipt_version']
            elif mutation == 'change-outcome': packet['records'][receipt]['data']['outcome'] = 'disproof'
            elif mutation == 'capsule-header': packet['records'][capsule]['data']['text'] = 'Prior reviewer verdict'
            elif mutation == 'inject': packet['records'][injected] = self.store.get(injected)
            else: packet['target_hash'] = '0' * 64
            with self.store.transaction():
                malformed = self.store.put('task', {'packet': packet, 'packet_hash': digest(packet)})
                self.store.decide(malformed, 'ready', {'reason': 'Synthetic imported packet'})
            run, artifact = self.native_review(malformed)
            with self.subTest(mutation=mutation), self.assertRaises(StateError):
                self.tasks.review_provenance(run, receipt, 'pass', artifact, ['formal-target-fidelity'])

    def test_error_fields_namespace_version_and_resolution_channel_fail_closed(self):
        mutations = [('verification_error', value) for value in ('', False, 0, [], {})]
        mutations += [('artifact_collection_error', False), ('namespace_setup', True),
                      ('namespace_setup', 'claimed isolation'), ('version', None), ('channel', 'fake')]
        for index, (field, value) in enumerate(mutations):
            if index:
                self.plan = self.evidence.formal_plan(self.target,
                    self.r.artifact('theorem t : True := True.intro'), 't', 'True', author='formalizer')
                self.review(self.plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
            observed = fixture.execution(self.r, self.plan)
            if field == 'namespace_setup': observed['replay'][field] = value
            elif field == 'channel':
                report = json.loads(blob_bytes(observed['semantic_output']))
                report['resolution']['channel'] = value
                observed['semantic_output'] = fixture.blob(json.dumps(report).encode())
            else: observed[field] = value
            with self.subTest(field=field, value=value):
                receipt = self.run_check(observed)
                self.assertEqual(self.store.status(receipt), 'failed')
                self.assertFalse(self.r._formal_current(receipt))

    def test_actual_axiom_name_without_matching_reference_schema_is_insufficient(self):
        report = json.loads(blob_bytes(fixture.execution(self.r, self.plan)['semantic_output']))
        axiom = {**report['semantics']['declarations'][0], 'name': exact_name('propext'),
                 'display_name': 'propext', 'type': 0, 'values': [], 'detail': {'kind': 'axiom'}}
        for scope in ('semantics', 'reference_profile'):
            report[scope]['declarations'].append(copy.deepcopy(axiom))
            report[scope]['axioms'] = [axiom['name']]
        report['primitive_reference_count'] += 1
        symbol = self.store.get(self.plan)['data']['check_symbol']
        validate_report(report, symbol, ['propext'])
        report['semantics']['declarations'][-1]['type'] = 1
        with self.assertRaisesRegex(StateError, 'schema'):
            validate_report(report, symbol, ['propext'])

    def test_legacy_pending_recovery_retains_original_assurance(self):
        from mathtrace.execution import Executions
        data = copy.deepcopy(self.store.get(self.plan)['data'])
        for key in ('receipt_version', 'checking_profile', 'helper_artifact', 'helper_sha256'):
            data.pop(key)
        with self.store.transaction():
            legacy_plan = self.store.put('formal_plan', data)
        self.review(legacy_plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        executions = Executions(self.r)
        source = self.store.get(data['check_source'])['data']['text']
        attempt, _ = executions.begin(legacy_plan, 'formal', {'source': source, 'timeout': 120},
            metadata={'toolchain': self.toolchain, 'toolchain_hash': self.store.get(self.toolchain)['hash'],
                      'checker_path': fixture.PINNED['executable'], 'checker_hash': 'synthetic-historical'})
        process = fixture.execution(self.r, self.plan)['result']
        observation = {'version': {**process, 'stdout': 'Lean (version 4.30.0)'},
            'result': {**process, 'stdout': "'" + data['check_symbol'] + "' does not depend on any axioms"},
            'compiled_output': fixture.blob(b'historical synthetic compiled file'), 'replay': process}
        returned = test_research.recorded_result(observation, executions.journal(attempt))
        with patch('mathtrace.evidence.verify_toolchain', return_value=fixture.PINNED):
            receipt = self.evidence._complete_execution(attempt, returned)
        self.assertEqual(self.store.status(receipt), 'checked')
        self.assertNotIn('receipt_version', self.store.get(receipt)['data'])
        self.assertEqual(self.evidence.recover_execution(attempt)['receipt'], receipt)
        self.assertEqual(self.r._formal_condition(receipt)['issues'][0]['category'], 'migration')

    def test_views_are_bound_to_owner_and_do_not_qualify_as_full_capsules(self):
        report = json.loads(blob_bytes(fixture.execution(self.r, self.plan)['semantic_output']))
        view = semantic_view(report, max_chars=None)
        self.assertTrue(view['statement_complete'])
        self.assertEqual(validate_view(report, view), set(view['declarations']))
        altered = copy.deepcopy(report)
        altered['semantics']['expressions'][0] = ['sort', ['succ', ['zero']]]
        with self.assertRaisesRegex(StateError, 'exact slice'):
            validate_view(altered, view)
        with self.assertRaises(StateError):
            SemanticGraph(view)

    def test_parser_rejects_declaration_relationship_native_and_typed_identity_errors(self):
        report = json.loads(blob_bytes(fixture.execution(self.r, self.plan)['semantic_output']))
        for mutation in ('parent', 'native', 'boolean-root', 'missing-detail', 'symbol-type'):
            altered = copy.deepcopy(report)
            if mutation == 'parent': altered['semantics']['declarations'][1]['detail']['inductive'] = exact_name('True.rec')
            elif mutation == 'native': altered['semantics']['declarations'][-1]['name'] = exact_name('Lean.reduceNat')
            elif mutation == 'boolean-root': altered['semantics']['root_type'] = True
            elif mutation == 'missing-detail': del altered['semantics']['declarations'][0]['detail']['recursive']
            with self.subTest(mutation=mutation), self.assertRaises(StateError):
                validate_report(altered, None if mutation == 'symbol-type' else self.store.get(self.plan)['data']['check_symbol'], [])

    def test_legacy_status_requires_explicit_new_evidence(self):
        receipt = self.run_check()
        data = copy.deepcopy(self.store.get(receipt)['data'])
        data.pop('receipt_version')
        data.pop('checking_profile')
        data['kernel_replay'] = 'same-kernel-fresh-environment'
        with self.store.transaction():
            legacy = self.store.put('formal_receipt', data)
            self.store.decide(legacy, 'checked', {'reason': 'Historical protocol'})
        condition = self.r._formal_condition(legacy)
        self.assertFalse(condition['current'])
        self.assertEqual(condition['issues'][0]['category'], 'migration')
        self.assertEqual(self.store.status(legacy), 'checked')


if __name__ == '__main__':
    unittest.main()
