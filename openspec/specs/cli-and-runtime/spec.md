# CLI and Runtime Specification

## Purpose
MathTrace provides a unified command-line control surface, isolated package installation packaging, and native agent projection management to operate campaigns and maintain environment integrity.

## Requirements

### Requirement: Unified Command-Line Interface
The system SHALL provide a CLI command surface accessible via the `mathtrace` executable or `python -m mathtrace` for campaign administration, evaluation, and auditing.

#### Scenario: Identity and status inspection
- **WHEN** the user executes `mathtrace --help` or requests runtime identity
- **THEN** the CLI displays the MathTrace environment description, active version, and available operational commands.

#### Scenario: Campaign state querying
- **WHEN** the user invokes campaign commands against an active database
- **THEN** the CLI queries the store, executes the requested operation, and formats status outputs deterministically.

### Requirement: Isolated Package Build and Distribution
The system SHALL support building and installing the `mathtrace` Python package as a self-contained distribution wheel with verified file checksums. Package validation SHALL verify the complete archive against the intended runtime, canonical license, required notices, and explicit proprietary license metadata, rejecting unexpected packages, duplicate or unsafe paths, and stale build content.

#### Scenario: Package wheel generation
- **WHEN** package validation or build tools run
- **THEN** standard wheel artifacts are created under `dist/` or transient build roots without polluting source directories
- **AND** release wheels are built from clean isolated inputs rather than reusing stale build output

#### Scenario: Bytecode and asset fidelity verification
- **WHEN** an installed package wheel is validated
- **THEN** package tools verify that installed modules, assets, and entry points exactly match source definitions
- **AND** validation checks the entire archive member set, required notices, metadata, and recorded checksums rather than only the `mathtrace/` subtree

#### Scenario: Legacy package contamination is rejected
- **WHEN** stale build output contains a legacy `gsd_math` tree or another unapproved package
- **THEN** the clean release build excludes that content
- **AND** validation rejects any wheel into which it is injected even when the current `mathtrace/` files match source

#### Scenario: Unexpected or unsafe archive members
- **WHEN** an archive contains duplicate members, redirected or escaping paths, unapproved files, or mismatched entry points or version metadata
- **THEN** validation fails before that artifact is accepted for installer bundling

#### Scenario: Explicit and faithful licensing metadata
- **WHEN** a Python wheel is built and inspected independently of the source checkout
- **THEN** its metadata identifies MathTrace's custom proprietary license and its included legal files
- **AND** LICENSE is its sole MathTrace license-file entry and matches the maintained source bytes; separate third-party licenses remain governed by their own obligations

#### Scenario: Missing or altered legal material
- **WHEN** a wheel omits or changes a required legal file or contradicts the approved license in its metadata, even with recomputed archive checksums
- **THEN** package validation rejects it before installer bundling

#### Scenario: Inconsistent author metadata
- **WHEN** a wheel has inconsistent author metadata, even with recomputed checksums
- **THEN** package validation rejects it while preserving existing runtime and archive integrity checks

### Requirement: Native Projection Synchronization
The system SHALL maintain and synchronize the native agent environment in `.agents/` from runtime definitions while strictly preserving external toolchains and skills.

#### Scenario: Native projection generation
- **WHEN** `python tools/install_native.py` is executed
- **THEN** the installer regenerates `.agents/math/`, `.agents/agents/`, and math skills, updating `work/native-install.json` with the installation manifest.

#### Scenario: External asset preservation
- **WHEN** external tools or OpenSpec skills exist in `.agents/skills/` or `.agents/workflows/`
- **THEN** the projection installer identifies and preserves all external files without overwriting or deleting them.

### Requirement: Runtime Execution Mode Selection
The system SHALL use one runtime execution-mode selection mechanism for computation, formal execution and toolchain provisioning, accepting `direct` and `bubblewrap` and defaulting to `direct`. Mode selection SHALL NOT depend on agent workflow or coding-harness sandbox settings.

#### Scenario: Native default across operating systems
- **WHEN** an operator executes a reviewed Python experiment or Lean plan on Windows, Linux or macOS without selecting a mode
- **THEN** execution uses native processes without requiring WSL, Ubuntu, Docker, Bubblewrap or another sandbox dependency.

#### Scenario: Explicit optional sandbox
- **WHEN** an operator selects `bubblewrap` on supported Linux or through the existing Windows/Ubuntu WSL transport
- **THEN** the runtime uses the existing Linux sandbox backend and records that selection.

#### Scenario: Unavailable or invalid mode
- **WHEN** the selected backend is unavailable, unsupported on the host, or an unknown mode is supplied
- **THEN** the operation reports an explicit error without launching a different backend or silently falling back.

#### Scenario: Committed selection survives recovery
- **WHEN** an existing attempt is inspected, recovered or requested again after the runtime default changes
- **THEN** its recorded mode and original request determine recovery, no new workload is launched, and a conflicting mode request is rejected rather than changing the attempt.

### Requirement: Target-Compatible Pinned Toolchain Provisioning
The system SHALL provision publisher-digest-verified Lean distributions matching the selected execution target's operating system and architecture. Provisioning SHALL preserve exact release pinning, complete archive manifests, fresh installation trees and rejection of redirected or unverified files.

#### Scenario: Native distribution selection
- **WHEN** native Lean is provisioned for Windows x86-64, Linux x86-64 or AArch64, or macOS x86-64 or AArch64
- **THEN** the matching official pinned distribution is installed with platform-correct executable naming and permissions, and its OS/architecture and publisher identity are recorded.

#### Scenario: Sandbox target differs from host
- **WHEN** Lean is provisioned for the optional Windows/WSL backend
- **THEN** provisioning selects the supported Linux execution-target distribution rather than a Windows executable.

#### Scenario: Unsupported or mismatched target
- **WHEN** no supported publisher asset exists for the target, its digest is unavailable, or an installed toolchain does not match the chosen backend
- **THEN** the runtime rejects the operation without substituting an arbitrary binary, architecture or backend.

### Requirement: Execution-Independent Harness Instructions
The system SHALL retain the existing mathematical skills and specialist-agent structures across execution modes. Runtime instructions and generated harness payloads SHALL use the runtime's selected mode without requiring optional sandbox setup or OpenSpec, and SHALL preserve specialist independence and model/effort inheritance.

#### Scenario: Same Codex workflow in both modes
- **WHEN** existing Codex skills and paired TOML/Markdown specialist agents are used with either execution mode
- **THEN** workers continue returning proposals, root mediates reviewed execution, and no mode-specific skill, agent definition or mathematical procedure is required.

#### Scenario: Source and generated payload consistency
- **WHEN** execution instructions are regenerated from maintained sources
- **THEN** existing Codex agent formats and skill locations are retained, execution-related wording stays consistent across maintained copies, and unrelated owner customizations and external assets are preserved or reported as conflicts before replacement.

#### Scenario: Capture limitation remains independent
- **WHEN** a harness lacks qualified independent transcript capture
- **THEN** the limitation remains disclosed and the runtime does not treat native execution or sandbox selection as a substitute for independent review evidence.

