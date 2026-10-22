# Adaptive Coordination Specification

## Purpose
MathTrace coordinates complex multi-step mathematical workflows by projecting dynamic frontiers from immutable events, tracking durable work intents, and managing obligation life cycles with crash recovery.

## Requirements

### Requirement: Dynamic Frontier Projection
The system SHALL compute the current mathematical frontier, open obligations, and available action routes dynamically from verified event history.

#### Scenario: Frontier derivation
- **WHEN** the campaign state is inspected for next available actions
- **THEN** the coordinator computes the active frontier by filtering fulfilled subgoals and exposing pending obligations.

#### Scenario: Route certificate qualification
- **WHEN** an agent selects an admissible mathematical route
- **THEN** the coordinator verifies prerequisite certificates before issuing execution authorization.

### Requirement: Durable Work Intent Registration
The system SHALL record committed work intent records in the database prior to dispatching computational or agent tasks to prevent duplicate or unledgered actions.

#### Scenario: Intent registration before launch
- **WHEN** a task or computation is scheduled for execution
- **THEN** a work intent record is committed to the database before the process or subagent is launched.

#### Scenario: Duplicate execution prevention
- **WHEN** an agent attempts to initiate an identical task that already has an active work intent
- **THEN** the coordinator detects the conflicting intent and rejects the redundant launch.

### Requirement: Idempotent Execution Recovery
The system SHALL recover in-flight or interrupted task outputs from attributable journal files without re-executing the underlying workload.

#### Scenario: Interrupted session output recovery
- **WHEN** a process completes execution during an agent restart or interruption
- **THEN** the coordinator re-opens the recorded attempt journal and imports the finished output without rerunning the task.

### Requirement: Obligation Lineage and Repair Tracking
The system SHALL maintain explicit lineage for all mathematical obligations generated during proof decomposition and track structured repair states.

#### Scenario: Subgoal obligation generation
- **WHEN** a claim is decomposed into lemma obligations
- **THEN** each obligation is assigned an immutable parent lineage reference and registered in the active frontier.

#### Scenario: Obligation repair state management
- **WHEN** a proposed proof step for an obligation fails or is refuted
- **THEN** the obligation transitions into a designated repair state and generates an actionable diagnostic record.
