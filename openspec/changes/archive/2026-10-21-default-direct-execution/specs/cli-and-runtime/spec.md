# Spec Delta

## ADDED Requirements

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
