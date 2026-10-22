# Spec Delta

## MODIFIED Requirements

### Requirement: Pinned Lean 4 Proof Checking
The system SHALL verify formal proofs using an explicitly pinned official Lean 4 toolchain, fresh checking context and the existing checked-target primitive profile in either execution mode. It SHALL preserve compiler concurrency control, timeouts and output bounds, record actual resource enforcement, and reject checks lacking required mathematical evidence.

#### Scenario: Fresh checker invocation
- **WHEN** formal Lean proof code is checked for verification
- **THEN** the runtime compiles with `-j2` and verifies retained outputs through the pinned checked-target helper's pristine primitive-context replay; the standalone fresh-check path retains `leanchecker --fresh`, and the receipt distinguishes these checking protocols.

#### Scenario: Malformed declaration rejection
- **WHEN** a proof contains an unchecked false premise or type mismatch
- **THEN** compilation or fresh checking rejects it and records a failed formal receipt rather than qualifying diagnostic stdout as proof.

#### Scenario: Native checking without namespace attestation
- **WHEN** native compilation and checked-target verification succeed with all required evidence intact
- **THEN** absence of Linux namespaces alone does not disqualify the proof check, and the receipt explicitly reports direct execution without sandbox isolation.

#### Scenario: Resource enforcement differs across platforms
- **WHEN** formal execution occurs on a supported native platform
- **THEN** timeouts and output bounds are enforced, available process limits and their scope are recorded, unsupported limits are explicitly identified, and no receipt falsely claims the sandbox's 8 GiB address-space or bounded-filesystem enforcement.

### Requirement: Bubblewrap Host Isolation
The system SHALL isolate computational scripts and external theorem checkers inside the existing Bubblewrap container with unshared host namespaces only when `bubblewrap` is explicitly selected. Successful sandbox evidence SHALL require its existing isolation attestations; Direct Execution SHALL NOT fabricate them.

#### Scenario: Namespace isolation and network denial
- **WHEN** a computation or checker process starts in the explicitly selected Bubblewrap backend
- **THEN** the sandbox drops network access and isolates IPC, PID, UTS, and user namespaces from the host, retaining existing seccomp restrictions.

#### Scenario: Read-only host filesystem binding
- **WHEN** the optional sandbox mounts system directories
- **THEN** root host paths are mounted read-only and ephemeral writes are confined to clean, bounded temporary storage under the existing isolation policy.

#### Scenario: Sandbox setup fails
- **WHEN** an explicitly selected sandbox cannot establish required isolation
- **THEN** the runtime retains attributable failure evidence where available, does not qualify an isolated observation or proof check, and does not retry through Direct Execution.

### Requirement: Compiled Semantic Inspection
The system SHALL inspect retained compiled artifacts using the pinned checked-target verifier, binding exact declarations, types, definition semantics and foundation schemas to the selected theorem. Original-target fidelity SHALL require independent review; receipts SHALL NOT claim independently verified source-to-object correspondence.

#### Scenario: Binary semantic fidelity verification
- **WHEN** Lean compiles a proof into intermediate or binary artifacts
- **THEN** the full fixed compiled-file family is retained with explicit presence, sizes and hashes, checked semantic views expose the exact theorem and material definitions, and independent review assesses their fidelity to the original target.

#### Scenario: Declaration spoofing prevention
- **WHEN** a compiled artifact attempts to satisfy a goal using an unapproved external axiom or mismatched declaration name
- **THEN** semantic inspection fails and the formal receipt is rejected.

#### Scenario: Portable exact resolution
- **WHEN** verification resolves modules on Windows, Linux or macOS
- **THEN** reference modules resolve only under the pinned official distribution and candidate modules resolve only under the recorded ordered roots, with exact part-presence and byte-manifest bindings and no implicit current-directory or ambient override roots.

## ADDED Requirements

### Requirement: Distinct Process and Isolation Evidence
The system SHALL separately record process outcome, execution environment, mathematical checking result and optional sandbox attestation. These facts SHALL bind the exact committed request and attributable terminal observation, including mode, producer and verifier identities. Direct evidence SHALL disclose its trusted local-host boundary.

#### Scenario: Successful native experiment
- **WHEN** a reviewed native Python experiment executes successfully without namespace setup
- **THEN** its receipt records a computational observation with isolation not established, and does not independently establish a universal mathematical claim.

#### Scenario: Timeout or output overflow
- **WHEN** native execution times out or exceeds bounded captured output
- **THEN** the recorded result preserves that condition, cannot qualify a successful formal check, and does not convert a failed experiment into a mathematical refutation.

#### Scenario: Uncertain teardown
- **WHEN** the recorder cannot establish the termination it would certify, including unresolved owned-process cleanup
- **THEN** it does not publish a successful terminal teardown assertion, recovery preserves uncertainty, and missing evidence does not authorize automatic retry.

#### Scenario: Review sees environment assurance
- **WHEN** an independent reviewer receives compiled formal evidence
- **THEN** bounded task context includes the recorded execution mode and material environment/assurance limitations alongside exact semantic views, without importing diagnostic process text or other reviewers' verdicts.

### Requirement: Historical Receipt and Release Compatibility
The system SHALL validate recorded evidence by its original protocol without rewriting history, weakening old isolation checks or upgrading legacy assurance. Current receipts in either execution mode SHALL satisfy the existing source, foundation, fidelity, provenance, candidate-audit and release gates.

#### Scenario: Existing checked sandbox receipt
- **WHEN** an intact previously eligible sandbox receipt is evaluated after Direct Execution becomes the default
- **THEN** its original request and namespace requirements remain enforced and the default change alone neither invalidates it nor changes its assurance.

#### Scenario: Interrupted historical attempt
- **WHEN** a pre-change pending attempt has attributable terminal output available
- **THEN** recovery uses its original protocol and receipt writer without replaying the workload or relabeling it as direct execution.

#### Scenario: Legacy or damaged evidence
- **WHEN** evidence was already ineligible under its original checking profile, lacks required bindings, or has withdrawn dependencies
- **THEN** the runtime preserves that ineligibility and requires the existing repair or fresh-check path rather than treating the default change as migration approval.

#### Scenario: Candidate release in either mode
- **WHEN** a candidate relies on qualified formal evidence from either mode
- **THEN** freezing retains its exact evidence closure and release still requires all existing independent audits, target fidelity, criteria fulfillment and nonparty challenge dispositions; a valid check alone cannot bypass any gate.
