import sqlite3
import tempfile
import unittest
from pathlib import Path

from mathtrace.store import Store, StateError, StaleState, digest


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'state.sqlite'
        self.store = Store(self.path, create=True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_failed_operation_leaves_no_partial_records_or_events(self):
        before = self.store.export()
        with self.assertRaises(StateError):
            with self.store.transaction():
                self.store.put('claim', {'statement': 'P'}, record_id='P')
                self.store.put('claim', {'statement': 'Q'}, record_id='P')
        self.assertEqual(before, self.store.export())

    def test_new_process_sees_committed_evidence_and_health(self):
        with self.store.transaction():
            record = self.store.put('claim', {'statement': 'P', 'assumptions': ['A']})
            self.store.decide(record, 'withdrawn', {'reason': 'support lost, not refutation'})
        with Store(self.path) as resumed:
            self.assertEqual(resumed.get(record)['data']['statement'], 'P')
            self.assertEqual(resumed.status(record), 'withdrawn')
            self.assertTrue(resumed.health()['ok'])

    def test_stale_transaction_rejected_before_mutation(self):
        old = self.store.revision
        with self.store.transaction():
            self.store.put('claim', {'statement': 'P'})
        with self.assertRaises(StaleState):
            with self.store.transaction(old):
                self.store.put('claim', {'statement': 'Q'})
        self.assertEqual(len(self.store.records()), 1)

    def test_records_cannot_be_rewritten_even_by_direct_sql(self):
        with self.store.transaction():
            identifier = self.store.put('artifact', {'text': 'original proof'})
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute('UPDATE records SET payload=? WHERE id=?', ('{}', identifier))
        self.assertTrue(self.store.health()['ok'])

    def test_projection_tampering_is_detected(self):
        with self.store.transaction():
            identifier = self.store.put('claim', {'statement': 'unproved'})
        self.store.db.execute('UPDATE decisions SET status=? WHERE target=?', ('accepted', identifier))
        self.assertFalse(self.store.health()['ok'])

    def test_idempotency_key_binds_payload(self):
        fp = digest({'operation': 'register', 'statement': 'P'})
        with self.store.transaction():
            self.assertIsNone(self.store.request('request-1', fp))
            self.store.finish_request('request-1', fp, {'record': 'P'})
        with self.store.transaction():
            self.assertEqual(self.store.request('request-1', fp), {'record': 'P'})
            with self.assertRaises(StateError):
                self.store.request('request-1', digest({'statement': 'Q'}))

    def test_write_requires_transaction(self):
        with self.assertRaises(StateError):
            self.store.put('claim', {'statement': 'P'})

    def test_unknown_schema_is_not_silently_migrated(self):
        self.store.db.execute("UPDATE metadata SET value='999' WHERE key='schema'")
        with self.assertRaises(StateError):
            Store(self.path)

    def test_export_at_reconstructs_exact_historical_state(self):
        rev1 = self.store.revision
        snap1 = self.store.export()
        self.assertEqual(self.store.export_at(rev1), snap1)

        with self.store.transaction():
            p = self.store.put('claim', {'statement': 'P'})
        rev2 = self.store.revision
        snap2 = self.store.export()
        self.assertEqual(self.store.export_at(rev2), snap2)

        with self.store.transaction():
            self.store.decide(p, 'withdrawn', {'reason': 'superseded'})
        rev3 = self.store.revision
        snap3 = self.store.export()
        self.assertEqual(self.store.export_at(rev3), snap3)

        # Historical reconstruction matches past exports
        self.assertEqual(self.store.export_at(rev1), snap1)
        self.assertEqual(self.store.export_at(rev2), snap2)

        # Bounds validation
        self.assertEqual(self.store.export_at(0)['records'], [])
        with self.assertRaises(StateError):
            self.store.export_at(-1)
        with self.assertRaises(StateError):
            self.store.export_at(rev3 + 1)


if __name__ == '__main__':
    unittest.main()
