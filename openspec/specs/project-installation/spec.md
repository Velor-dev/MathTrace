# project-installation Specification

## Purpose

Install a complete MathTrace runtime and selected coding-harness integration into an existing project, with verifiable dependencies, preserved user ownership, and recoverable updates.

## Requirements

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


### Requirement: Self-contained installation payload

The installer SHALL bundle a version-matched verified Python wheel and the selected harness's complete required asset closure. Installed runtime invocation, skills, agents, guides, and references SHALL resolve independently of the MathTrace source checkout and npm cache. The installer SHALL NOT create `coding-harnesses/` in the target project root, SHALL locate shared references under `.mathtrace/`, and SHALL provide visible progress during provisioning without production npm dependencies.

#### Scenario: Source checkout and npm cache are unavailable
- **WHEN** installation completes and the source checkout and original npm package directory are unavailable
- **THEN** the installed launcher runs the expected local MathTrace runtime and all required harness references resolve within the installed project
- **AND** runtime execution requires no environment activation or global PATH modification

#### Scenario: Complete harness inventory
- **WHEN** each supported harness payload is installed in its documented supported environment
- **THEN** its existing eight skills and applicable specialist bindings are available with their required shared assets
- **AND** mutually exclusive OpenCode versions are not activated together

#### Scenario: Uncluttered project root
- **WHEN** any supported harness (such as Antigravity, Claude Code, Cursor, or Devin) is installed into a target project
- **THEN** no `coding-harnesses/` directory is created in the target project root
- **AND** any required shared guides, policies, or protocol references are deployed under `.mathtrace/` rather than the project root

#### Scenario: Visible provisioning progress
- **WHEN** installation initiates Python runtime environment creation, wheel installation, or Lean 4 toolchain downloading and extraction
- **THEN** user-visible status progress messages are emitted to stdout before and during each operation
- **AND** the terminal does not remain silently stalled during network downloads or archive extraction


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


### Requirement: User-owned files and agent structures

Installation SHALL preserve unrelated files, user configuration, external skills, specialist isolation, and existing skill behavior. Codex's customized skill locations and paired agent structure SHALL be retained. Conflicting existing content SHALL be reported and preserved before replacement, and project instruction merges SHALL change only the MathTrace-owned section.

#### Scenario: Customized Codex project
- **WHEN** Codex is selected in a project with existing customized skills or paired agent files
- **THEN** the existing structure is retained and unowned or modified conflicting files are not overwritten
- **AND** duplicate compatibility skill entries are not activated automatically

#### Scenario: Existing project instructions and unrelated assets
- **WHEN** a project contains its own instructions, configurations, and unrelated skills
- **THEN** these remain intact outside an explicitly managed MathTrace section
- **AND** no new mathematical skill sequence, model routing, specialist context access, or evidence qualification is introduced

### Requirement: Recoverable ownership-aware updates

Repeated installation and updates SHALL track exact owned file identities, preserve local edits, preflight conflicts, and retain recoverable deployment state. Only unchanged previously owned obsolete files SHALL be removed. Concurrent operations and redirected destination paths SHALL be rejected. Failures SHALL NOT leave an unreported mixed active installation or rewrite campaign history to undo deployment.

#### Scenario: Unchanged repeat installation
- **WHEN** the same release and harness are installed again with unchanged owned files
- **THEN** installation verifies and reuses the deployment without duplicating instruction sections or toolchain records

#### Scenario: Update conflicts or unsupported harness switch
- **WHEN** an update encounters edited owned files, unowned collisions, or an incompatible existing harness deployment
- **THEN** preflight stops with the exact conflicts and preserves active files and configuration

#### Scenario: Interrupted update
- **WHEN** deployment fails or is interrupted after staging begins
- **THEN** recovery restores or identifies the previous active file deployment using retained installation records and backups
- **AND** retries reconcile valid append-only provisioning records without deleting campaign history

### Requirement: Verified readiness and distribution notices
Installation SHALL report success only after verifying payload integrity, local runtime identity, required guide paths, campaign health, pinned toolchain integrity, and selected harness prerequisites. Artifacts and installed projects SHALL retain the canonical proprietary license and required notices within owner-approved permissions. Local validation SHALL NOT depend on publication or expand those permissions.

#### Scenario: Verification failure
- **WHEN** a required check fails or cannot establish readiness
- **THEN** installation reports the failing check, recovery state, and corrective action without claiming complete success

#### Scenario: Artifact rights preservation
- **WHEN** wheel and npm artifacts are prepared for local validation
- **THEN** the canonical MathTrace license and required notices are retained without unapproved licensing terms
- **AND** private workspace data, credentials, campaign evidence, and development archives are excluded

#### Scenario: License available independently of checkout and cache
- **WHEN** any supported harness is installed and the original checkout and npm cache are unavailable
- **THEN** the exact canonical LICENSE remains readable inside the project without network access; README.md supplies project attribution and downloaded components retain their own legally required notices
- **AND** the project's own root license and unrelated notices are not replaced

#### Scenario: Repeat installation and update preservation
- **WHEN** legal files are installed again or updated
- **THEN** existing ownership-aware conflict checks, recoverable deployment, and notice verification apply
- **AND** edited or unowned conflicting project files are preserved and reported
- **AND** obsolete MathTrace notice files from earlier installations are removed only when unchanged and previously owned

### Requirement: Explicit license metadata with retained publication safeguards
The npm artifact SHALL identify its canonical custom license using file-based metadata. Authorized public publication SHALL require an assembled, integrity-verified payload; publishing the unassembled source directory SHALL fail. Package validation SHALL preserve license, runtime, version, and payload checks. Tests SHALL use local artifacts without registry writes.

#### Scenario: Authorized public artifact
- **WHEN** an approved release is assembled, packed, and validated
- **THEN** the package is public with a resolving canonical license reference and a payload-validating publication hook
- **AND** registry and access metadata identify the official public npm registry

#### Scenario: Incomplete publication input
- **WHEN** the publication hook runs without a valid assembled payload
- **THEN** publication fails before registry writes
- **AND** tests verify this failure without bypassing integrity checks
