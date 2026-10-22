# Mathematical Evaluation Specification

## Purpose
MathTrace evaluates mathematical claims and inferences using scoped support and refutation semantics, cycle-free witness forests, and conditional theorem applications to guarantee sound deduction without circularity.

## Requirements

### Requirement: Scoped Inference Evaluation
The system SHALL evaluate mathematical support and refutations within explicit, bounded inference scopes rather than relying on ambient global assertions.

#### Scenario: Contained hypothesis evaluation
- **WHEN** an inference is evaluated under local branch assumptions
- **THEN** support is computed strictly within the bounded scope without leaking premises to sibling claims.

#### Scenario: Antitone refutation propagation
- **WHEN** an antecedent or prerequisite within an inference tree is refuted
- **THEN** the system propagates the refutation bounds conservatively to disqualify dependent conclusions.

### Requirement: Selected Witness Forest
The system SHALL construct and evaluate inference graphs using selected witness forests (`scoped-selected-forest-v3`) that memoize identical subarguments while preventing circular reasoning.

#### Scenario: Subargument deduplication
- **WHEN** multiple inferences rely on identical verified subarguments
- **THEN** the witness forest shares the verified subargument across branches without duplicate proof searches.

#### Scenario: Cycle rejection
- **WHEN** an inference chain introduces an indirect circular dependency
- **THEN** the evaluator detects the cycle during finite tree grounding and rejects the witness as invalid.

### Requirement: Conditional Theorem Application
The system SHALL qualify conditional theorem rules before antecedent discharge and require explicit grounding of all mapped hypotheses in consuming inferences.

#### Scenario: Rule qualification before proof
- **WHEN** an agent introduces a conditional theorem rule with unproven antecedents
- **THEN** the runtime qualifies the rule schema while tracking all antecedents as mandatory obligations.

#### Scenario: Consuming inference hypothesis grounding
- **WHEN** a conclusion consumes a qualified conditional theorem
- **THEN** the evaluator verifies that every mapped antecedent is grounded by valid scoped evidence.

### Requirement: Credible Refutation Veto
The system SHALL treat credible informal or computational refutations as blocking vetoes that prevent claim promotion regardless of claimed formal verification.

#### Scenario: Informal counterexample blocking promotion
- **WHEN** a credible counterexample or refutation is registered against a claim
- **THEN** promotion of the claim is blocked until the refutation is explicitly adjudicated and dismissed.
