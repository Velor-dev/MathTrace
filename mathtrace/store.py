"""Transactional immutable research records.

This module records evidence and decisions. It does not judge mathematical truth.
All mutations share a SQLite transaction and an append-only hash-chained event log.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
KINDS = frozenset({
    'route_decision', 'boundary_certificate', 'learning_candidate', 'learning_admission',
    "contract", "definition", "assumption", "claim", "inference", "artifact",
    "route", "obligation", "counterexample", "external_theorem", "application",
    "experiment", "background", "task", "dispatch", "run", "result", "native_failure", "native_conflict", "review", "objection", "adjudication", "resolution",
    "candidate", "toolchain", "formal_plan", "formal_receipt", "execution", "ingestion_failure", "work_intent", "completion_request", "completion_evidence", "fulfillment_certificate", "learning", "exposure", "release", "checkpoint",
})
ZERO_HASH = "0" * 64


class StateError(ValueError):
    """An operation would violate the research state contract."""


class InputContractError(StateError):
    """Pure input semantics failed; no transport/store/provenance diagnosis."""


class StaleState(StateError):
    """State changed since an operation was assessed."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """One campaign database. Workers should receive packets, not this object.

    Transaction serialization protects concurrent root requests. Host tool access
    must separately prevent worker writes; SQLite is not an authorization boundary.
    """

    def __init__(self, path: str | Path, *, create: bool = False):
        self.path = Path(path).resolve()
        if create:
            if self.path.exists():
                raise StateError(f"Campaign already exists: {self.path}")
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif not self.path.is_file():
            raise StateError(f"Campaign does not exist: {self.path}")
        self.db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute("PRAGMA foreign_keys=ON")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            if create:
                self._initialize()
            self._check_schema()
        except BaseException:
            self.db.close()
            raise

    def _initialize(self) -> None:
        self.db.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE records(
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                hash TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE events(
                seq INTEGER PRIMARY KEY, type TEXT NOT NULL, target TEXT,
                payload TEXT NOT NULL, created TEXT NOT NULL,
                previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TABLE decisions(
                target TEXT PRIMARY KEY REFERENCES records(id), status TEXT NOT NULL,
                event_seq INTEGER NOT NULL REFERENCES events(seq));
            CREATE TABLE requests(
                id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
            CREATE TRIGGER records_no_update BEFORE UPDATE ON records
                BEGIN SELECT RAISE(ABORT, 'immutable record'); END;
            CREATE TRIGGER records_no_delete BEFORE DELETE ON records
                BEGIN SELECT RAISE(ABORT, 'immutable record'); END;
            CREATE TRIGGER events_no_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'immutable event'); END;
            CREATE TRIGGER events_no_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'immutable event'); END;
            COMMIT;
        """)
        with self.transaction():
            self.db.execute("INSERT INTO metadata VALUES('schema',?)", (str(SCHEMA_VERSION),))
            self.event("initialized", None, {"schema": SCHEMA_VERSION})

    def _check_schema(self) -> None:
        try:
            row = self.db.execute("SELECT value FROM metadata WHERE key='schema'").fetchone()
        except sqlite3.DatabaseError as error:
            raise StateError("Not a MathTrace database") from error
        if not row or row["value"] != str(SCHEMA_VERSION):
            raise StateError("Unsupported campaign schema; do not mutate it")

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self, expected: int | None = None) -> Iterator[None]:
        if self.db.in_transaction:
            savepoint = 'nested_' + uuid.uuid4().hex
            self.db.execute(f'SAVEPOINT {savepoint}')
            try:
                if expected is not None and self.revision != expected:
                    raise StaleState(f'Expected snapshot {expected}; current snapshot {self.revision}')
                yield
                self.db.execute(f'RELEASE SAVEPOINT {savepoint}')
            except BaseException:
                self.db.execute(f'ROLLBACK TO SAVEPOINT {savepoint}')
                self.db.execute(f'RELEASE SAVEPOINT {savepoint}')
                raise
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if expected is not None and self.revision != expected:
                raise StaleState(f"Expected snapshot {expected}; current snapshot {self.revision}")
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _writing(self) -> None:
        if not self.db.in_transaction:
            raise StateError("Mutation requires an explicit transaction")

    @property
    def revision(self) -> int:
        return self.db.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]

    def event(self, event_type: str, target: str | None, data: dict) -> int:
        self._writing()
        previous = self.db.execute("SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq = previous["seq"] + 1 if previous else 1
        prev_hash = previous["hash"] if previous else ZERO_HASH
        stamp = now()
        body = {"seq": seq, "type": event_type, "target": target, "data": data,
                "created": stamp, "previous_hash": prev_hash}
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)",
                        (seq, event_type, target, canonical(data), stamp, prev_hash, digest(body)))
        return seq

    def put(self, kind: str, data: dict, *, record_id: str | None = None) -> str:
        self._writing()
        if kind not in KINDS or not isinstance(data, dict):
            raise StateError("Unknown record kind or non-object payload")
        identifier = record_id or f"{kind}-{uuid.uuid4().hex}"
        if not isinstance(identifier, str) or not identifier or len(identifier) > 160:
            raise StateError("Invalid record identity")
        body = {"id": identifier, "kind": kind, "data": data}
        try:
            self.db.execute("INSERT INTO records VALUES(?,?,?,?,?)",
                            (identifier, kind, canonical(data), digest(body), now()))
        except sqlite3.IntegrityError as error:
            raise StateError(f"Record already exists: {identifier}; create a new revision") from error
        seq = self.event("registered", identifier, {"kind": kind, "record_hash": digest(body)})
        self.db.execute("INSERT INTO decisions VALUES(?,?,?)", (identifier, "proposed", seq))
        return identifier

    def get(self, identifier: str, kind: str | None = None) -> dict:
        if not isinstance(identifier, str) or not identifier.strip():
            raise StateError('Record identity must be a nonempty string')
        row = self.db.execute("SELECT * FROM records WHERE id=?", (identifier,)).fetchone()
        if not row or (kind is not None and row["kind"] != kind):
            raise StateError(f"Missing {kind or 'record'}: {identifier}")
        data = json.loads(row["payload"])
        if digest({"id": row["id"], "kind": row["kind"], "data": data}) != row["hash"]:
            raise StateError(f"Corrupted record: {identifier}")
        return {"id": row["id"], "kind": row["kind"], "data": data,
                "hash": row["hash"], "created": row["created"]}

    def records(self, kind: str | None = None) -> list[dict]:
        rows = self.db.execute("SELECT id FROM records WHERE (? IS NULL OR kind=?) ORDER BY rowid",
                               (kind, kind)).fetchall()
        return [self.get(row["id"]) for row in rows]

    def status(self, identifier: str) -> str:
        if not isinstance(identifier, str) or not identifier.strip():
            raise StateError('Record identity must be a nonempty string')
        row = self.db.execute("SELECT d.status,e.type,e.payload,e.target FROM decisions d "
                              "JOIN events e ON e.seq=d.event_seq WHERE d.target=?", (identifier,)).fetchone()
        if not row:
            raise StateError(f"Unknown record: {identifier}")
        data = json.loads(row["payload"])
        expected = "proposed" if row["type"] == "registered" else data.get("status")
        if row["target"] != identifier or expected != row["status"]:
            raise StateError("Corrupted decision projection; run health before proceeding")
        return row["status"]

    def decide(self, identifier: str, status: str, reason: dict) -> int:
        self._writing()
        self.get(identifier)
        if not status or not isinstance(reason, dict) or not reason:
            raise StateError("Decision requires a status and reason")
        seq = self.event("decision", identifier, {"status": status, "reason": reason})
        self.db.execute("UPDATE decisions SET status=?,event_seq=? WHERE target=?",
                        (status, seq, identifier))
        return seq

    def request(self, identifier: str, fingerprint: str) -> Any | None:
        self._writing()
        row = self.db.execute("SELECT * FROM requests WHERE id=?", (identifier,)).fetchone()
        if not row:
            return None
        if row["fingerprint"] != fingerprint:
            raise StateError("Idempotency key reused for different operation")
        return json.loads(row["response"])

    def finish_request(self, identifier: str, fingerprint: str, response: Any) -> None:
        self._writing()
        self.db.execute("INSERT INTO requests VALUES(?,?,?)",
                        (identifier, fingerprint, canonical(response)))

    def export(self) -> dict:
        """Obtain a coherent, inspectable snapshot, including historical events."""
        own_transaction = not self.db.in_transaction
        if own_transaction:
            self.db.execute("BEGIN")
        try:
            return {"schema": SCHEMA_VERSION, "revision": self.revision,
                    "records": self.records(),
                    "decisions": [dict(r) for r in self.db.execute("SELECT * FROM decisions ORDER BY target")],
                    "events": [dict(r) for r in self.db.execute("SELECT * FROM events ORDER BY seq")]}
        finally:
            if own_transaction:
                self.db.execute("COMMIT")

    def export_at(self, revision: int) -> dict:
        """Reconstruct the exact database snapshot at a historical revision from the event log."""
        if not isinstance(revision, int) or revision < 0 or revision > self.revision:
            raise StateError(f"Revision {revision} is out of bounds [0, {self.revision}]")
        own_transaction = not self.db.in_transaction
        if own_transaction:
            self.db.execute("BEGIN")
        try:
            events_rows = [dict(r) for r in self.db.execute(
                "SELECT * FROM events WHERE seq <= ? ORDER BY seq", (revision,))]
            records_rows = self.db.execute(
                "SELECT r.id FROM records r JOIN events e ON e.target = r.id AND e.type = 'registered' "
                "WHERE e.seq <= ? ORDER BY r.rowid", (revision,)).fetchall()
            records = [self.get(row["id"]) for row in records_rows]

            decisions_map = {}
            for e in events_rows:
                if e["type"] == "registered":
                    decisions_map[e["target"]] = {"target": e["target"], "status": "proposed", "event_seq": e["seq"]}
                elif e["type"] == "decision":
                    payload = json.loads(e["payload"])
                    decisions_map[e["target"]] = {"target": e["target"], "status": payload["status"], "event_seq": e["seq"]}
            decisions = [decisions_map[k] for k in sorted(decisions_map.keys())]

            return {
                "schema": SCHEMA_VERSION,
                "revision": revision,
                "records": records,
                "decisions": decisions,
                "events": events_rows,
            }
        finally:
            if own_transaction:
                self.db.execute("COMMIT")

    def health(self) -> dict:
        """Verify bytes and rebuild decision projection from the event log."""
        snapshot = self.export()
        errors = []
        expected_status = {}
        prev_hash = ZERO_HASH
        record_map = {r["id"]: r for r in snapshot["records"]}
        registered = set()
        for expected_seq, row in enumerate(snapshot["events"], 1):
            data = json.loads(row["payload"])
            body = {"seq": row["seq"], "type": row["type"], "target": row["target"],
                    "data": data, "created": row["created"], "previous_hash": row["previous_hash"]}
            if row["seq"] != expected_seq or row["previous_hash"] != prev_hash or digest(body) != row["hash"]:
                errors.append(f"Broken event chain at {row['seq']}")
            prev_hash = row["hash"]
            if row["type"] == "registered":
                record = record_map.get(row["target"])
                if not record or record["hash"] != data.get("record_hash"):
                    errors.append(f"Registration mismatch at {row['seq']}")
                registered.add(row["target"])
                expected_status[row["target"]] = ("proposed", row["seq"])
            elif row["type"] == "decision":
                if row["target"] not in registered:
                    errors.append(f"Decision precedes record at {row['seq']}")
                expected_status[row["target"]] = (data["status"], row["seq"])
        for record in snapshot["records"]:
            if record["id"] not in registered or digest({k: record[k] for k in ("id", "kind", "data")}) != record["hash"]:
                errors.append(f"Record integrity failure: {record['id']}")
        actual = {r["target"]: (r["status"], r["event_seq"]) for r in snapshot["decisions"]}
        if actual != expected_status:
            errors.append("Decision projection does not match event log")
        integrity = self.db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            errors.append(integrity)
        return {"ok": not errors, "errors": errors, "revision": snapshot["revision"],
                "record_count": len(record_map), "event_head": prev_hash}
