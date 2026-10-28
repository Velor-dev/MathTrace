# Spec Delta

## MODIFIED Requirements

### Requirement: One-invocation project installation

The installer SHALL expose `npx mathtrace@latest`, present a minimalist numbered selection displaying each supported harness name cleanly without duplicate parenthetical identifiers, and install the selected integration into the invocation's project directory without a global MathTrace installation or a separate init command. The installer SHALL require existing Python 3.11+ and SHALL NOT install Python automatically.

#### Scenario: Successful interactive installation
- **WHEN** a user selects a valid harness and all prerequisites are available
- **THEN** the installer provisions and verifies the local runtime, default campaign store, pinned Lean toolchain, and selected integration in that invocation
- **AND** the target project's package dependencies and existing Python environment are not replaced

#### Scenario: Minimalist harness selection menu
- **WHEN** the interactive installer lists available harness options
- **THEN** each choice is formatted cleanly by name (such as `1. Devin`, `4. Antigravity`, `5. Codex`) without duplicate parenthetical identifiers

#### Scenario: Invalid selection or cancellation
- **WHEN** input is invalid, the user cancels, or interactive selection is unavailable without an explicit harness selection
- **THEN** invalid input is explained or cancellation is reported without selecting an arbitrary harness or changing active project files

#### Scenario: Unsupported Python environment
- **WHEN** Python is missing, older than 3.11, or lacks usable environment/pip support
- **THEN** installation stops with precise prerequisite instructions before active deployment
- **AND** no global or system Python installation is attempted

### Requirement: Bounded external harness prerequisites

The installer SHALL NOT execute host harness binary checks or require host CLI presence on the local machine during project installation. Installer-managed writes SHALL stay inside the target project. It SHALL NOT silently install host applications, extensions, or plugins, modify profile/home configuration, configure credentials, or claim readiness from copied files alone.

#### Scenario: Missing Pi extension
- **WHEN** Pi is selected without a verifiably compatible required subagent extension
- **THEN** installation stops before active project changes and identifies the external extension setup and rerun steps

#### Scenario: Hermes skill source is not configured
- **WHEN** Hermes is selected without a verified skill source bound to the target project's deployed skills
- **THEN** installation stops with the exact profile skill-source setup and working-directory requirements
- **AND** the installer does not modify that profile or the user's home directory

#### Scenario: External requirements are satisfied
- **WHEN** the existing setup is verified for the selected harness
- **THEN** the installer proceeds without requiring host CLI executable presence on the local PC (such as `antigravity --version`) or modifying the external environment
- **AND** any remaining host loading or evidence qualification limits are disclosed

#### Scenario: No host harness execution probe
- **WHEN** a user selects any supported harness (including Antigravity, Codex, Cursor, Devin, Claude Code, and others)
- **THEN** installation proceeds without checking or executing host CLI version commands on the local computer
- **AND** configuration and assets for the selected harness are deployed into the project directory regardless of whether the user uses a desktop application or CLI

### Requirement: Existing runtime and toolchain integrity

The installer SHALL use existing MathTrace state initialization and publisher-verified pinned Lean provisioning mechanisms using Direct Execution. The npm package SHALL NOT offer, probe, or download optional Bubblewrap sandbox components or require WSL during project installation. It SHALL preserve existing campaign events, receipts, toolchains, mathematical verification gates, and historical execution identities.

#### Scenario: Fresh project bootstrap
- **WHEN** no default campaign database exists
- **THEN** installation initializes it and provisions the supported exact Lean release for the selected execution target
- **AND** it creates no mathematical contract, proof claim, independent-review qualification, or release acceptance

#### Scenario: Existing project or repeated installation
- **WHEN** the default database and a matching verified toolchain already exist
- **THEN** they are reused without reinitialization, history rewriting, or duplicate toolchain provisioning
- **AND** invalid or incompatible existing state is reported without replacement

#### Scenario: Native default and optional sandbox
- **WHEN** project installation runs on a supported Windows, Linux, or macOS target
- **THEN** native Lean is provisioned using Direct Execution without offering an optional Bubblewrap sandbox download or probing WSL/libseccomp in the npm package
- **AND** historical records and direct verification receipts remain intact
