# Advisory Learning Specification

## Purpose
MathTrace captures empirical research tactics, failure patterns, and search heuristics into an advisory knowledge layer that guides reasoning agents without contaminating deductive mathematical proof trees.

## Requirements

### Requirement: Advisory Boundary Isolation
The system SHALL strictly isolate empirical advisory lessons from deductive mathematical inferences, preventing heuristics from serving as formal proof witnesses.

#### Scenario: Advisory separation from proof trees
- **WHEN** an agent consults advisory hints or tactical lessons during problem solving
- **THEN** advisory records are excluded from the formal inference graph and cannot satisfy mathematical proof obligations.

#### Scenario: Formal certification independence
- **WHEN** a proof or candidate audit is validated
- **THEN** the validation engine verifies that zero proof steps depend on advisory entries.

### Requirement: Lineage-Based Advisory Curation
The system SHALL curate advisory lessons by linking each recommendation to an immutable event origin, candidate identifier, and recorded outcome.

#### Scenario: Lesson extraction from campaign outcome
- **WHEN** an exploration path yields an informative success or refutation
- **THEN** the learning module extracts a structured advice packet pinned to the exact source event and candidate lineage.

#### Scenario: Origin immutability preservation
- **WHEN** an origin candidate is subsequently superseded or retired
- **THEN** the curated advisory lesson preserves its historical origin pointer without undergoing silent rebasing.

### Requirement: Scoped Target Admission and Revocation
The system SHALL support explicit admission of advisory lessons to specific problem scopes and allow revocation when advice is determined to be counterproductive or obsolete.

#### Scenario: Targeted advice injection
- **WHEN** a worker agent requests guidance for a specific lemma category
- **THEN** the coordinator filters and delivers only advisory lessons admitted for that mathematical domain.

#### Scenario: Advisory revocation without theorem invalidation
- **WHEN** an advisory heuristic is revoked or deprecated
- **THEN** the advisory status is updated without invalidating any previously verified mathematical proofs.
