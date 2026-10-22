# Canonical State Specification

## Purpose
MathTrace maintains all campaign data in an append-only, transactional SQLite database with monotonic event streams and cryptographic SHA-256 state digests to guarantee auditability, crash resilience, and immutability.

## Requirements

### Requirement: Transactional SQLite Ledger
The system SHALL persist all campaign entities, artifacts, and event logs in a dedicated SQLite database with foreign key enforcement and atomic transaction boundaries.

#### Scenario: Atomic entity persistence
- **WHEN** a new claim, inference, or evidence record is registered
- **THEN** the store writes the entity and its corresponding event log within a single database transaction.

#### Scenario: Foreign key integrity enforcement
- **WHEN** an entity references a nonexistent parent or prerequisite identifier
- **THEN** the store rejects the write and raises a constraint violation.

### Requirement: Monotonic Event Streaming
The system SHALL append every state modification to a monotonic event sequence and derive all operational projections strictly from ordered event history.

#### Scenario: Event sequence appending
- **WHEN** a state transition occurs in the campaign
- **THEN** a new event is assigned an incremented sequence index and committed immutably.

#### Scenario: Deterministic state projection
- **WHEN** the campaign frontier or eligibility table is queried
- **THEN** the runtime projects the current state from the verified event log without mutating underlying records.

### Requirement: State Digest Computation
The system SHALL compute a deterministic cryptographic SHA-256 digest representing the complete database contents to detect out-of-band modifications.

#### Scenario: Valid state verification
- **WHEN** a campaign session opens an existing store
- **THEN** the stored digest is verified against the recalculated database hash before accepting commands.

#### Scenario: Tamper detection
- **WHEN** an external process modifies the database file out of band
- **THEN** the store detects the digest mismatch and refuses to load or execute operations.
