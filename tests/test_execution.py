"""Execution identity/recovery tests, including one actual isolated crash window."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import test_research
from mathtrace.campaign import Campaign
from mathtrace.evidence import Evidence
from mathtrace.execution import Executions
from mathtrace.orchestration import Orchestration
from mathtrace.store import Store, StateError, digest


class ExecutionTests(unittest.TestCase):
    tearDown = test_research.ResearchTests.tearDown
    claim = test_research.ResearchTests.claim
    review = test_research.ResearchTests.review

    def setUp(self):
        test_research.ResearchTests.setUp(self)
        self.r = Campaign(self.store)
        self.evidence = Evidence(self.r)

    def plan(self):
        source = self.r.artifact("print('real recovered result')")
        plan = self.evidence.experiment(self.claim(), source, 'One exact computation', author='worker')
        self.review(plan, ['execution-scope', 'source-integrity'])
        return plan, source

    def observed(self):
        return {'execution_environment': {'backend': 'explicitly-mocked-boundary'},
                'stdout': 'mock observation', 'stderr': '', 'exit_code': 0, 'timed_out': False,
                'namespace_setup': None, 'isolation_established': False}

    def test_intent_commits_before_call_and_repeats_do_not_execute_again(self):
        plan, _ = self.plan()
        calls = []
        def runner(*args, journal):
            execution = self.store.get(journal['execution'], 'execution')
            self.assertEqual(execution['data']['plan'], plan)
            self.assertEqual(self.store.status(execution['id']), 'pending')
            self.assertFalse(self.store.db.in_transaction)
            calls.append(execution['id'])
            return test_research.recorded_result(self.observed(), journal, mode='direct')
        with patch('mathtrace.evidence.invoke', side_effect=runner):
            receipt = self.evidence.run_experiment(plan)
            self.assertEqual(self.evidence.run_experiment(plan), receipt)
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan, timeout=120)
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan, rerun_of=calls[0])
            second = self.evidence.run_experiment(plan, timeout=120, rerun_of=calls[0], reason='Reproduce with more time')
            self.assertNotEqual(second, receipt)
            self.assertEqual(self.evidence.run_experiment(plan, timeout=120, rerun_of=calls[0],
                                                       reason='Reproduce with more time'), second)
        self.assertEqual(len(calls), 2)
        actions = Orchestration(self.r).next_actions()['actions']
        self.assertFalse(any(a.get('target') == plan and a['action'] == 'inspect-experiment-plan' for a in actions))

    def test_uncertain_attempt_blocks_retry_and_remains_visible(self):
        plan, _ = self.plan()
        with patch('mathtrace.evidence.invoke', side_effect=StateError('Transport timeout')) as runner:
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan)
            execution = self.store.records('execution')[0]['id']
            self.assertEqual(self.store.status(execution), 'uncertain')
            for parameters in ({}, {'rerun_of': execution, 'reason': 'Guess it stopped'}):
                with self.assertRaises(StateError):
                    self.evidence.run_experiment(plan, **parameters)
            self.assertEqual(runner.call_count, 1)
        state = self.evidence.inspect_execution(execution)
        self.assertFalse(state['retry_authorized'])
        self.assertEqual(state['liveness'], 'not-established')
        self.assertIn('inspect-execution', [a['action'] for a in Orchestration(self.r).next_actions()['actions']])
        self.assertEqual([r for r in self.store.records('experiment') if r['data'].get('plan')], [])

    def test_other_connection_cannot_launch_an_already_pending_attempt(self):
        plan, _ = self.plan()
        def runner(*args, journal):
            with Store(self.store.path) as second:
                with self.assertRaises(StateError):
                    Evidence(Campaign(second)).run_experiment(plan)
            return test_research.recorded_result(self.observed(), journal, mode='direct')
        with patch('mathtrace.evidence.invoke', side_effect=runner) as process:
            self.evidence.run_experiment(plan)
        self.assertEqual(process.call_count, 1)
        self.assertEqual(len(self.store.records('execution')), 1)

    def test_terminal_output_is_retained_when_source_is_withdrawn_mid_run(self):
        plan, source = self.plan()
        def runner(*args, journal):
            self.r.withdraw(source, 'Source provenance was retracted during execution')
            return test_research.recorded_result(self.observed(), journal, mode='direct')
        with patch('mathtrace.evidence.invoke', side_effect=runner):
            receipt = self.evidence.run_experiment(plan)
        execution = self.store.get(receipt)['data']['execution']
        self.assertEqual(self.store.status(execution), 'completed')
        self.assertEqual(self.store.status(receipt), 'observed')
        self.assertFalse(self.r._scope_current(receipt))
        self.assertEqual(self.evidence.recover_execution(execution)['receipt'], receipt)

    def test_real_recorder_output_survives_root_interruption_and_recovers_once(self):
        plan, _ = self.plan()
        with patch.object(self.evidence, '_complete_execution', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.evidence.run_experiment(plan)
        execution = self.store.records('execution')[0]['id']
        self.assertEqual(self.store.status(execution), 'pending')
        self.assertTrue(self.evidence.inspect_execution(execution)['terminal_available'])
        with Store(self.store.path) as reopened:
            resumed = Evidence(Campaign(reopened))
            with patch('mathtrace.evidence.invoke', side_effect=AssertionError('Recovery must not run code')):
                receipt = resumed.recover_execution(execution)['receipt']
                self.assertEqual(resumed.run_experiment(plan), receipt)
                self.assertEqual(resumed.recover_execution(execution)['receipt'], receipt)
            self.assertEqual(reopened.get(receipt)['data']['result']['stdout'].strip(), 'real recovered result')
            self.assertEqual(len([r for r in reopened.records('experiment') if r['data'].get('plan')]), 1)

    def test_backend_error_requires_observed_teardown_before_rerun(self):
        plan, _ = self.plan()
        def failed_runner(*args, journal):
            directory = Path(journal['directory'])
            directory.mkdir(parents=True)
            started = {k: journal[k] for k in ('execution', 'request_hash')}
            started.update(execution_mode='direct', execution_protocol='mode-aware-execution-v1')
            terminal = {**started, 'producer': started, 'producer_hash': digest(started), 'ok': False,
                        'teardown': 'recorder-owned-processes-waited', 'error': 'Mocked setup failure'}
            (directory / 'started.json').write_text(json.dumps(started))
            (directory / 'terminal.json').write_text(json.dumps(terminal))
            raise StateError('Mocked setup failure')
        with patch('mathtrace.evidence.invoke', side_effect=failed_runner):
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan)
        execution = self.store.records('execution')[0]['id']
        self.assertEqual(self.store.status(execution), 'failed')
        self.assertFalse(self.evidence.recover_execution(execution)['ok'])
        with patch('mathtrace.evidence.invoke', side_effect=test_research.recorded_runner(self.observed())):
            self.evidence.run_experiment(plan, rerun_of=execution, reason='Repair setup and deliberately repeat')

    def test_exact_terminal_observation_is_idempotent_and_conflicting_output_is_rejected(self):
        plan, _ = self.plan()
        with patch('mathtrace.evidence.invoke', side_effect=test_research.recorded_runner(self.observed())):
            receipt = self.evidence.run_experiment(plan)
        execution = self.store.get(receipt)['data']['execution']
        terminal = self.evidence.recover_execution(execution)
        envelope = json.loads(self.store.get(terminal['observation'])['data']['text'])
        executions = Executions(self.r)
        writer = lambda *_: self.fail('Duplicate terminal output must not write a new receipt')
        self.assertEqual(executions.terminal(execution, envelope, writer)['receipt'], receipt)
        revision = self.store.revision
        envelope['result']['stdout'] = 'Different result under same attempt ID'
        with self.assertRaises(StateError):
            executions.terminal(execution, envelope, writer)
        self.assertEqual(self.store.revision, revision)

    def test_invalid_timeout_and_enclosing_transactions_cannot_leave_launches(self):
        plan, _ = self.plan()
        with patch('mathtrace.evidence.invoke') as process:
            for invalid in (True, False, '60', float('nan'), float('inf'), 0, -1, 86401):
                with self.assertRaises(StateError):
                    self.evidence.run_experiment(plan, timeout=invalid)
            with self.store.transaction():
                with self.assertRaises(StateError):
                    self.evidence.run_experiment(plan)
            self.assertFalse(process.called)
        self.assertEqual(self.store.records('execution'), [])

    def test_absent_producer_cannot_close_a_pending_attempt(self):
        plan, _ = self.plan()
        with patch('mathtrace.evidence.invoke', return_value=self.observed()):
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan)
        execution = self.store.records('execution')[0]['id']
        self.assertEqual(self.store.status(execution), 'uncertain')
        self.assertNotIn('terminal', self.evidence.inspect_execution(execution))
        self.assertEqual([r for r in self.store.records('experiment') if r['data'].get('plan')], [])

    def test_namespace_setup_failure_is_retained_as_failed_execution_evidence(self):
        plan, _ = self.plan()
        def runner(*args, journal):
            payload = {**self.observed(), 'namespace_setup': None, 'exit_code': 1, 'stderr': 'Setup failed'}
            returned = test_research.recorded_result(payload, journal, mode='bubblewrap')
            envelope = {**returned['_producer'], 'result': payload}
            directory = Path(journal['directory'])
            directory.mkdir(parents=True)
            (directory / 'started.json').write_text(json.dumps(envelope['producer']))
            (directory / 'terminal.json').write_text(json.dumps(envelope))
            raise StateError('Namespace setup did not complete')
        with patch('mathtrace.evidence.invoke', side_effect=runner):
            with self.assertRaises(StateError):
                self.evidence.run_experiment(plan, execution_mode='bubblewrap')
        execution = self.store.records('execution')[0]['id']
        receipt = self.evidence.recover_execution(execution)['receipt']
        self.assertEqual(self.store.status(receipt), 'failed')
        self.assertEqual(self.store.get(receipt)['data']['evidence_class'], 'execution-failure')
        self.assertFalse(self.store.get(receipt)['data']['isolation_established'])
        self.assertTrue(any(a.get('receipt') == receipt and a['action'] == 'assess-execution-failure'
                            for a in Orchestration(self.r).next_actions()['actions']))

    def test_withdrawn_execution_preserves_output_without_restoring_attribution(self):
        plan, _ = self.plan()
        def runner(*args, journal):
            self.r.withdraw(journal['execution'], 'Execution attribution retracted while process ran')
            return test_research.recorded_result(self.observed(), journal, mode='direct')
        with patch('mathtrace.evidence.invoke', side_effect=runner):
            receipt = self.evidence.run_experiment(plan)
        execution = self.store.get(receipt)['data']['execution']
        self.assertEqual(self.store.status(execution), 'withdrawn')
        self.assertEqual(self.evidence.inspect_execution(execution)['terminal']['receipt'], receipt)
        self.assertFalse(self.evidence.recover_execution(execution)['attribution_current'])
        self.assertFalse(self.r._scope_current(receipt))
        with self.assertRaises(StateError):
            self.evidence.run_experiment(plan, rerun_of=execution, reason='Attempt to bypass retraction')

    def test_execution_assessment_preserves_bounded_advisory_knowledge(self):
        plan, _ = self.plan()
        target = self.store.get(plan)['data']['target']
        with patch('mathtrace.evidence.invoke', side_effect=test_research.recorded_runner(self.observed())):
            receipt = self.evidence.run_experiment(plan)
        execution = self.store.get(receipt)['data']['execution']
        controller = Orchestration(self.r)
        with self.assertRaises(StateError):
            controller.assess_execution(execution, 'No conclusion', [self.claim('Unrelated')], 'New evidence')
        response = controller.assess_execution(execution, 'Finite observation; universal statement unresolved', [],
                                               'A proof connecting the finite result to the full target')
        self.assertEqual(controller.assess_execution(execution, 'Finite observation; universal statement unresolved', [],
            'A proof connecting the finite result to the full target'), response)
        self.assertFalse(response['mathematical_acceptance'])
        self.assertFalse(any(a.get('execution') == execution for a in controller.next_actions()['actions']))
        self.r.withdraw(execution, 'Later provenance retraction')
        certificate = self.r.portfolio(target)['dispositions'][-1]
        self.assertEqual(certificate['outcome'], 'observed')
        self.assertFalse(certificate['source_records_current'])
        packet = controller.tasks.packet(controller.strategize(target))
        self.assertEqual(packet['research_state']['dispositions'][-1]['execution'], execution)


if __name__ == '__main__':
    unittest.main()
