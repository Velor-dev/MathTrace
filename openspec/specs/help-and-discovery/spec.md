# Help and Discovery Specification

## Purpose
MathTrace equips human users and AI agents with interactive discovery skills, operational documentation guides, and scenario walk-throughs to guide mathematical problem-solving campaigns.

## Requirements

### Requirement: Interactive Help Skill
The system SHALL provide an interactive discovery skill (`mathtrace-help`) enabling users and agents to query workflows, role responsibilities, and runtime commands.

#### Scenario: Workflow discovery query
- **WHEN** a user or agent invokes the `/mathtrace-help` skill
- **THEN** the skill presents the core mathematical workflow phases, available native roles, and standard CLI commands.

#### Scenario: Targeted topic assistance
- **WHEN** the help skill is queried with a specific topic keyword
- **THEN** the skill provides focused guidance and references to authoritative documentation.

### Requirement: Protocol and Role Navigation
The system SHALL maintain clear documentation mapping agent responsibilities, execution protocols, and verification gates for mathematical research.

#### Scenario: Role boundary clarification
- **WHEN** an agent consults protocol documentation in `.agents/math/`
- **THEN** the guide clarifies permissible actions, required handoffs, and verification obligations for each specialist role.

#### Scenario: Campaign phase orientation
- **WHEN** a campaign transitions between intake, exploration, formalization, audit, and release
- **THEN** discovery guides outline entry prerequisites and required artifacts for the active phase.

### Requirement: Entry-point skill guide discovery

The `math-intake` and `math-progress` skills SHALL instruct the main agent to read the applicable MathTrace `help.md` directly alongside `PROTOCOL.md`. The guidance SHALL enable selection of relevant skills according to the current request and campaign state without requiring a fixed sequence or invoking `mathtrace-help` for discovery.

#### Scenario: Intake discovers available skills

- **WHEN** the main agent follows `math-intake`
- **THEN** its entry-point instructions direct it to read both the execution protocol and the skill guide
- **AND** the existing intake obligations remain in effect

#### Scenario: Progress discovers skills within the requested scope

- **WHEN** the main agent follows `math-progress` for a status-only request
- **THEN** its entry-point instructions direct it to read both the execution protocol and the skill guide
- **AND** discovery does not authorize research continuation, delegation, or other actions beyond the request

#### Scenario: Flexible selection during mathematical work

- **WHEN** the main agent considers available skills using the guide
- **THEN** the guidance permits choosing relevant skills as appropriate to the request and campaign state
- **AND** it does not require invoking every skill, a fixed sequence, or the display-only `mathtrace-help` skill

### Requirement: Compatible discovery across coding harnesses

All supported coding harnesses SHALL expose equivalent intake and progress discovery guidance with guide references resolvable from their documented deployed project layout. Propagation SHALL preserve the owner's customized Codex agents/skills structure, existing skill mandates, and specialist-agent isolation.

#### Scenario: Native and Antigravity guide resolution

- **WHEN** intake or progress is used in the managed native projection or the Antigravity payload deployed at the project root
- **THEN** the instructions resolve the protocol and guide to `.agents/math/PROTOCOL.md` and `.agents/math/help.md`

#### Scenario: Shared guidance through harness adapters

- **WHEN** intake or progress is used through any supported adapter that forwards to shared skill definitions, including either supported Codex skill location
- **THEN** following the wrapper reaches instructions to read `coding-harnesses/shared/PROTOCOL.md` and `coding-harnesses/shared/help.md` from the target project root
- **AND** the adapter retains its existing argument handling and host bindings

#### Scenario: Codex customization and specialist boundaries are preserved

- **WHEN** the discovery guidance is propagated
- **THEN** existing Codex agent files and skill entry locations are preserved
- **AND** specialist instructions and scoped task packets do not acquire a requirement to load the root skill guide or orchestrate skills
