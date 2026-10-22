import hashlib
import json
import unittest
import test_research

from mathtrace.context import Tasks
from mathtrace.store import StateError, digest


class ContextTests(unittest.TestCase):
    setUp = test_research.ResearchTests.setUp
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def task(self, target, role='referee', checks=None):
        return Tasks(self.r).create(role, target, checks=checks or ['validity'], mandate='Exact task')

    def launch(self, task, conversation='native-conversation'):
        return Tasks(self.r).start(task, conversation, host='antigravity',
                                  dispatch_evidence=self.proof, tools=[], inherited_history=False)

    def test_scout_receives_exact_problem_but_not_candidate(self):
        p = self.claim('target lemma')
        inference = self.r.inference(p, [], self.proof, 'author')
        task = self.task(inference, role='scout')
        packet = Tasks(self.r).packet(task)
        self.assertIn(p, packet['records'])
        self.assertIn(self.contract, packet['records'])
        self.assertNotIn(inference, packet['records'])
        self.assertNotIn(self.proof, packet['records'])

    def test_referee_has_exact_proof_and_assumptions(self):
        p = self.claim()
        assumption = self.r.assumption('temporary A')
        inference = self.r.inference(p, [], self.proof, 'author', assumptions=[assumption])
        packet = Tasks(self.r).packet(self.task(inference))
        self.assertIn(assumption, packet['records'])
        self.assertIn(self.proof, packet['records'])
        self.assertNotIn('author', packet['records'][inference]['data'])

    def test_other_verdict_cannot_be_added_without_exposure_transition(self):
        p = self.claim()
        inference = self.r.inference(p, [], self.proof, 'author')
        verdict = self.review(inference)
        task = self.task(inference)
        with self.assertRaises(StateError):
            Tasks(self.r).extend(task, [verdict], 'Need reviewer opinion')
        extended = Tasks(self.r).extend(task, [verdict], 'Informed reconciliation', becomes_informed=True)
        self.assertEqual(Tasks(self.r).packet(extended)['independence'], 'informed')
        self.assertEqual(Tasks(self.r).packet(task)['independence'], 'blind')

    def test_same_native_conversation_cannot_count_twice(self):
        p = self.claim()
        first, second = self.task(p), self.task(p)
        self.launch(first)
        with self.assertRaises(StateError):
            self.launch(second)

    def test_inherited_history_and_write_tool_break_isolated_dispatch(self):
        task = self.task(self.claim())
        for tools, inherited in [(['run_command'], False), ([], True)]:
            with self.assertRaises(StateError):
                Tasks(self.r).start(task, 'native', host='antigravity', dispatch_evidence=self.proof,
                                    tools=tools, inherited_history=inherited)

    def test_result_cannot_claim_unassigned_check(self):
        task = self.task(self.claim())
        run = self.launch(task)
        output = json.dumps({'task_id': task, 'packet_hash': Tasks(self.r).packet(task)['packet_hash'],
                             'outcome': 'review', 'verdict': 'pass', 'checks': ['formal-proof'], 'reasoning': 'test'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'native-conversation', 'status': 'SUCCESS', 'response': output}))
        with self.assertRaisesRegex(StateError, 'outside its task'):
            Tasks(self.r).finish(run, artifact, receipt, outcome='review', verdict='pass', checks=['formal-proof'])

    def test_returned_content_cannot_be_replaced_by_root_summary(self):
        run = self.launch(self.task(self.claim()))
        receipt = self.r.artifact(json.dumps({'conversation_id': 'native-conversation', 'status': 'SUCCESS', 'response': 'actual response'}))
        with self.assertRaisesRegex(StateError, 'differs from the host'):
            Tasks(self.r).finish(run, self.proof, receipt, outcome='inconclusive')

    def test_receipt_for_other_conversation_rejected(self):
        run = self.launch(self.task(self.claim()))
        receipt = self.r.artifact(json.dumps({'conversation_id': 'wrong', 'status': 'SUCCESS'}))
        with self.assertRaises(StateError):
            Tasks(self.r).finish(run, self.proof, receipt, outcome='review', verdict='pass', checks=['validity'])

    def test_review_requires_native_receipt_not_identity_strings(self):
        inference = self.r.inference(self.claim(), [], self.proof, 'author')
        with self.assertRaises(StateError):
            self.r.review(inference, 'another-person', 'fake-run', 'pass', self.proof, ['validity'])

    def test_late_exposure_invalidates_independent_review(self):
        p = self.claim()
        inference = self.accept(p)
        self.assertEqual(self.r.claim_state(p)['state'], 'supported')
        Tasks(self.r).expose(self.last_run, 'other-verdict', self.proof, 'Read a peer verdict')
        self.assertEqual(self.r.claim_state(p)['state'], 'unsupported')
        self.assertEqual(self.store.status(inference), 'accepted')

    def test_duplicate_review_of_same_result_rejected(self):
        p = self.claim()
        inference = self.r.inference(p, [], self.proof, 'author')
        review = self.review(inference)
        data = self.store.get(review)['data']
        with self.assertRaises(StateError):
            self.r.review(inference, data['reviewer'], data['run_id'], 'pass', data['artifact'], data['checks'])

    def test_blind_discovery_blocks_raw_artifacts_and_counterexamples(self):
        target = self.claim()
        counterexample = self.r.counterexample(target, self.proof, 'hunter')
        tasks = Tasks(self.r)
        for source in [self.proof, counterexample]:
            with self.assertRaises(StateError):
                tasks.create('scout', target, checks=['route'], mandate='Explore', background=[source])
            task = self.task(target, role='scout')
            with self.assertRaises(StateError):
                tasks.extend(task, [source], 'Supplement')

    def test_background_admission_rationale_is_reviewable_but_hidden_from_blind_discovery(self):
        target = self.claim()
        source = self.r.artifact('Exact foundational definitions')
        rationale = self.r.artifact('Admission scope and source-fidelity argument')
        tasks = Tasks(self.r)
        background = tasks.background(target, source, 'foundation', rationale)
        review_task = tasks.create('referee', background, checks=['background-scope', 'source-fidelity'],
                                   mandate='Assess admission rationale against source')
        self.assertIn(rationale, tasks.packet(review_task)['records'])
        self.review(background, ['background-scope', 'source-fidelity'])
        blind = tasks.create('scout', target, checks=['route'], mandate='Independent route', background=[background])
        packet = tasks.packet(blind)
        self.assertIn(source, packet['records'])
        self.assertNotIn(rationale, packet['records'])
        self.assertTrue(packet['records'][background]['data']['admission_rationale_omitted'])
        self.assertNotIn('rationale', packet['records'][background]['data'])
        self.r.withdraw(rationale, 'Admission argument no longer trusted')
        self.assertFalse(self.r._scope_current(background))
        with self.assertRaises(StateError):
            tasks.create('scout', target, checks=['route'], mandate='Fresh independent route', background=[background])

    def test_unrecorded_operator_receipt_does_not_qualify_as_independent(self):
        inference = self.r.inference(self.claim(), [], self.proof, 'author')
        tasks = Tasks(self.r)
        checks = ['validity', 'scope', 'dependencies']
        task = self.task(inference, checks=checks)
        run = self.launch(task)
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
                             'outcome': 'review', 'verdict': 'pass', 'checks': checks, 'reasoning': 'Reported review'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'native-conversation', 'status': 'SUCCESS', 'response': output}))
        tasks.finish(run, artifact, receipt, outcome='review', verdict='pass', checks=checks)
        with self.assertRaisesRegex(StateError, 'exposure must match'):
            self.r.review(inference, 'native-conversation', run, 'pass', artifact, checks)
        self.r.review(inference, 'native-conversation', run, 'pass', artifact, checks, exposure='reported-independent')
        with self.assertRaisesRegex(StateError, 'coverage is incomplete'):
            self.r.promote(inference, expected=self.store.revision, request_id='reported')

    def test_machine_heavy_records_are_compactly_projected_in_task_packets(self):
        target = self.claim('Statement')
        normal_proof = self.r.artifact('Normal human-readable proof text.')
        json_evidence = self.r.artifact('{"model_evidence": [1, 2, 3], "formula": "x + y = z"}',
                                        media_type='application/json')

        # Legitimate reachable context path for application/json:
        # A reviewed foundational background artifact admitted to an informed auditor task
        tasks = Tasks(self.r)
        rationale = self.r.artifact('Mathematical model output dataset rationale')
        bg = tasks.background(target, json_evidence, 'foundation', rationale)
        self.review(bg, ['background-scope', 'source-fidelity'])

        # Binary artifact
        with self.store.transaction():
            binary_artifact = self.store.put('artifact', {
                'text': 'AQIDBAUG' * 5000,  # ~40 KB base64
                'encoding': 'base64',
                'media_type': 'application/x-lean-olean',
                'content_hash': 'h' * 64,
                'sha256': 's' * 64,
                'size': 30000,
            })
            # Toolchain with 1,000 files
            large_files = {f'dir/file_{i}.txt': 'f' * 64 for i in range(1000)}
            toolchain = self.store.put('toolchain', {
                'root': '/opt/lean',
                'executable': 'bin/lean',
                'files': large_files,
                'version': 'v4.30.0',
                'publisher_metadata': 'https://api.github.com/...',
                'release_digest': 'sha256:' + 'd' * 64,
                'archive': '/tmp/lean.zip',
                'platform': 'linux-x86_64',
                'installation_layout': 'fresh-archive-exact-versioned-tree',
                'archive_file_set_hash': 'a' * 64,
            })
            # Formal plan with legitimate assumptions (empty list, per Evidence.formal_plan)
            plan = self.store.put('formal_plan', {
                'target': target,
                'source': normal_proof,
                'check_source': normal_proof,
                'symbol': 's',
                'check_symbol': 'cs',
                'expected_type': 'True',
                'assumptions': [],
                'allowed_axioms': [],
                'author': 'formalizer',
                'outcome': 'proof',
            })
            # Reflect actual production library_manifest shape: only root and files
            extra_libraries = [{
                'root': '/opt/mathlib',
                'files': {f'Mathlib/file_{i}.olean': 'm' * 64 for i in range(500)}
            }]
            large_stdout = 'Lean trace diagnostic ' * 300  # ~6.6 KB
            large_stderr = 'Warning trace ' * 250  # ~3.5 KB
            receipt = self.store.put('formal_receipt', {
                'target': target,
                'plan': plan,
                'source': normal_proof,
                'toolchain': toolchain,
                'compiled_artifact': binary_artifact,
                'assumptions': [],
                'checker': 'lean4-reviewed-source',
                'checker_path': '/opt/lean/bin/lean',
                'checker_hash': 'c' * 64,
                'libraries': extra_libraries,
                'result': {
                    'exit_code': 0,
                    'stdout': large_stdout,
                    'stderr': large_stderr,
                    'timed_out': False,
                },
                'version': {
                    'exit_code': 0,
                    'stdout': 'Lean (version 4.30.0)',
                    'stderr': '',
                },
            })

        task = tasks.create('fidelity-auditor', receipt, checks=['formal-receipt'], mandate='Audit formal receipt',
                            independence='informed', background=[bg])
        packet = tasks.packet(task)

        # 1. Binary artifact has text omitted and metadata retained
        self.assertIn(binary_artifact, packet['records'])
        proj_bin = packet['records'][binary_artifact]['data']
        self.assertTrue(proj_bin.get('content_omitted'))
        self.assertNotIn('text', proj_bin)
        self.assertEqual(proj_bin['encoding'], 'base64')
        self.assertEqual(proj_bin['media_type'], 'application/x-lean-olean')
        self.assertEqual(proj_bin['sha256'], 's' * 64)
        self.assertEqual(proj_bin['size'], 30000)

        # Canonical binary artifact still retains full text
        self.assertEqual(self.store.get(binary_artifact)['data']['text'], 'AQIDBAUG' * 5000)

        # 2. Toolchain has files omitted, files_hash and archive_file_set_hash kept distinct, host paths sanitized
        self.assertIn(toolchain, packet['records'])
        proj_toolchain = packet['records'][toolchain]['data']
        self.assertTrue(proj_toolchain.get('manifest_omitted'))
        self.assertNotIn('files', proj_toolchain)
        self.assertNotIn('root', proj_toolchain)
        self.assertNotIn('archive', proj_toolchain)
        self.assertNotIn('manifest_hash', proj_toolchain)
        self.assertEqual(proj_toolchain['file_count'], 1000)
        self.assertEqual(proj_toolchain['files_hash'], digest(large_files))
        self.assertEqual(proj_toolchain['archive_file_set_hash'], 'a' * 64)
        self.assertEqual(proj_toolchain['version'], 'v4.30.0')

        # Canonical toolchain still retains full files dict and host paths
        self.assertEqual(len(self.store.get(toolchain)['data']['files']), 1000)
        self.assertEqual(self.store.get(toolchain)['data']['root'], '/opt/lean')
        self.assertEqual(self.store.get(toolchain)['data']['archive'], '/tmp/lean.zip')

        # 3. Normal proof artifact retains full text without content_omitted
        self.assertIn(normal_proof, packet['records'])
        proj_text = packet['records'][normal_proof]['data']
        self.assertEqual(proj_text['text'], 'Normal human-readable proof text.')
        self.assertFalse(proj_text.get('content_omitted', False))

        # 4. Human-readable application/json artifact retains full text
        self.assertIn(json_evidence, packet['records'])
        proj_json = packet['records'][json_evidence]['data']
        self.assertEqual(proj_json['text'], '{"model_evidence": [1, 2, 3], "formula": "x + y = z"}')
        self.assertEqual(proj_json['media_type'], 'application/json')
        self.assertFalse(proj_json.get('content_omitted', False))

        # 5. Nested formal receipt compacts libraries, bounds streams, and removes machine-local checker_path
        self.assertIn(receipt, packet['records'])
        proj_receipt = packet['records'][receipt]['data']
        self.assertNotIn('checker_path', proj_receipt)
        self.assertEqual(proj_receipt['checker'], 'lean4-reviewed-source')
        self.assertEqual(proj_receipt['checker_hash'], 'c' * 64)

        # Extra-library files compacted and root sanitized (honest production shape: files_hash, file_count, manifest_omitted)
        self.assertEqual(len(proj_receipt['libraries']), 1)
        proj_lib = proj_receipt['libraries'][0]
        self.assertNotIn('files', proj_lib)
        self.assertNotIn('root', proj_lib)
        self.assertTrue(proj_lib.get('manifest_omitted'))
        self.assertEqual(proj_lib['file_count'], 500)
        self.assertEqual(proj_lib['files_hash'], digest(extra_libraries[0]['files']))
        self.assertEqual(set(proj_lib.keys()), {'files_hash', 'file_count', 'manifest_omitted'})

        # Process stdout / stderr bounded
        bounded_stdout = proj_receipt['result']['stdout']
        self.assertIsInstance(bounded_stdout, dict)
        self.assertTrue(bounded_stdout['truncated'])
        self.assertEqual(bounded_stdout['length'], len(large_stdout))
        self.assertEqual(bounded_stdout['preview'], large_stdout[:2048])
        self.assertEqual(bounded_stdout['sha256'], hashlib.sha256(large_stdout.encode('utf-8')).hexdigest())

        bounded_stderr = proj_receipt['result']['stderr']
        self.assertIsInstance(bounded_stderr, dict)
        self.assertTrue(bounded_stderr['truncated'])
        self.assertEqual(bounded_stderr['length'], len(large_stderr))
        self.assertEqual(bounded_stderr['preview'], large_stderr[:2048])

        # Short version stream is untouched
        self.assertEqual(proj_receipt['version']['stdout'], 'Lean (version 4.30.0)')

        # Canonical store receipt retains full data without loss
        canon_receipt = self.store.get(receipt)['data']
        self.assertEqual(canon_receipt['checker_path'], '/opt/lean/bin/lean')
        self.assertEqual(canon_receipt['libraries'][0]['root'], '/opt/mathlib')
        self.assertEqual(len(canon_receipt['libraries'][0]['files']), 500)
        self.assertEqual(canon_receipt['result']['stdout'], large_stdout)
        self.assertEqual(canon_receipt['result']['stderr'], large_stderr)

    def test_review_checks_reject_collection_coercion(self):
        target = self.claim()
        tasks = Tasks(self.r)

        # 1. Tasks.create rejects dict / string / non-list checks
        for invalid in [{'validity': True}, 'validity', 123]:
            with self.assertRaisesRegex(StateError, 'assessment obligations'):
                tasks.create('referee', target, checks=invalid, mandate='Audit target')

        # 2. Worker response with dict checks is rejected
        task = self.task(target, checks=['validity'])
        run = self.launch(task, conversation='conv-review-1')
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
                             'outcome': 'review', 'verdict': 'pass', 'checks': {'validity': True}, 'reasoning': 'audit'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'conv-review-1', 'status': 'SUCCESS', 'response': output}))
        with self.assertRaisesRegex(StateError, 'Worker checks are malformed or outside its task contract'):
            tasks.finish(run, artifact, receipt, outcome='review', verdict='pass', checks=['validity'])

        # 3. Caller passing dict checks to finish is rejected
        task2 = self.task(target, checks=['validity'])
        run2 = self.launch(task2, conversation='conv-review-2')
        output2 = json.dumps({'task_id': task2, 'packet_hash': tasks.packet(task2)['packet_hash'],
                              'outcome': 'review', 'verdict': 'pass', 'checks': ['validity'], 'reasoning': 'audit'})
        artifact2 = self.r.artifact(output2)
        receipt2 = self.r.artifact(json.dumps({'conversation_id': 'conv-review-2', 'status': 'SUCCESS', 'response': output2}))
        with self.assertRaisesRegex(StateError, "Recorded result differs from the worker's declared assessment"):
            tasks.finish(run2, artifact2, receipt2, outcome='review', verdict='pass', checks={'validity': True})

    def test_task_create_background_and_extend_added_reject_collection_coercion(self):
        target = self.claim()
        tasks = Tasks(self.r)
        d1 = self.r.definition("D1", "First definition")
        d2 = self.r.definition("D2", "Second definition")
        base_rev = self.store.revision
        base_count = len(self.store.records())

        # 1. Tasks.create background must be an exact list or None
        for invalid in [{d1: False}, d1, 123, [123], [""]]:
            with self.assertRaisesRegex(StateError, "background must be an exact list"):
                tasks.create("prover", target, checks=["argument"], mandate="prove", background=invalid)

        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)

        task = tasks.create("prover", target, checks=["argument"], mandate="prove")

        # 2. Tasks.extend added must be an exact nonempty list of strings
        for invalid in [{d2: False}, d2, 123, [], [123], [""]]:
            with self.assertRaisesRegex(StateError, "added must be a nonempty list"):
                tasks.extend(task, invalid, "Need D2")

        # 3. Valid extend succeeds
        extended = tasks.extend(task, [d2], "Need D2")
        self.assertIn(d2, tasks.packet(extended)["records"])

    def test_extend_becomes_informed_rejects_non_boolean_and_preserves_state(self):
        target = self.claim()
        tasks = Tasks(self.r)
        inference = self.r.inference(target, [], self.proof, 'author')
        task = tasks.create('prover', target, checks=['argument'], mandate='prove', independence='blind')

        base_rev = self.store.revision
        base_count = len(self.store.records())

        # Non-boolean inputs must be rejected with StateError
        for invalid in ["false", "true", 0, 1, None, [], {}]:
            with self.assertRaisesRegex(StateError, "becomes_informed must be an exact boolean"):
                tasks.extend(task, [inference], "Extend", becomes_informed=invalid)

        # Original task remains blind, no new task, store revision/records unchanged
        self.assertEqual(tasks.packet(task)["independence"], "blind")
        self.assertEqual(self.store.revision, base_rev)
        self.assertEqual(len(self.store.records()), base_count)

        # becomes_informed=False still rejected because history requires informed transition
        with self.assertRaises(StateError):
            tasks.extend(task, [inference], "Extend", becomes_informed=False)
        self.assertEqual(tasks.packet(task)["independence"], "blind")
        self.assertEqual(self.store.revision, base_rev)

        # becomes_informed=True explicitly succeeds and transitions to informed
        revised = tasks.extend(task, [inference], "Explicit transition", becomes_informed=True)
        self.assertEqual(tasks.packet(revised)["independence"], "informed")
        self.assertIn(inference, tasks.packet(revised)["records"])



