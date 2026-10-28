# Spec Delta

## MODIFIED Requirements

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
- **AND** official Lean distribution archive downloads emit continuous real-time progress indicators displaying transferred bytes, total size, percentage, and transfer speed
- **AND** toolchain archive extraction and integrity verification emit clear user-visible status messages before extracting files and during validation
- **AND** the terminal does not remain silently stalled during network downloads or archive extraction


### Requirement: Existing runtime and toolchain integrity

The installer SHALL use existing MathTrace state initialization and publisher-verified pinned Lean provisioning mechanisms using Direct Execution. The npm package SHALL NOT offer, probe, or download optional Bubblewrap sandbox components or require WSL during project installation. It SHALL preserve existing campaign events, receipts, toolchains, mathematical verification gates, and historical execution identities. Fresh provisioning SHALL validate the extracted distribution against the archive manifest without executing redundant immediate post-installation verification sweeps on unchanged newly extracted trees.

#### Scenario: Fresh project bootstrap
- **WHEN** no default campaign database exists
- **THEN** installation initializes it and provisions the supported exact Lean release for the selected execution target
- **AND** newly extracted toolchain trees are verified against archive digests without immediate redundant file tree re-verification sweeps
- **AND** it creates no mathematical contract, proof claim, independent-review qualification, or release acceptance

#### Scenario: Existing project or repeated installation
- **WHEN** the default database and a matching verified toolchain already exist
- **THEN** they are reused without reinitialization, history rewriting, or duplicate toolchain provisioning
- **AND** invalid or incompatible existing state is reported without replacement

#### Scenario: Native default and optional sandbox
- **WHEN** project installation runs on a supported Windows, Linux, or macOS target
- **THEN** native Lean is provisioned using Direct Execution without offering an optional Bubblewrap sandbox download or probing WSL/libseccomp in the npm package
- **AND** historical records and direct verification receipts remain intact
