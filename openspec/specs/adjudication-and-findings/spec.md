# Adjudication and Findings Specification

## Purpose
MathTrace enforces rigorous adjudication of mathematical findings, objections, and counterarguments through nonparty reviews and scope certification to resolve challenges without silent substitution of evidence.

## Requirements

### Requirement: Independent Nonparty Adjudication
The system SHALL require that all formal findings, counterarguments, and objections are adjudicated by independent nonparty review protocols.

#### Scenario: Author nonparty separation
- **WHEN** an objection is raised against an inference or candidate release
- **THEN** adjudication requires review by an agent or evaluator distinct from the original author.

#### Scenario: Challenge resolution recording
- **WHEN** a nonparty reviewer evaluates a contested finding
- **THEN** the outcome is recorded as an immutable adjudication decision binding the target claim or candidate.

### Requirement: Independent Scope Certification
The system SHALL separate the certification of finding scope and well-formedness from substantive mathematical validation.

#### Scenario: Scope well-formedness assessment
- **WHEN** a finding or objection packet is submitted
- **THEN** the runtime certifies that the target, assumptions, and scope references are well-formed before admitting the challenge.

#### Scenario: No premature truth attribution
- **WHEN** a finding receives scope certification
- **THEN** the finding enters the active portfolio as a formal challenge without being treated as definitive mathematical truth.

### Requirement: Targeted Finding Scoping
The system SHALL distinguish between candidate-scoped findings and claim-scoped findings to prevent unwarranted target-wide blocking while ensuring sound isolation.

#### Scenario: Candidate-scoped defect isolation
- **WHEN** a finding demonstrates an implementation flaw specific to one candidate artifact
- **THEN** that candidate is blocked while alternative candidates addressing the same claim remain eligible.

#### Scenario: Claim-scoped refutation enforcement
- **WHEN** a finding demonstrates a fundamental mathematical counterexample to a claim
- **THEN** all current and future candidates targeting that claim are blocked until the finding is retracted or resolved.

### Requirement: Finding Dismissal and Retraction
The system SHALL manage finding retractions and dismissals explicitly without permitting silent substitution of historical audit witnesses.

#### Scenario: Retraction restoring eligibility
- **WHEN** a nonparty adjudication dismisses or retracts a previous finding with verified counter-evidence
- **THEN** downstream eligibility is recomputed and restored without altering immutable historical events.

#### Scenario: Prevention of silent witness substitution
- **WHEN** a finding invalidates a previously frozen audit witness
- **THEN** the system requires a fresh audit and rejects automatic substitution of alternate witnesses under the old certificate.
