import base64
from copy import deepcopy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import test_research
import formal_fixture
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.evidence import Evidence
from mathtrace.store import StateError, digest


class CampaignTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def test_comparable_strength_obligation_prevents_claiming_route_complete(self):
        target = self.claim()
        route = self.r.route(target, 'Reduce to an open lemma', family='reduction')
        obligation = self.r.obligation(route, 'Prove equivalent open lemma', claim=self.claim('Q'))
        self.r.route_status(route, 'blocked', self.proof, reopen_condition='A proof of Q becomes available')
        with self.assertRaises(StateError):
            self.r.close_obligation(obligation, expected=self.store.revision)
        self.assertIn(obligation, self.r.progress()['open_obligations'])
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_closed_obligation_reopens_when_support_withdrawn(self):
        target = self.claim()
        support = self.accept(target)
        route = self.r.route(target, 'direct', family='elementary')
        obligation = self.r.obligation(route, 'Establish target', claim=target)
        self.review(obligation, ['obligation-mapping'])
        self.r.close_obligation(obligation, expected=self.store.revision)
        self.assertNotIn(obligation, self.r.progress()['open_obligations'])
        self.r.withdraw(support, 'invalid argument')
        self.assertIn(obligation, self.r.progress()['open_obligations'])

    def test_external_theorem_requires_all_hypotheses(self):
        theorem = self.r.external_theorem('sqrt(x²)=x for x>=0', 'source v1', self.proof, ['nonnegative'], [])
        target = self.claim('sqrt(x²)=x')
        with self.assertRaises(StateError):
            self.r.application(theorem, target, {}, 'identity substitution', self.proof, 'author')
        h = self.claim('x>=0')
        self.accept(h)
        app = self.r.application(theorem, target, {'nonnegative': h}, 'identity substitution', self.proof, 'author')
        self.review(app, ['source', 'hypotheses', 'substitution', 'conclusion'])
        self.r.accept_application(app, expected=self.store.revision)
        inf = self.r.inference(target, [], self.proof, 'author', applications=[app])
        self.review(inf)
        self.r.promote(inf, expected=self.store.revision, request_id='application')
        self.assertEqual(self.r.claim_state(target)['state'], 'supported')
        self.r.withdraw(theorem, 'source retraction')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_candidate_does_not_silently_swap_alternative_proof(self):
        target = self.claim()
        first = self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.accept(target)
        self.r.withdraw(first, 'gap in frozen proof')
        self.assertEqual(self.r.claim_state(target)['state'], 'supported')
        self.assertFalse(self.r.candidate_current(candidate))
        with self.assertRaises(StateError):
            self.r.audit_candidate(candidate, expected=self.store.revision)

    def test_candidate_reader_reconstructs_exact_target_manifest_and_summary_scope(self):
        target, other = self.claim(), self.claim('Different target')
        self.accept(target)
        self.accept(other)
        summary = self.r.artifact('Complete candidate proof')
        original = self.r.freeze(target, summary, author='author')
        data = self.store.get(original)['data']
        self.assertTrue(self.r.candidate_current(original))
        malformed = []
        wrong_target = deepcopy(data)
        wrong_target['target'] = other
        malformed.append(wrong_target)
        empty = deepcopy(data)
        empty['manifest'] = {}
        empty['manifest_hash'] = digest({'records': {}, 'derivation': empty['derivation'],
                                        'evaluator': empty['evaluator']})
        malformed.append(empty)
        bad_hash = deepcopy(data)
        bad_hash['manifest_hash'] = 'not-the-witness-hash'
        malformed.append(bad_hash)
        extra = deepcopy(data)
        extra['manifest'][self.r.artifact('Unselected material')] = 'unbound'
        malformed.append(extra)
        bad_id = deepcopy(data)
        bad_id['proof'] = []
        malformed.append(bad_id)
        for bad in malformed:
            with self.store.transaction():
                identifier = self.store.put('candidate', bad)
                self.store.decide(identifier, 'frozen', {'reason': 'Imported malformed fixture'})
            self.assertFalse(self.r.candidate_current(identifier))
        with self.store.transaction():
            self.store.decide(summary, 'rejected', {'reason': 'Candidate proof defect'})
        self.assertFalse(self.r.candidate_current(original))
        with self.assertRaises(StateError):
            self.r.freeze(target, summary, author='author')

    def test_candidate_audit_without_exact_witnesses_is_not_current(self):
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        with self.store.transaction():
            self.store.decide(candidate, 'audited', {'reason': 'Malformed imported audit fixture'})
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.r.candidate_audit_current(candidate))
        self.assertIn(candidate, self.r.progress()['reaudit_needed'])
        with self.assertRaises(StateError):
            self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')

    def test_same_selected_proof_can_regain_qualification_without_replacing_candidate_audit(self):
        target = self.claim()
        support = self.accept(target)
        qualification = [r['id'] for r in self.store.records('review') if r['data']['target'] == support][0]
        candidate = self.r.freeze(target, self.proof, author='author')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], reviewer='fidelity', role='fidelity-auditor')
        self.review(candidate, ['falsification'], reviewer='adversarial', role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        publication = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        audit_witnesses = self.store.get(publication)['data']['reviews']
        self.r.withdraw(qualification, 'Qualification witness retracted; proof bytes unchanged')
        self.assertFalse(self.r.release_current(publication))
        self.review(support)
        self.assertTrue(self.r.release_current(publication))
        self.assertEqual(self.store.get(publication)['data']['reviews'], audit_witnesses)

    def test_imported_application_cannot_omit_an_exact_theorem_hypothesis(self):
        target = self.claim()
        theorem = self.r.external_theorem('T if H', 'Exact source', self.proof, ['H'], [])
        with self.store.transaction():
            application = self.store.put('application', {'theorem': theorem, 'conclusion': target,
                'mapping': {}, 'substitution': 'identity', 'artifact': self.proof, 'author': 'author'})
        self.review(application, ['source', 'hypotheses', 'substitution', 'conclusion'])
        with self.assertRaises(StateError):
            self.r.accept_application(application, expected=self.store.revision)
        with self.store.transaction():
            self.store.decide(application, 'accepted', {'reason': 'Malformed imported status'})
        inference = self.r.inference(target, [], self.proof, 'author', applications=[application])
        self.review(inference)
        with self.assertRaises(StateError):
            self.r.promote(inference, expected=self.store.revision, request_id='missing-mapped-hypothesis')

    def test_formal_disproof_selects_one_complete_assurance_eligible_refutation(self):
        # Synthetic checker boundary tests selection policy, not proof validity.
        target, lemma = self.claim('False'), self.claim('0 = 0')
        self.accept(lemma)
        evidence = Evidence(self.r)
        source = self.r.artifact('theorem negation : Not False := by intro h; cases h')
        plan = evidence.formal_plan(target, source, 'negation', 'Not False', author='formalizer', outcome='disproof')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])
        toolchain = formal_fixture.toolchain(self.r)
        symbol = self.store.get(plan)['data']['check_symbol']
        process = {'exit_code': 0, 'timed_out': False, 'namespace_setup': True, 'output_limited': False}
        checked = formal_fixture.execution(self.r, plan)
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(checked)), \
             patch('mathtrace.evidence.verify_toolchain', return_value={'executable': sys.executable}):
            receipt = evidence.run_lean(plan, toolchain=toolchain)
        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        from mathtrace.orchestration import Orchestration
        self.assertTrue(self.r._formal_current(receipt))
        actions = [a['action'] for a in Orchestration(self.r).next_actions()['actions'] if a.get('receipt') == receipt]
        self.assertIn('assess-formal-evidence', actions)
        self.assertNotIn('review-formal-receipt', actions)
        first = self.r.counterexample(target, self.proof, 'hunter', formal_receipt=receipt, dependencies=[lemma])
        self.review(first, ['domain', 'negation', 'scope', 'dependencies'])
        self.r.validate_counterexample(first, expected=self.store.revision)
        second = self.r.counterexample(target, self.proof, 'hunter', formal_receipt=receipt)
        self.review(second, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(second, expected=self.store.revision)
        candidate = self.r.freeze(target, self.proof, author='hunter', outcome='disproof', assurance='machine-checked')
        self.assertEqual(self.store.get(candidate)['data']['derivation']['counterexample'], second)
        self.assertTrue(self.r.candidate_current(candidate))

    def test_release_requires_fidelity_and_falsification_then_becomes_stale(self):
        target = self.claim()
        support = self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        with self.assertRaises(StateError):
            self.r.audit_candidate(candidate, expected=self.store.revision)
        self.review(candidate, ['target-fidelity'], reviewer='fidelity', role='fidelity-auditor')
        self.review(candidate, ['falsification'], reviewer='adversarial', role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        self.assertTrue(self.r.progress()['releases'][0]['current'])
        self.r.withdraw(support, 'fatal issue')
        self.assertFalse(self.r.progress()['releases'][0]['current'])
        self.assertEqual(self.store.status(release), 'released')  # history preserved

    def test_learning_stales_without_global_memory(self):
        target = self.claim()
        support = self.accept(target)
        learning = self.r.learning('P was established', [target], category='structural-insight', reopen_condition='Recheck if support changes')
        self.assertTrue(self.r.learning_current(learning))
        self.r.withdraw(support, 'gap')
        self.assertFalse(self.r.learning_current(learning))

    def test_release_readiness_withdrawal_and_deliberate_republication(self):
        from mathtrace.orchestration import Orchestration
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        self.assertIn(candidate, self.r.progress()['release_ready'])
        self.assertIn({'action': 'release-candidate', 'candidate': candidate, 'automatic_release': False},
                      Orchestration(self.r).next_actions()['actions'])
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        before = self.store.revision
        self.assertEqual(self.r.release(candidate, expected=before, assurance='audited-informal'), release)
        self.assertEqual(self.store.revision, before)
        self.r.withdraw(release, 'Publication retracted for correction')
        self.assertFalse(self.r.release_current(release))
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertEqual(self.r.progress()['release_ready'], [])
        self.assertFalse(any(a.get('release') == release for a in Orchestration(self.r).next_actions()['actions']))
        with self.assertRaises(StateError):
            self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        replacement = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal',
                                     supersedes=release, reason='Corrected publication metadata')
        self.assertTrue(self.r.release_current(replacement))
        self.assertFalse(self.r.release_current(release))

    def test_release_audit_witnesses_cannot_be_silently_replaced(self):
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        proof_review = self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        self.r.withdraw(proof_review, 'Reviewer receipt retracted')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.r.release_current(release))

    def test_first_publication_cannot_replace_witnesses_beneath_old_audit(self):
        from mathtrace.orchestration import Orchestration
        target = self.claim()
        self.accept(target)
        candidate = self.r.freeze(target, self.proof, author='author')
        witness = self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        self.r.withdraw(witness, 'Audit receipt retracted')
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.assertTrue(self.r.candidate_current(candidate))
        self.assertFalse(self.r.candidate_audit_current(candidate))
        self.assertEqual(self.r.progress()['release_ready'], [])
        self.assertIn(candidate, self.r.progress()['reaudit_needed'])
        self.assertTrue(any(a['action'] == 'reaudit-candidate'
                            for a in Orchestration(self.r).next_actions()['actions']))
        with self.assertRaisesRegex(StateError, 'review witness'):
            self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        self.assertTrue(self.r.candidate_audit_current(candidate))
        self.assertIn(candidate, self.r.progress()['release_ready'])

    def test_candidate_id_churn_cannot_republish_the_same_withdrawn_manifest(self):
        target = self.claim()
        self.accept(target)
        def audited(proof):
            candidate = self.r.freeze(target, proof, author='author')
            self.review(candidate, ['full-proof', 'dependency-closure'])
            self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
            self.review(candidate, ['falsification'], role='falsifier')
            self.r.audit_candidate(candidate, expected=self.store.revision)
            return candidate
        first = audited(self.proof)
        release = self.r.release(first, expected=self.store.revision, assurance='audited-informal')
        self.r.withdraw(release, 'Retract this publication')
        clone = audited(self.proof)
        self.assertEqual(self.store.get(clone)['data']['manifest_hash'], self.store.get(first)['data']['manifest_hash'])
        self.assertNotIn(clone, self.r.progress()['release_ready'])
        with self.assertRaises(StateError):
            self.r.release(clone, expected=self.store.revision, assurance='audited-informal')
        replacement = self.r.release(clone, expected=self.store.revision, assurance='audited-informal',
            supersedes=release, reason='Deliberate republication of the same frozen proof')
        self.assertTrue(self.r.release_current(replacement))
        different = audited(self.r.artifact('Different complete candidate argument; synthetic fixture'))
        self.assertIn(different, self.r.progress()['release_ready'])

    def test_failed_route_learning_remains_useful(self):
        route = self.r.route(self.claim(), 'failed mechanism', family='test')
        self.r.route_status(route, 'blocked', self.proof, reopen_condition='New lemma')
        learning = self.r.learning('This mechanism is blocked', [route], category='failed-mechanism', reopen_condition='New lemma')
        self.assertTrue(self.r.learning_current(learning))
        self.r.route_status(route, 'active', self.proof, reopen_condition='New lemma now available')
        self.assertFalse(self.r.learning_current(learning))

    def test_verified_disproof_has_its_own_audit_and_release(self):
        target = self.claim('Every nonnegative real has positive square')
        example = self.r.counterexample(target, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        candidate = self.r.freeze(target, self.proof, author='hunter', outcome='disproof')
        self.review(candidate, ['full-proof', 'target-fidelity', 'dependency-closure', 'falsification'])
        with self.assertRaises(StateError):
            self.r.audit_candidate(candidate, expected=self.store.revision)
        self.review(candidate, ['full-refutation'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        released = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        self.assertEqual(self.store.get(released)['data']['outcome'], 'disproof')
        self.r.withdraw(example, 'domain check found invalid')
        self.assertFalse(self.r.progress()['releases'][0]['current'])

    def test_transitive_definition_withdrawal_disables_support(self):
        base = self.r.definition('domain', 'positive real numbers')
        derived = self.r.definition('notation', 'x is in the domain', [base])
        claim = self.r.claim('P', self.contract, definitions=[derived])
        self.accept(claim)
        self.r.withdraw(base, 'definition interpreted incorrectly')
        self.assertEqual(self.r.claim_state(claim)['state'], 'unsupported')

    def test_source_evidence_withdrawal_invalidates_application_support(self):
        source = self.r.artifact('Exact external theorem source')
        theorem = self.r.external_theorem('T', 'edition 1', source, [], [])
        target = self.claim('T')
        app = self.r.application(theorem, target, {}, 'same statement', self.proof, 'author')
        self.review(app, ['source', 'hypotheses', 'substitution', 'conclusion'])
        self.r.accept_application(app, expected=self.store.revision)
        inference = self.r.inference(target, [], self.proof, 'author', applications=[app])
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='with-source')
        self.r.withdraw(source, 'source was incomplete')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')

    def test_withdrawn_target_cannot_receive_new_disproof_candidate(self):
        target = self.claim()
        self.r.withdraw(target, 'invalid scope')
        example = self.r.counterexample(target, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        with self.assertRaises(StateError):
            self.r.validate_counterexample(example, expected=self.store.revision)
        with self.assertRaises(StateError):
            self.r.freeze(target, self.proof, author='hunter', outcome='disproof')

    def test_compiled_artifact_withdrawal_invalidates_frozen_formal_candidate(self):
        target = self.claim('True')
        source = self.r.artifact('theorem t : True := by trivial')
        evidence = Evidence(self.r)
        plan = evidence.formal_plan(target, source, 't', 'True', author='formalizer')
        self.review(plan, ['formal-source-integrity', 'formal-target-fidelity', 'foundations'])

        # Create large synthetic toolchain with 500 files
        synthetic_files = {f'lib/lean/file_{i}.olean': 'a' * 64 for i in range(500)}
        synthetic_files['bin/lean'] = '0' * 64
        toolchain = formal_fixture.toolchain(self.r, synthetic_files)

        # Meaningfully large synthetic binary payload (100 KB binary -> base64)
        raw_binary_bytes = b'LEAN_OLEAN_BINARY_PAYLOAD_TEST_' * 3200  # ~100 KB
        large_base64_payload = base64.b64encode(raw_binary_bytes).decode('ascii')

        symbol = self.store.get(plan)['data']['check_symbol']
        execution = formal_fixture.execution(self.r, plan, primary=raw_binary_bytes)
        pinned = {'executable': sys.executable, 'root': str(Path(sys.executable).parent), 'manifest_hash': '0' * 64}
        with patch('mathtrace.execution.Executions.selection', return_value=('bubblewrap', None)), patch('mathtrace.evidence.check_lean', side_effect=test_research.recorded_runner(execution)), patch('mathtrace.evidence.verify_toolchain', return_value=pinned):
            receipt = evidence.run_lean(plan, toolchain=toolchain)

        receipt_data = self.store.get(receipt)['data']
        compiled_artifact = receipt_data['compiled_artifact']
        self.assertIsNotNone(compiled_artifact)

        self.review(receipt, ['formal-receipt', 'formal-target-fidelity', 'foundations'])
        inference = self.r.inference(target, [], self.proof, 'author', assurance='formal', formal_receipt=receipt)
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='formal-promote')
        self.assertEqual(self.r.claim_state(target, policy='formal-only')['state'], 'supported')

        candidate = self.r.freeze(target, self.proof, author='author', assurance='machine-checked')
        candidate_rec = self.store.get(candidate)

        # 1. Candidate manifest must contain compiled_artifact
        self.assertIn(compiled_artifact, candidate_rec['data']['manifest'])

        # 2. Context packet for auditor must include compiled_artifact in records
        tasks = Tasks(self.r)
        task = tasks.create('fidelity-auditor', candidate, checks=['target-fidelity'], mandate='Audit candidate')
        packet = tasks.packet(task)
        self.assertIn(compiled_artifact, packet['records'])

        # 3. Compact projection for binary artifact in packet:
        projected_artifact = packet['records'][compiled_artifact]['data']
        self.assertTrue(projected_artifact.get('content_omitted'))
        self.assertNotIn('text', projected_artifact)
        self.assertEqual(projected_artifact['encoding'], 'base64')
        self.assertEqual(projected_artifact['media_type'], 'application/x-lean-olean')
        self.assertEqual(projected_artifact['sha256'], execution['compiled_output']['sha256'])
        self.assertEqual(projected_artifact['size'], len(raw_binary_bytes))
        self.assertIn('content_hash', projected_artifact)

        # Canonical store artifact must STILL contain the full raw text:
        canonical_artifact = self.store.get(compiled_artifact)['data']
        self.assertEqual(canonical_artifact['text'], large_base64_payload)

        # 4. Compact projection for toolchain manifest in packet:
        self.assertIn(toolchain, packet['records'])
        projected_toolchain = packet['records'][toolchain]['data']
        self.assertTrue(projected_toolchain.get('manifest_omitted'))
        self.assertNotIn('files', projected_toolchain)
        self.assertNotIn('root', projected_toolchain)
        self.assertEqual(projected_toolchain['file_count'], 502)
        self.assertEqual(projected_toolchain['manifest_hash'], '0' * 64)
        self.assertEqual(projected_toolchain['files_hash'], digest(self.store.get(toolchain)['data']['files']))

        # Canonical store toolchain must STILL contain the full files dictionary:
        canonical_toolchain = self.store.get(toolchain)['data']
        self.assertIn('files', canonical_toolchain)
        self.assertEqual(len(canonical_toolchain['files']), 502)

        # 5. Human-readable mathematical text artifact (self.proof) must retain text:
        self.assertIn(self.proof, packet['records'])
        projected_proof = packet['records'][self.proof]['data']
        self.assertIn('text', projected_proof)
        self.assertEqual(projected_proof['text'], self.store.get(self.proof)['data']['text'])
        self.assertFalse(projected_proof.get('content_omitted', False))

        # 6. Candidate is currently valid
        self.assertTrue(self.r.candidate_current(candidate))

        # 7. Withdrawing the compiled artifact invalidates the frozen candidate
        self.r.withdraw(compiled_artifact, 'corrupted olean artifact')
        self.assertFalse(self.r.candidate_current(candidate))
        with self.assertRaises(StateError):
            self.r.audit_candidate(candidate, expected=self.store.revision)

    def test_disproof_candidate_freeze_rejected_when_contract_forbids_disproof(self):
        contract_no_disproof = self.r.contract('P_nodis', [], completion='Proof only', allow_disproof=False)
        claim_no_disproof = self.r.claim('P_nodis', contract_no_disproof)
        example = self.r.counterexample(claim_no_disproof, self.proof, 'hunter')
        self.review(example, ['domain', 'negation', 'scope'])
        self.r.validate_counterexample(example, expected=self.store.revision)
        with self.assertRaisesRegex(StateError, 'does not permit a disproof release'):
            self.r.freeze(claim_no_disproof, self.proof, author='hunter', outcome='disproof')

    def test_external_theorem_and_application_reject_collection_coercion(self):
        d1 = self.r.definition("D1", "First definition")
        a1 = self.r.artifact("# Source text")
        base_rev = self.store.revision
        base_count = len(self.store.records())

        # external_theorem hypotheses must be an exact list
        for invalid in [{"h1": False, "h2": False}, "h1", 123, ["h1", 123], [""]]:
            with self.assertRaisesRegex(StateError, "Hypotheses must have distinct nonempty labels"):
                self.r.external_theorem("Th", "Source v1", a1, hypotheses=invalid, definitions=[d1])

        # external_theorem definitions must be an exact list
        for invalid in [{d1: False}, d1, 123, [123], [""]]:
            with self.assertRaisesRegex(StateError, "definitions must be an exact list"):
                self.r.external_theorem("Th", "Source v1", a1, hypotheses=["h1"], definitions=invalid)

        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)

        th = self.r.external_theorem("Th", "Source v1", a1, hypotheses=["h1"], definitions=[d1])
        c1 = self.claim("C1")

        # application mapping must be an exact dict
        for invalid in [["h1"], "h1", 123, None, {"h1": 123}, {123: c1}, {"h1": ""}, {"": c1}]:
            with self.assertRaisesRegex(StateError, "mapping must be an exact dictionary"):
                self.r.application(th, c1, mapping=invalid, substitution="x -> y", artifact=a1, author="tester")

        # Valid application succeeds and stores exact dict
        app = self.r.application(th, c1, mapping={"h1": c1}, substitution="x -> y", artifact=a1, author="tester")
        self.assertEqual(self.store.get(app)["data"]["mapping"], {"h1": c1})

    def test_learning_rejects_collection_coercion(self):
        d1 = self.r.definition("D1", "First definition")
        base_rev = self.store.revision
        base_count = len(self.store.records())

        # learning sources must be an exact nonempty list
        for invalid in [{d1: False}, d1, 123, [], [123], [""]]:
            with self.assertRaisesRegex(StateError, "Local learning requires exact source records"):
                self.r.learning("Insight", sources=invalid, category="structural-insight", reopen_condition="never")

        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)

        lrn = self.r.learning("Insight", sources=[d1], category="structural-insight", reopen_condition="never")
        self.assertIn(d1, self.store.get(lrn)["data"]["sources"])


