import json
import unittest

import test_research
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class AdjudicationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review
    accept = test_research.ResearchTests.accept

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)

    def case(self, finding, disposition='dismissed'):
        response = self.r.artifact('Self-contained response to the exact challenge; synthetic protocol fixture.')
        return self.r.adjudication(finding, response, disposition=disposition, author='root')

    def test_negative_retraction_and_legacy_withdrawal_never_unblock(self):
        target = self.claim()
        inference = self.accept(target)
        negative = self.review(inference, verdict='fail')
        self.r.withdraw(negative, 'Wrongly attributed producer record')
        self.assertEqual(self.store.status(negative), 'provenance-retracted')
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertTrue(self.r.finding_blocking(negative))
        # Existing stores with old generic-withdrawal decisions are conservative too.
        with self.store.transaction():
            self.store.decide(negative, 'withdrawn', {'reason': 'Legacy retraction'})
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.assertIn({'action': 'adjudicate-review', 'review': negative},
                      Orchestration(self.r).next_actions()['actions'])
        objection = self.r.objection(inference, self.proof, 'hunter')
        self.r.withdraw(objection, 'Reporter retracted provenance')
        self.assertTrue(self.r.finding_blocking(objection))
        self.assertIn(objection, self.r.progress()['open_objections'])

    def test_dismissal_requires_exact_case_and_current_recorded_witnesses(self):
        target = self.claim()
        inference = self.accept(target)
        finding = self.review(inference, verdict='fail')
        case = self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        self.assertTrue(any(a['action'] == 'review-adjudication-case' and a.get('case') == case
                            for a in Orchestration(self.r).next_actions()['actions']))
        with self.assertRaises(StateError):
            self.r.adjudicate(case, expected=self.store.revision)
        witness = self.review(case, checks, role='adjudicator')
        self.assertTrue(any(a['action'] == 'adjudicate-case' and a.get('case') == case
                            for a in Orchestration(self.r).next_actions()['actions']))
        resolution = self.r.adjudicate(case, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertEqual(self.r.claim_state(target)['state'], 'supported')
        self.r.withdraw(witness, 'Adjudicator evidence retracted')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertEqual(self.r.claim_state(target)['state'], 'unsupported')
        self.review(case, checks, role='adjudicator')
        self.assertTrue(self.r.finding_blocking(finding))  # no witness substitution
        new_case = self.case(finding)
        self.review(new_case, checks, role='adjudicator')
        self.r.adjudicate(new_case, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertEqual(self.store.get(resolution)['data']['reviews'], [witness])

    def test_toolchain_finding_has_exact_subject_context_and_can_be_adjudicated(self):
        with self.store.transaction():
            toolchain = self.store.put('toolchain', {'root': '/private/host', 'files': {'bin/lean': 'a' * 64},
                'release': 'v4.30.0', 'publisher_archive': {'sha256': 'b' * 64}})
            self.store.decide(toolchain, 'installed', {'reason': 'Synthetic toolchain'})
        objection = self.r.objection(toolchain, self.proof, 'environment-checker')
        case = self.case(objection)
        tasks = Tasks(self.r)
        task = tasks.create('adjudicator', case, independence='informed',
            checks=['finding-scope', 'counterargument', 'dismissed'], mandate='Assess exact environment objection')
        packet = tasks.packet(task)
        self.assertIsNone(packet['claim'])
        self.assertEqual(packet['context_type'], 'infrastructure')
        self.assertIn(objection, packet['records'])
        self.assertIn(toolchain, packet['records'])
        self.assertIn(self.store.get(case)['data']['response'], packet['records'])
        self.assertNotIn('/private/host', json.dumps(packet))
        self.assertTrue(self.r._blocked(toolchain))
        self.review(case, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator')
        self.r.resolve_objection(objection, 'dismissed', case=case, expected=self.store.revision)
        self.assertFalse(self.r._blocked(toolchain))
        self.assertEqual(self.store.status(toolchain), 'installed')

    def test_adjudication_is_informed_and_does_not_replace_proof_review(self):
        target = self.claim()
        inference = self.r.inference(target, [], self.proof, 'author')
        objection = self.r.objection(inference, self.proof, 'hunter')
        case = self.case(objection)
        tasks = Tasks(self.r)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        with self.assertRaises(StateError):
            tasks.create('referee', case, independence='informed', checks=checks, mandate='Cannot substitute role')
        with self.assertRaises(StateError):
            tasks.create('adjudicator', case, checks=checks, mandate='Cannot hide exposure')
        review = self.review(case, checks, role='adjudicator')
        self.assertEqual(self.store.get(review)['data']['exposure'], 'informed')
        self.r.adjudicate(case, expected=self.store.revision)
        with self.assertRaises(StateError):
            self.r.promote(inference, expected=self.store.revision, request_id='needs-real-proof-review')
        self.review(inference)
        self.r.promote(inference, expected=self.store.revision, request_id='after-proof-review')

    def test_case_failure_is_not_outvoted_and_response_or_resolution_retraction_reopens(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        case = self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        for _ in range(3):
            self.review(case, checks, role='adjudicator')
        negative = self.review(case, checks, verdict='fail', role='adjudicator')
        self.r.withdraw(negative, 'Retract report')
        self.assertTrue(any(a['action'] == 'revise-adjudication-case' and a.get('case') == case
                            for a in Orchestration(self.r).next_actions()['actions']))
        with self.assertRaises(StateError):
            self.r.adjudicate(case, expected=self.store.revision)
        fresh = self.case(finding)
        self.review(fresh, checks, role='adjudicator')
        with self.assertRaises(StateError):
            self.r.adjudicate(fresh, expected=self.store.revision)
        self.assertIn(negative, self.store.get(fresh)['data']['prior_findings'])
        checks += ['prior-challenges']
        self.review(fresh, checks, role='adjudicator')
        resolution = self.r.adjudicate(fresh, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.r.withdraw(self.store.get(fresh)['data']['response'], 'Counterargument failed')
        self.assertTrue(self.r.finding_blocking(finding))
        next_case = self.case(finding)
        self.review(next_case, checks, role='adjudicator')
        latest = self.r.adjudicate(next_case, expected=self.store.revision)
        self.r.withdraw(latest, 'Resolution record retracted')
        self.assertTrue(self.r.finding_blocking(finding))
        self.assertEqual(self.store.status(resolution), 'proposed')

    def test_new_challenge_to_an_earlier_response_suspends_unaware_dismissal(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        first, second = self.case(finding), self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        self.review(second, checks, role='adjudicator')
        self.r.adjudicate(second, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        negative = self.review(first, checks, verdict='fail', role='adjudicator')
        self.assertTrue(self.r.finding_blocking(finding))
        repaired = self.case(finding)
        checks += ['prior-challenges']
        task = Tasks(self.r).create('adjudicator', repaired, independence='informed',
            checks=checks, mandate='Assess whether revised response escapes earlier defect')
        self.assertIn(negative, Tasks(self.r).packet(task)['records'])
        self.review(repaired, checks, role='adjudicator')
        self.r.adjudicate(repaired, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(self.r.finding_blocking(negative))  # old response remains defective

    def test_objection_to_exact_review_or_producer_evidence_suspends_dismissal(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        case = self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        witness = self.review(case, checks, role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        provenance_objection = self.r.objection(witness, self.proof, 'provenance-auditor')
        self.assertTrue(self.r.finding_blocking(finding))
        response_case = self.case(provenance_objection)
        self.review(response_case, checks, role='adjudicator')
        self.r.adjudicate(response_case, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        native_result = self.store.get(witness)['data']['provenance']['result']
        receipt = self.store.get(native_result)['data']['host_receipt']
        self.r.objection(receipt, self.proof, 'producer-auditor')
        self.assertTrue(self.r.finding_blocking(finding))

    def test_revised_response_must_address_prior_response_artifact_challenge(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        old_case = self.case(finding)
        response = self.store.get(old_case)['data']['response']
        challenge = self.r.objection(response, self.proof, 'counterargument-auditor')
        revised = self.case(finding)
        data = self.store.get(revised)['data']
        self.assertIn(challenge, data['prior_findings'])
        self.assertEqual(data['prior_cases'][challenge], old_case)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        task = Tasks(self.r).create('adjudicator', revised, independence='informed',
            checks=checks + ['prior-challenges'], mandate='Compare exact prior and revised responses')
        packet = Tasks(self.r).packet(task)
        self.assertEqual(packet['records'][response]['data']['text'], self.store.get(response)['data']['text'])
        self.review(revised, checks, role='adjudicator')
        with self.assertRaises(StateError):
            self.r.adjudicate(revised, expected=self.store.revision)
        self.review(revised, checks + ['prior-challenges'], role='adjudicator')
        self.r.adjudicate(revised, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(self.r.finding_blocking(challenge))

    def test_reported_capture_extra_exposure_and_party_identity_do_not_qualify(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        case = self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        review = self.review(case, checks, role='adjudicator')
        run = self.store.get(review)['data']['run_id']
        Tasks(self.r).expose(run, 'other-verdict', self.proof, 'Untracked verdict after packet dispatch')
        with self.assertRaises(StateError):
            self.r.adjudicate(case, expected=self.store.revision)
        party = self.store.get(review)['data']['reviewer']
        other_case = self.r.adjudication(finding, self.proof, disposition='dismissed', author=party)
        # Fresh runs prevent actual conversation reuse; a case author cannot review their own case.
        self.assertIn(party, self.store.get(other_case)['data']['parties'])
        tasks = Tasks(self.r)
        task = tasks.create('adjudicator', other_case, independence='informed', checks=checks, mandate='Assess case')
        with self.assertRaisesRegex(StateError, 'already used'):
            tasks.start(task, party, host='antigravity', dispatch_evidence=self.proof, tools=[], inherited_history=False)
        run = tasks.start(task, 'operator-reported-adjudicator', host='antigravity',
                          dispatch_evidence=self.proof, tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
            'outcome': 'review', 'verdict': 'pass', 'checks': checks, 'reasoning': 'Operator-reported review'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'operator-reported-adjudicator',
                                             'status': 'SUCCESS', 'response': output}))
        tasks.finish(run, artifact, receipt, outcome='review', verdict='pass', checks=checks)
        self.r.review(other_case, 'operator-reported-adjudicator', run, 'pass', artifact, checks, exposure='informed')
        with self.assertRaisesRegex(StateError, 'coverage is incomplete'):
            self.r.adjudicate(other_case, expected=self.store.revision)

    def test_candidate_author_cannot_adjudicate_their_release_through_a_wrapper(self):
        import uuid
        target = self.claim()
        self.accept(target)
        author = str(uuid.uuid4())
        candidate = self.r.freeze(target, self.proof, author=author)
        self.review(candidate, ['full-proof', 'dependency-closure'])
        self.review(candidate, ['target-fidelity'], role='fidelity-auditor')
        self.review(candidate, ['falsification'], role='falsifier')
        self.r.audit_candidate(candidate, expected=self.store.revision)
        release = self.r.release(candidate, expected=self.store.revision, assurance='audited-informal')
        finding = self.r.objection(release, self.proof, 'hunter')
        case = self.case(finding)
        self.review(case, ['finding-scope', 'counterargument', 'dismissed'], role='adjudicator',
                    conversation_id=author)
        with self.assertRaisesRegex(StateError, 'coverage is incomplete'):
            self.r.adjudicate(case, expected=self.store.revision)
        self.assertTrue(self.r.finding_blocking(finding))

    def test_nonwitness_provenance_fault_does_not_inflate_case_scope(self):
        inference = self.accept(self.claim())
        finding = self.r.objection(inference, self.proof, 'hunter')
        case = self.case(finding)
        checks = ['finding-scope', 'counterargument', 'dismissed']
        self.review(case, checks, role='adjudicator')
        self.r.adjudicate(case, expected=self.store.revision)
        tasks = Tasks(self.r)
        task = tasks.create('adjudicator', case, independence='informed', checks=checks, mandate='Extra operator report')
        dispatch = self.r.artifact('Operator report, not qualified producer evidence')
        run = tasks.start(task, 'unqualified-extra-assessor', host='antigravity',
                          dispatch_evidence=dispatch, tools=[], inherited_history=False)
        output = json.dumps({'task_id': task, 'packet_hash': tasks.packet(task)['packet_hash'],
            'outcome': 'review', 'verdict': 'pass', 'checks': checks, 'reasoning': 'Unqualified extra opinion'})
        artifact = self.r.artifact(output)
        receipt = self.r.artifact(json.dumps({'conversation_id': 'unqualified-extra-assessor', 'status': 'SUCCESS', 'response': output}))
        tasks.finish(run, artifact, receipt, outcome='review', verdict='pass', checks=checks)
        self.r.review(case, 'unqualified-extra-assessor', run, 'pass', artifact, checks, exposure='informed')
        unrelated_fault = self.r.objection(dispatch, self.proof, 'producer-auditor')
        self.assertFalse(self.r.finding_blocking(finding))
        revised = self.case(finding)
        self.assertNotIn(unrelated_fault, self.store.get(revised)['data']['prior_findings'])
        self.review(revised, checks, role='adjudicator')
        self.r.adjudicate(revised, expected=self.store.revision)
        self.assertFalse(self.r.finding_blocking(finding))
        self.assertTrue(self.r.finding_blocking(unrelated_fault))


if __name__ == '__main__':
    unittest.main()
