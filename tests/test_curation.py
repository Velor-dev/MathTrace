"""Root advisory pipeline; reviews/checker fixtures are synthetic bookkeeping."""
import unittest
from copy import deepcopy

import test_research
from mathtrace.advisory import Advisory
from mathtrace.campaign import Campaign
from mathtrace.context import Tasks
from mathtrace.coordination import Coordination
from mathtrace.curation import Curation
from mathtrace.orchestration import Orchestration
from mathtrace.store import StateError


class CurationTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    accept = test_research.ResearchTests.accept
    review = test_research.ResearchTests.review

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.a, self.cu = Advisory(self.r), Curation(self.r)
        self.target = self.claim()
        self.route = self.r.route(self.target, 'Exact researched mechanism', family='direct')
        event = self.a._latest(self.route)
        self.boundary = self.a.boundary(event['revision'], event['hash'], target=self.route)

    def extract(self, **changes):
        args = dict(target=self.target, boundary=self.boundary, summary='The selected mechanism has an exact residual',
            sources=[self.target], category='failed-mechanism', applicability='This selected mechanism on the exact target',
            reopen_condition='A reviewed estimate closes the residual', author='root', expected=self.store.revision,
            request_id='extract')
        args.update(changes)
        return self.cu.extract(**args)

    def curate(self, candidate):
        return self.cu.curate(candidate, reason='Preserve useful scoped advice', author='root',
            expected=self.store.revision, request_id='curate-' + candidate)

    def admit(self, learning, **changes):
        args = dict(learning=learning, target=self.target, applicability='Advisory route choice only',
            reason='Explicit informed strategy input', author='root', expected=self.store.revision,
            request_id='admit-' + learning)
        args.update(changes)
        return self.cu.admit(**args)

    def test_extraction_curation_admission_is_explicit_current_idempotent_and_never_proof(self):
        candidate = self.extract()['candidate']
        Orchestration(self.r).checkpoint('Unrelated checkpoint')
        recovered = self.extract(expected=0, request_id='new-extraction-request')
        self.assertEqual(recovered['candidate'], candidate)
        self.assertTrue(recovered['current'])
        curated = self.curate(candidate)
        learning = curated['learning']
        self.assertTrue(curated['current'])
        self.assertTrue(self.r.learning_current(learning))
        self.assertEqual(self.cu.selection(self.target)['selected'], [])
        self.admit(learning)
        packet = Tasks(self.r).packet(Orchestration(self.r).strategize(self.target))
        self.assertIn(learning, packet['records'])
        self.assertTrue(packet['records'][learning]['data']['source_semantics']['omitted'])
        self.assertEqual(packet['advisory_learning']['selected'][0]['learning'], learning)
        blind = Tasks(self.r).packet(Tasks(self.r).create('scout', self.target, checks=['exploration'], mandate='Independent route'))
        self.assertNotIn(learning, blind['records'])
        self.assertNotIn('advisory_learning', blind)
        self.assertEqual(self.r.claim_state(self.target)['state'], 'unsupported')

    def test_actual_source_changes_stale_candidate_lesson_admission_and_strategy_basis(self):
        candidate = self.extract()['candidate']
        learning = self.curate(candidate)['learning']
        admission = self.admit(learning)['admission']
        intent = Coordination(self.r).prepare_work(self.target, 'strategy', 'one', self.target, 'strategist',
            ['route-portfolio'], 'Choose complementary routes', 'Root selection rationale',
            expected=self.store.revision, request_id='strategy', independence='informed')
        self.assertTrue(Coordination(self.r).inspect_work(intent['intent'])['basis_unchanged'])
        self.accept(self.target)
        self.assertFalse(self.cu.candidate_current(candidate))
        self.assertFalse(self.r.learning_current(learning))
        self.assertFalse(self.cu.admission_current(admission))
        self.assertEqual(self.cu.selection(self.target)['excluded_stale_admissions'], 1)
        self.assertFalse(Coordination(self.r).inspect_work(intent['intent'])['basis_unchanged'])
        self.assertFalse(self.extract(expected=0)['current'])

    def test_manual_lesson_requires_explicit_target_admission_and_selection_has_omission_counts(self):
        manual = self.r.learning('Manual scoped observation', [self.target], category='structural-insight', reopen_condition='Source changes')
        self.assertEqual(self.cu.selection(self.target)['selected'], [])
        self.admit(manual)
        other = self.claim('Other exact target')
        self.assertEqual(self.cu.selection(other)['selected'], [])
        omitted = self.cu.selection(self.target, max_items=0)
        self.assertEqual(omitted['selected'], [])
        self.assertEqual(omitted['omitted_current'], 1)

    def test_withdrawn_admission_blocks_carried_automatic_advice_without_removing_history(self):
        lesson = self.curate(self.extract()['candidate'])['learning']
        admission = self.admit(lesson)['admission']
        task = Orchestration(self.r).strategize(self.target)
        self.r.withdraw(admission, 'Root target admission revoked')
        self.assertTrue(self.r.learning_current(lesson))
        self.assertEqual(self.cu.selection(self.target)['selected'], [])
        definition = self.r.definition('Extra', 'Exact definition')
        with self.assertRaises(StateError):
            Tasks(self.r).extend(task, [definition], 'New context')
        self.assertIn(lesson, Tasks(self.r).packet(task)['records'])

    def test_decline_and_checkpoint_selection_remain_advisory(self):
        candidate = self.extract()['candidate']
        declined = self.cu.curate(candidate, disposition='decline', reason='Too speculative', author='root',
            expected=self.store.revision, request_id='decline')
        self.assertIsNone(declined['learning'])
        checkpoint = Orchestration(self.r).checkpoint('Selected exact research checkpoint')
        row = self.store.db.execute("SELECT seq,hash FROM events WHERE type='registered' AND target=?", (checkpoint,)).fetchone()
        boundary = self.a.boundary(row['seq'], row['hash'], target=checkpoint)
        self.assertTrue(self.extract(boundary=boundary, request_id='checkpoint')['current'])

    def test_execution_assessment_requires_actual_outcome_and_boundary_sources(self):
        import test_conditions
        receipt, _ = test_conditions.ConditionTests.formal(self)
        target = self.store.get(receipt)['data']['target']
        execution = self.store.get(receipt)['data']['execution']
        assessed = Orchestration(self.r).assess_execution(execution, 'Compilation finished; mapping remains unqualified', [],
            'Exact independent qualification supplied')
        row = self.store.db.execute('SELECT hash FROM events WHERE seq=?', (assessed['assessment_revision'],)).fetchone()
        boundary = self.a.boundary(assessed['assessment_revision'], row['hash'], target=execution)
        candidate = self.extract(target=target, boundary=boundary, sources=[], request_id='execution')['candidate']
        d = self.store.get(candidate)['data']
        self.assertIn(receipt, d['sources'])
        observation = self.store.get(boundary)['data']['event']['payload']['observation']
        self.assertIn(observation, d['sources'])
        malformed = deepcopy(d)
        malformed['sources'].remove(observation)
        from mathtrace.store import digest
        malformed['basis'].pop(observation)
        malformed['basis_hash'] = digest(malformed['basis'])
        with self.store.transaction():
            imported = self.store.put('learning_candidate', malformed)
        self.assertFalse(self.cu.candidate_current(imported))

    def test_imported_empty_sources_and_incomplete_admission_fail_closed(self):
        learning = self.curate(self.extract()['candidate'])['learning']
        data = deepcopy(self.store.get(learning)['data'])
        data['sources'], data['source_status'], data['source_semantics'] = {}, {}, {}
        with self.store.transaction():
            malformed = self.store.put('learning', data)
        self.assertFalse(self.r.learning_current(malformed))
        admission = self.admit(learning)['admission']
        data = deepcopy(self.store.get(admission)['data'])
        data['applicability'] = ''
        with self.store.transaction():
            imported = self.store.put('learning_admission', data)
            self.store.decide(imported, 'active', {'reason': 'Malformed imported fixture'})
        self.assertFalse(self.cu.admission_current(imported))

    def test_native_completion_extraction_pins_response_and_receipt_and_keeps_historical_authenticity(self):
        self.review(self.target, ['scope'])
        run = self.last_run
        row = self.store.db.execute("SELECT seq,hash,payload FROM events WHERE type='completion-qualification' AND target=?", (run,)).fetchone()
        boundary = self.a.boundary(row['seq'], row['hash'], target=run)
        candidate = self.extract(boundary=boundary, sources=[], request_id='completion')['candidate']
        import json
        result = self.store.get(json.loads(row['payload'])['result'])['data']
        sources = self.store.get(candidate)['data']['sources']
        self.assertIn(result['artifact'], sources)
        self.assertIn(result['host_receipt'], sources)
        self.r.withdraw(run, 'Historical completion remains readable after attribution withdrawal')
        self.assertEqual(self.a.boundary_data(boundary)['event']['revision'], row['seq'])

    def test_stale_origin_cannot_rebase_and_candidate_lineage_is_not_a_mutable_dependency(self):
        candidate = self.extract()['candidate']
        lesson = self.curate(candidate)['learning']
        d = self.store.get(lesson)['data']
        self.accept(self.target)
        with self.assertRaises(StateError):
            self.r.learning(d['summary'], list(d['sources']), category=d['category'], reopen_condition=d['reopen_condition'],
                target=d['target'], applicability=d['applicability'], origin=d['origin'])
        fresh = self.extract(request_id='fresh')['candidate']
        current = self.curate(fresh)['learning']
        self.r.withdraw(fresh, 'Proposal lineage withdrawal is not withdrawal of the curated advice')
        self.assertTrue(self.r.learning_current(current))

    def test_declined_malformed_admission_and_packet_are_not_current_inputs(self):
        candidate = self.extract()['candidate']
        self.cu.curate(candidate, disposition='decline', reason='Speculative', author='root',
            expected=self.store.revision, request_id='decline')
        self.assertFalse(self.cu.candidate_current(candidate))
        with self.store.transaction():
            self.store.put('learning_admission', {'profile': 'source-bound-local-curation-v1'})
        self.assertEqual(self.cu.selection(self.target)['excluded_stale_admissions'], 1)
        task = Tasks(self.r).create('scout', self.target, checks=['exploration'], mandate='Exact exploration')
        d = deepcopy(self.store.get(task)['data'])
        d['packet_hash'] = 'forged'
        with self.store.transaction():
            bad = self.store.put('task', d)
        with self.assertRaises(StateError):
            Tasks(self.r).packet(bad)
