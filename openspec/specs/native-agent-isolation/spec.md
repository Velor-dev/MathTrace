# Native Agent Isolation Specification

## Purpose
MathTrace enforces strict isolation boundaries for autonomous mathematical agents through tool-free specialist role definitions, attributable terminal observation capture, and deterministic profile admission.

## Requirements

### Requirement: Tool-Free Specialist Roles
The system SHALL define mathematical agent roles with minimal, purpose-specific capabilities and exclude destructive or arbitrary tool execution from reasoning roles.

#### Scenario: Specialist role configuration
- **WHEN** a mathematical reasoning subagent is spawned
- **THEN** its profile provides only designated domain skills and denies access to host manipulation commands.

#### Scenario: Role integrity enforcement
- **WHEN** an agent role definition is inspected or validated
- **THEN** the runtime verifies that role definitions strictly match the managed native specification.

### Requirement: Attributable Input and Output Admission
The system SHALL admit child agent contributions into the campaign ledger exclusively through verifiable, recorded terminal inputs and outputs.

#### Scenario: Exact terminal response recording
- **WHEN** a child agent produces a mathematical argument or proposal
- **THEN** the host recorder captures the exact attributable terminal transcript and hashes the payload for receipt admission.

#### Scenario: Unqualified session rejection
- **WHEN** an agent response lacks valid transcript attribution or shows tool use outside its admissible profile
- **THEN** the contribution is rejected and barred from entering the campaign ledger.

### Requirement: Model and Reasoning Effort Inheritance
The system SHALL configure subagent execution to inherit the parent agent's foundation model and reasoning effort settings by default while permitting explicit manual overrides.

#### Scenario: Default parameter inheritance
- **WHEN** a subagent is invoked without explicit model parameters
- **THEN** the runtime binds the parent agent's active model identifier and reasoning effort level to the subagent configuration.

#### Scenario: Explicit parameter override
- **WHEN** a specialized subagent call specifies an approved model variant
- **THEN** the runtime executes the subagent with the declared override while logging the configuration in the session metadata.
